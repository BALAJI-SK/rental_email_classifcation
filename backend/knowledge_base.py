import json
import re
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


async def get_contact_context(db, contact_id: int) -> dict:
    """
    Return full contact profile with open threads, message history,
    and missing_info list for smart draft generation.
    """
    async with db.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)) as c:
        contact = await c.fetchone()
    if not contact:
        return {}

    contact = dict(contact)

    # Open threads for this contact
    async with db.execute("""
        SELECT id, subject, urgency_level, urgency_score, status, ai_summary,
               category, last_message_at, days_open
        FROM threads
        WHERE primary_contact_id = ? AND status IN ('open', 'in_progress', 'escalated')
        ORDER BY urgency_score DESC
    """, (contact_id,)) as c:
        open_threads = [dict(r) for r in await c.fetchall()]

    # Property name
    property_name = None
    if contact.get("property_id"):
        async with db.execute(
            "SELECT name FROM properties WHERE id = ?", (contact["property_id"],)
        ) as c:
            row = await c.fetchone()
            property_name = row[0] if row else None

    # Determine missing info
    missing_info = []
    if not contact.get("phone"):
        missing_info.append("phone")
    if not contact.get("unit"):
        missing_info.append("unit")
    if not contact.get("email"):
        missing_info.append("email")
    if contact.get("type") == "tenant" and not contact.get("lease_end"):
        missing_info.append("lease_end")

    return {
        "id": contact["id"],
        "name": contact["name"],
        "email": contact.get("email"),
        "phone": contact.get("phone"),
        "type": contact.get("type"),
        "role": contact.get("role"),
        "unit": contact.get("unit"),
        "property_id": contact.get("property_id"),
        "property": property_name,
        "lease_start": contact.get("lease_start"),
        "lease_end": contact.get("lease_end"),
        "is_known": bool(contact.get("is_known")),
        "total_messages": contact.get("total_messages", 0),
        "total_threads": contact.get("total_threads", 0),
        "open_threads": open_threads,
        "open_thread_count": len(open_threads),
        "sentiment_trend": contact.get("sentiment_avg"),
        "first_seen": contact.get("first_seen"),
        "last_seen": contact.get("last_seen"),
        "notes": contact.get("notes"),
        "missing_info": missing_info,
    }


async def get_contact_sheet(db, property_id: str = None) -> list[dict]:
    """Return contact data list for Excel export."""
    conditions = ["c.type = 'tenant'"]
    params = []
    if property_id:
        conditions.append("c.property_id = ?")
        params.append(property_id)

    where = "WHERE " + " AND ".join(conditions)

    async with db.execute(f"""
        SELECT c.id, c.name, c.email, c.phone, c.unit, c.property_id,
               c.lease_start, c.lease_end, c.is_known, c.total_messages,
               c.total_threads, c.sentiment_avg, c.last_seen,
               p.name as property_name
        FROM contacts c
        LEFT JOIN properties p ON c.property_id = p.id
        {where}
        ORDER BY p.name, c.name
    """, params) as cursor:
        rows = [dict(r) for r in await cursor.fetchall()]

    # Add open issue count per contact
    for row in rows:
        async with db.execute("""
            SELECT COUNT(*) FROM threads
            WHERE primary_contact_id = ? AND status IN ('open', 'in_progress')
        """, (row["id"],)) as c:
            row["open_issues"] = (await c.fetchone())[0]

    return rows


async def update_contact_from_message(db, contact_id: int, message: dict):
    """
    Extract any new info from a message body and update the contact record.
    Looks for phone numbers and unit references.
    """
    body = message.get("body", "")

    # Extract phone
    phone_match = re.search(r"(\+?[\d\s\-]{10,15})", body)
    new_phone = None
    if phone_match:
        candidate = phone_match.group(1).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 9:
            new_phone = candidate

    # Extract unit reference (e.g., "Apt 14B", "Unit 3C", "Flat 2")
    unit_match = re.search(r"\b(Apt|Unit|Flat|Apartment)\s+([A-Z0-9]{1,4}[A-Z]?)\b", body, re.I)
    new_unit = unit_match.group(0) if unit_match else None

    # Only update fields we don't already have
    async with db.execute(
        "SELECT phone, unit FROM contacts WHERE id = ?", (contact_id,)
    ) as c:
        contact = await c.fetchone()
    if not contact:
        return

    updates = []
    params = []
    if new_phone and not contact[0]:
        updates.append("phone = ?")
        params.append(new_phone)
    if new_unit and not contact[1]:
        updates.append("unit = ?")
        params.append(new_unit)

    # Also update is_known if we now have enough info
    if updates:
        updates.append("last_seen = ?")
        params.append(datetime.now(timezone.utc).isoformat())
        params.append(contact_id)
        await db.execute(
            f"UPDATE contacts SET {', '.join(updates)} WHERE id = ?", params
        )

        # Re-evaluate is_known
        async with db.execute(
            "SELECT email, phone, unit FROM contacts WHERE id = ?", (contact_id,)
        ) as c:
            row = await c.fetchone()
        if row and row[0] and (row[1] or row[2]):
            await db.execute(
                "UPDATE contacts SET is_known = 1 WHERE id = ?", (contact_id,)
            )

        await db.commit()
        logger.debug(f"Contact {contact_id} updated from message: {updates}")
