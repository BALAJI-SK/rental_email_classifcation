import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from database import db_dependency
from models import ContactUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/contacts")
async def list_contacts(
    type: Optional[str] = None,
    property_id: Optional[str] = None,
    is_known: Optional[bool] = None,
    db=Depends(db_dependency),
):
    conditions, params = [], []

    if type:
        types = [t.strip() for t in type.split(",")]
        placeholders = ",".join("?" * len(types))
        conditions.append(f"c.type IN ({placeholders})")
        params.extend(types)

    if property_id:
        conditions.append("c.property_id = ?")
        params.append(property_id)

    if is_known is not None:
        conditions.append("c.is_known = ?")
        params.append(1 if is_known else 0)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with db.execute(f"""
        SELECT c.id, c.name, c.email, c.phone, c.type, c.role, c.unit,
               c.property_id, c.is_known, c.total_messages, c.total_threads,
               c.sentiment_avg, c.last_seen, c.first_seen,
               p.name as property_name
        FROM contacts c
        LEFT JOIN properties p ON c.property_id = p.id
        {where}
        ORDER BY c.name
    """, params) as cur:
        contacts = [dict(r) for r in await cur.fetchall()]

    return {"contacts": contacts, "total": len(contacts)}


@router.get("/contacts/{contact_id}")
async def get_contact(contact_id: int, db=Depends(db_dependency)):
    from knowledge_base import get_contact_context
    ctx = await get_contact_context(db, contact_id)
    if not ctx:
        raise HTTPException(404, "Contact not found")

    # All threads for this contact
    async with db.execute("""
        SELECT id, subject, category, urgency_level, urgency_score, status,
               ai_summary, last_message_at, days_open, follow_up_count
        FROM threads
        WHERE primary_contact_id=?
        ORDER BY last_message_at DESC
    """, (contact_id,)) as c:
        threads = [dict(r) for r in await c.fetchall()]

    # Recent messages
    async with db.execute("""
        SELECT id, thread_id, timestamp, sender_type, subject, body
        FROM messages WHERE contact_id=?
        ORDER BY timestamp DESC LIMIT 20
    """, (contact_id,)) as c:
        messages = [dict(r) for r in await c.fetchall()]

    return {"contact": ctx, "threads": threads, "recent_messages": messages}


@router.patch("/contacts/{contact_id}")
async def update_contact(contact_id: int, body: ContactUpdate, db=Depends(db_dependency)):
    async with db.execute("SELECT id FROM contacts WHERE id=?", (contact_id,)) as c:
        if not await c.fetchone():
            raise HTTPException(404, "Contact not found")

    updates, params = [], []
    for field, value in body.model_dump(exclude_none=True).items():
        updates.append(f"{field} = ?")
        params.append(value)

    if not updates:
        raise HTTPException(400, "No fields to update")

    # Re-evaluate is_known
    updates.append("is_known = (CASE WHEN email IS NOT NULL AND (phone IS NOT NULL OR unit IS NOT NULL) THEN 1 ELSE 0 END)")

    params.append(contact_id)
    await db.execute(
        f"UPDATE contacts SET {', '.join(updates)} WHERE id=?", params
    )
    await db.commit()

    from knowledge_base import get_contact_context
    return await get_contact_context(db, contact_id)
