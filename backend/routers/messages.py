import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from database import db_dependency
from models import IncomingEmail, SimulateRequest

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_json_field(val) -> list:
    try:
        return json.loads(val or "[]")
    except Exception:
        return []


@router.get("/messages")
async def list_messages(
    thread_id: Optional[str] = None,
    property_id: Optional[str] = None,
    sender_type: Optional[str] = None,
    unread: Optional[bool] = None,
    search: Optional[str] = None,
    db=Depends(db_dependency),
):
    conditions, params = [], []

    if thread_id:
        conditions.append("thread_id = ?")
        params.append(thread_id)
    if property_id:
        conditions.append("property_id = ?")
        params.append(property_id)
    if sender_type:
        types = [s.strip() for s in sender_type.split(",")]
        placeholders = ",".join("?" * len(types))
        conditions.append(f"sender_type IN ({placeholders})")
        params.extend(types)
    if unread is True:
        conditions.append("is_read = 0")
    if search:
        conditions.append("(subject LIKE ? OR body LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with db.execute(f"""
        SELECT id, thread_id, thread_position, timestamp, sender_name, sender_email,
               sender_type, sender_unit, sender_role, property_id, recipient, cc,
               subject, body, attachments, is_read, created_at
        FROM messages {where}
        ORDER BY timestamp DESC
        LIMIT 200
    """, params) as c:
        messages = [dict(r) for r in await c.fetchall()]

    for m in messages:
        m["attachments"] = _parse_json_field(m.get("attachments"))

    return {"messages": messages, "total": len(messages)}


@router.post("/messages/incoming")
async def incoming_email(body: IncomingEmail, db=Depends(db_dependency)):
    """Process a new incoming email through the full EmailProcessor pipeline."""
    from email_processor import EmailProcessor
    from routers.ws import manager

    email_dict = {
        "sender_name": body.sender_name,
        "sender_email": body.sender_email,
        "sender_type": body.sender_type,
        "sender_unit": body.sender_unit,
        "to": body.to,
        "subject": body.subject,
        "body": body.body,
        "attachments": body.attachments or [],
        "property_id": body.property_id,
    }

    processor = EmailProcessor()
    result = await processor.process_new_email(db, email_dict, ws_manager=manager)
    return result


@router.post("/demo/simulate-email")
async def simulate_email(body: SimulateRequest, db=Depends(db_dependency)):
    """Run a pre-written demo scenario through the full email pipeline."""
    from email_processor import EmailProcessor, DEMO_SCENARIOS
    from routers.ws import manager

    scenario = body.scenario
    if scenario not in DEMO_SCENARIOS:
        raise HTTPException(
            400,
            f"Unknown scenario '{scenario}'. "
            f"Available: {', '.join(DEMO_SCENARIOS.keys())}"
        )

    email_dict = dict(DEMO_SCENARIOS[scenario])
    processor = EmailProcessor()
    result = await processor.process_new_email(db, email_dict, ws_manager=manager)
    return result
