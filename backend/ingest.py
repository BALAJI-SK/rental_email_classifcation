import json
import os
import asyncio
import re
from datetime import datetime, timezone

import aiosqlite
from database import DB_PATH, init_db

DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "proptech-test-data__1_.json")

SEED_CONTRACTORS = [
    {
        "company_name": "Dublin Maintenance Services",
        "contact_person": "Ronan Keane",
        "email": "emergencyplumbing@dublinmaintenance.ie",
        "phone": "+353 1 555 0101",
        "specialties": ["plumbing", "boiler", "heating", "general"],
        "service_areas": ["prop_001", "prop_002", "prop_003", "prop_004", "prop_005"],
        "avg_rating": 4.2,
        "total_jobs": 47,
        "avg_response_time_hours": 2.5,
        "avg_price_rating": "mid",
        "is_emergency_available": True,
    },
    {
        "company_name": "Emerald Electrical",
        "contact_person": "Sinead Flynn",
        "email": "sinead@emeraldelectrical.ie",
        "phone": "+353 1 555 0202",
        "specialties": ["electrical", "fire_safety", "smart_locks", "lighting"],
        "service_areas": ["prop_001", "prop_002", "prop_003"],
        "avg_rating": 4.7,
        "total_jobs": 31,
        "avg_response_time_hours": 4.0,
        "avg_price_rating": "premium",
        "is_emergency_available": True,
    },
    {
        "company_name": "Coyne Fire & Safety",
        "contact_person": "Mairead Coyne",
        "email": "mairead.coyne@coynefiresafety.ie",
        "phone": "+353 1 555 0303",
        "specialties": ["fire_safety", "emergency_lighting", "fire_panel", "compliance"],
        "service_areas": ["prop_001", "prop_002", "prop_003", "prop_004", "prop_005"],
        "avg_rating": 4.5,
        "total_jobs": 22,
        "avg_response_time_hours": 6.0,
        "avg_price_rating": "mid",
        "is_emergency_available": False,
    },
    {
        "company_name": "QuickFix Plumbing",
        "contact_person": "Darren Murphy",
        "email": "darren@quickfixplumbing.ie",
        "phone": "+353 1 555 0404",
        "specialties": ["plumbing", "boiler", "heating", "bathroom"],
        "service_areas": ["prop_001", "prop_003", "prop_005"],
        "avg_rating": 3.8,
        "total_jobs": 15,
        "avg_response_time_hours": 1.5,
        "avg_price_rating": "budget",
        "is_emergency_available": True,
    },
    {
        "company_name": "AllStar Property Maintenance",
        "contact_person": "Ciaran Dempsey",
        "email": "ciaran@allstarpm.ie",
        "phone": "+353 1 555 0505",
        "specialties": ["general", "painting", "carpentry", "locks", "fencing", "gutters"],
        "service_areas": ["prop_004", "prop_005"],
        "avg_rating": 4.0,
        "total_jobs": 38,
        "avg_response_time_hours": 8.0,
        "avg_price_rating": "budget",
        "is_emergency_available": False,
    },
    {
        "company_name": "Greenway Pest Control",
        "contact_person": "Aoife Brennan",
        "email": "aoife@greenwaypest.ie",
        "phone": "+353 1 555 0606",
        "specialties": ["pest_control", "fumigation", "rodent", "insect"],
        "service_areas": ["prop_001", "prop_002", "prop_003", "prop_004", "prop_005"],
        "avg_rating": 4.6,
        "total_jobs": 8,
        "avg_response_time_hours": 12.0,
        "avg_price_rating": "mid",
        "is_emergency_available": False,
    },
    {
        "company_name": "SecureTech Ireland",
        "contact_person": "Niall Gallagher",
        "email": "niall@securetech.ie",
        "phone": "+353 1 555 0707",
        "specialties": ["smart_locks", "cctv", "access_control", "security", "intercom"],
        "service_areas": ["prop_001", "prop_002", "prop_004"],
        "avg_rating": 4.3,
        "total_jobs": 19,
        "avg_response_time_hours": 5.0,
        "avg_price_rating": "premium",
        "is_emergency_available": True,
    },
]


def _extract_phone(body: str) -> str | None:
    """Pull a phone number from an email body."""
    match = re.search(r"(\+?[\d\s\-]{10,15})", body)
    if match:
        candidate = match.group(1).strip()
        digits = re.sub(r"\D", "", candidate)
        if len(digits) >= 9:
            return candidate
    return None


def _is_known(sender: dict, phone: str | None) -> bool:
    return bool(sender.get("email") and sender.get("name") and (phone or sender.get("unit")))


async def _find_or_create_contact(db, sender: dict, body: str, first_seen: str, last_seen: str) -> int:
    """Return contact id, creating if needed. Deduplicate by email."""
    email = sender.get("email")
    phone = _extract_phone(body)

    if email:
        async with db.execute("SELECT id FROM contacts WHERE email = ?", (email,)) as c:
            row = await c.fetchone()
        if row:
            return row[0]

    # Create new contact
    known = _is_known(sender, phone)
    await db.execute(
        """INSERT INTO contacts
           (name, email, phone, type, role, unit, property_id,
            is_known, total_messages, first_seen, last_seen)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            sender.get("name", "Unknown"),
            email,
            phone,
            sender.get("type", "external"),
            sender.get("role"),
            sender.get("unit"),
            sender.get("property_id"),
            known,
            first_seen,
            last_seen,
        ),
    )
    async with db.execute("SELECT last_insert_rowid()") as c:
        return (await c.fetchone())[0]


async def ingest_data():
    with open(DATA_PATH, "r") as f:
        data = json.load(f)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        # Check if already ingested
        async with db.execute("SELECT COUNT(*) FROM messages") as cursor:
            count = (await cursor.fetchone())[0]
        if count > 0:
            print(f"Data already ingested ({count} messages). Skipping.")
            return

        # ── 1. Properties ─────────────────────────────────────────
        props_by_id = {}
        for prop in data["metadata"]["properties"]:
            await db.execute(
                "INSERT OR IGNORE INTO properties (id, name, type, units, manager) VALUES (?, ?, ?, ?, ?)",
                (prop["id"], prop["name"], prop["type"], prop["units"], prop["manager"]),
            )
            props_by_id[prop["id"]] = prop
        await db.commit()

        # ── 2. Build contacts from all senders ────────────────────
        # Pre-pass: collect first/last seen per email
        sender_timestamps: dict[str, list[str]] = {}
        for email in data["emails"]:
            s = email.get("from", {})
            key = s.get("email") or s.get("name", "unknown")
            sender_timestamps.setdefault(key, []).append(email["timestamp"])

        contact_cache: dict[str, int] = {}  # email/name -> contact_id

        # ── 3. Insert messages, creating contacts on the fly ──────
        for email in data["emails"]:
            sender = email.get("from", {})
            key = sender.get("email") or sender.get("name", "unknown")
            timestamps = sender_timestamps[key]
            first_seen = min(timestamps)
            last_seen = max(timestamps)

            if key not in contact_cache:
                contact_id = await _find_or_create_contact(
                    db, sender, email.get("body", ""), first_seen, last_seen
                )
                contact_cache[key] = contact_id
            else:
                contact_id = contact_cache[key]

            attachments = json.dumps(email.get("attachments", []))
            await db.execute(
                """INSERT OR IGNORE INTO messages
                   (id, thread_id, thread_position, timestamp, sender_name, sender_email,
                    sender_type, sender_unit, sender_role, property_id, contact_id,
                    recipient, cc, subject, body, attachments, is_read)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    email["id"],
                    email["thread_id"],
                    email["thread_position"],
                    email["timestamp"],
                    sender.get("name", ""),
                    sender.get("email"),
                    sender.get("type", ""),
                    sender.get("unit"),
                    sender.get("role"),
                    sender.get("property_id"),
                    contact_id,
                    email.get("to"),
                    email.get("cc"),
                    email["subject"],
                    email["body"],
                    attachments,
                    email.get("read", False),
                ),
            )
        await db.commit()

        # Update contact stats (total_messages, last_seen)
        await db.execute("""
            UPDATE contacts SET
                total_messages = (
                    SELECT COUNT(*) FROM messages WHERE messages.contact_id = contacts.id
                ),
                last_seen = (
                    SELECT MAX(timestamp) FROM messages WHERE messages.contact_id = contacts.id
                )
        """)
        await db.commit()

        # ── 4. Build threads ──────────────────────────────────────
        async with db.execute(
            "SELECT * FROM messages ORDER BY thread_id, thread_position"
        ) as cursor:
            all_messages = [dict(r) for r in await cursor.fetchall()]

        threads_map: dict[str, list[dict]] = {}
        for msg in all_messages:
            threads_map.setdefault(msg["thread_id"], []).append(msg)

        today = datetime.now(timezone.utc)

        for tid, msgs in threads_map.items():
            msgs_sorted = sorted(msgs, key=lambda m: m["thread_position"])
            first = msgs_sorted[0]

            property_id = next((m["property_id"] for m in msgs_sorted if m["property_id"]), None)
            property_name = props_by_id[property_id]["name"] if property_id in props_by_id else None

            # Primary contact: first non-internal sender (prefer tenant)
            primary_msg = next(
                (m for m in msgs_sorted if m["sender_type"] == "tenant"),
                next((m for m in msgs_sorted if m["sender_type"] not in ("internal",)), msgs_sorted[0]),
            )
            primary_contact_id = primary_msg.get("contact_id")

            # Follow-up count: messages from same sender as position-1, at position > 1
            first_sender_email = msgs_sorted[0].get("sender_email")
            follow_up_count = sum(
                1 for m in msgs_sorted
                if m["thread_position"] > 1 and m.get("sender_email") == first_sender_email
            )

            timestamps = [m["timestamp"] for m in msgs_sorted]
            first_ts = min(timestamps)
            last_ts = max(timestamps)

            try:
                first_dt = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
                days_open = (today - first_dt).days
            except Exception:
                days_open = 0

            participant_names = list({m["sender_name"] for m in msgs_sorted if m["sender_name"]})
            participant_types = list({m["sender_type"] for m in msgs_sorted if m["sender_type"]})
            is_read = all(m["is_read"] for m in msgs_sorted)

            await db.execute(
                """INSERT OR IGNORE INTO threads
                   (id, subject, property_id, property_name, message_count,
                    follow_up_count, days_open, participant_names, participant_types,
                    primary_contact_id, first_message_at, last_message_at, is_read)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tid,
                    first["subject"],
                    property_id,
                    property_name,
                    len(msgs_sorted),
                    follow_up_count,
                    days_open,
                    json.dumps(participant_names),
                    json.dumps(participant_types),
                    primary_contact_id,
                    first_ts,
                    last_ts,
                    is_read,
                ),
            )

        # Update contacts.total_threads
        await db.execute("""
            UPDATE contacts SET
                total_threads = (
                    SELECT COUNT(*) FROM threads
                    WHERE threads.primary_contact_id = contacts.id
                )
        """)
        await db.commit()

        # ── 5. Seed contractors ───────────────────────────────────
        async with db.execute("SELECT COUNT(*) FROM contractors") as c:
            if (await c.fetchone())[0] == 0:
                for contractor in SEED_CONTRACTORS:
                    await db.execute(
                        """INSERT INTO contractors
                           (company_name, contact_person, email, phone, specialties,
                            service_areas, avg_rating, total_jobs, avg_response_time_hours,
                            avg_price_rating, is_emergency_available)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            contractor["company_name"],
                            contractor["contact_person"],
                            contractor["email"],
                            contractor["phone"],
                            json.dumps(contractor["specialties"]),
                            json.dumps(contractor["service_areas"]),
                            contractor["avg_rating"],
                            contractor["total_jobs"],
                            contractor["avg_response_time_hours"],
                            contractor["avg_price_rating"],
                            contractor["is_emergency_available"],
                        ),
                    )
                await db.commit()
                print(f"Seeded {len(SEED_CONTRACTORS)} contractors.")

        # ── 6. Print summary ──────────────────────────────────────
        async with db.execute("SELECT COUNT(*) FROM messages") as c:
            print(f"Messages: {(await c.fetchone())[0]}")
        async with db.execute("SELECT COUNT(*) FROM threads") as c:
            print(f"Threads:  {(await c.fetchone())[0]}")
        async with db.execute("SELECT COUNT(*) FROM contacts") as c:
            print(f"Contacts: {(await c.fetchone())[0]}")
        async with db.execute("SELECT COUNT(*) FROM contacts WHERE is_known = 1") as c:
            print(f"  Known:  {(await c.fetchone())[0]}")
        async with db.execute("SELECT COUNT(*) FROM contractors") as c:
            print(f"Contractors: {(await c.fetchone())[0]}")


async def main():
    await init_db()
    await ingest_data()


if __name__ == "__main__":
    asyncio.run(main())
