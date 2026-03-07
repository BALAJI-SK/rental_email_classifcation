import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from database import db_dependency, DB_PATH
from models import ThreadUpdate

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_json_field(val) -> list:
    try:
        return json.loads(val or "[]")
    except Exception:
        return []


def _build_filter(
    urgency: Optional[str], property_id: Optional[str],
    category: Optional[str], status: Optional[str], search: Optional[str]
) -> tuple[str, list]:
    conditions, params = [], []

    if urgency:
        levels = [u.strip() for u in urgency.split(",")]
        placeholders = ",".join("?" * len(levels))
        conditions.append(f"urgency_level IN ({placeholders})")
        params.extend(levels)

    if property_id:
        conditions.append("property_id = ?")
        params.append(property_id)

    if category:
        cats = [c.strip() for c in category.split(",")]
        placeholders = ",".join("?" * len(cats))
        conditions.append(f"category IN ({placeholders})")
        params.extend(cats)

    if status:
        statuses = [s.strip() for s in status.split(",")]
        placeholders = ",".join("?" * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)

    if search:
        conditions.append("(subject LIKE ? OR ai_summary LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


@router.get("/threads")
async def list_threads(
    urgency: Optional[str] = None,
    property_id: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    sort: str = Query("urgency_score", enum=["urgency_score", "last_message_at", "days_open"]),
    page: int = 1,
    per_page: int = 20,
    db=Depends(db_dependency),
):
    where, params = _build_filter(urgency, property_id, category, status, search)

    sort_map = {
        "urgency_score": "urgency_score DESC NULLS LAST, last_message_at DESC",
        "last_message_at": "last_message_at DESC",
        "days_open": "days_open DESC",
    }
    order = sort_map.get(sort, "urgency_score DESC NULLS LAST, last_message_at DESC")

    # Count total
    async with db.execute(f"SELECT COUNT(*) FROM threads {where}", params) as c:
        total = (await c.fetchone())[0]

    offset = (page - 1) * per_page
    async with db.execute(f"""
        SELECT id, subject, property_id, property_name, category, urgency_level,
               urgency_score, status, ai_summary, sentiment, sentiment_trend,
               message_count, follow_up_count, days_open, participant_names,
               participant_types, first_message_at, last_message_at, is_read,
               risk_flags, urgency_reasons, analysed_at
        FROM threads {where}
        ORDER BY {order}
        LIMIT ? OFFSET ?
    """, params + [per_page, offset]) as c:
        rows = [dict(r) for r in await c.fetchall()]

    for t in rows:
        for f in ("risk_flags", "urgency_reasons", "participant_names", "participant_types"):
            t[f] = _parse_json_field(t.get(f))

    return {"threads": rows, "total": total, "page": page, "per_page": per_page}


@router.get("/threads/{thread_id}")
async def get_thread(thread_id: str, db=Depends(db_dependency)):
    async with db.execute("SELECT * FROM threads WHERE id=?", (thread_id,)) as c:
        thread = await c.fetchone()
    if not thread:
        raise HTTPException(404, "Thread not found")
    thread = dict(thread)

    for f in ("risk_flags", "urgency_reasons", "participant_names",
              "participant_types", "recommended_actions"):
        thread[f] = _parse_json_field(thread.get(f))

    # Messages
    async with db.execute("""
        SELECT id, thread_position, timestamp, sender_name, sender_email,
               sender_type, sender_unit, sender_role, subject, body, attachments,
               is_read, contact_id
        FROM messages WHERE thread_id=? ORDER BY thread_position
    """, (thread_id,)) as c:
        messages = [dict(r) for r in await c.fetchall()]

    for m in messages:
        m["attachments"] = _parse_json_field(m.get("attachments"))

    # Contact
    contact = None
    if thread.get("primary_contact_id"):
        from knowledge_base import get_contact_context
        contact = await get_contact_context(db, thread["primary_contact_id"])

    # Escalation history
    async with db.execute("""
        SELECT id, old_score, new_score, old_level, new_level, reason, triggered_by, created_at
        FROM escalation_history WHERE thread_id=? ORDER BY created_at
    """, (thread_id,)) as c:
        escalation_history = [dict(r) for r in await c.fetchall()]

    # Mark as read
    await db.execute(
        "UPDATE threads SET is_read=1 WHERE id=?", (thread_id,)
    )
    await db.execute(
        "UPDATE messages SET is_read=1 WHERE thread_id=?", (thread_id,)
    )
    await db.commit()

    return {
        "thread": thread,
        "messages": messages,
        "contact": contact,
        "escalation_history": escalation_history,
    }


@router.patch("/threads/{thread_id}")
async def update_thread(thread_id: str, body: ThreadUpdate, db=Depends(db_dependency)):
    async with db.execute("SELECT id FROM threads WHERE id=?", (thread_id,)) as c:
        if not await c.fetchone():
            raise HTTPException(404, "Thread not found")

    updates, params = [], []
    if body.status is not None:
        updates.append("status = ?")
        params.append(body.status)
        if body.status == "resolved":
            updates.append("resolved_at = ?")
            params.append(datetime.now(timezone.utc).isoformat())

    if body.is_read is not None:
        updates.append("is_read = ?")
        params.append(body.is_read)

    if not updates:
        raise HTTPException(400, "No fields to update")

    params.append(thread_id)
    await db.execute(f"UPDATE threads SET {', '.join(updates)} WHERE id=?", params)
    await db.commit()

    # Broadcast thread update via WebSocket
    from routers.ws import manager
    async with db.execute("""
        SELECT id, subject, urgency_level, urgency_score, status, is_read,
               ai_summary, category
        FROM threads WHERE id=?
    """, (thread_id,)) as c:
        updated = dict(await c.fetchone())
    await manager.broadcast({"event": "thread_updated", "thread_id": thread_id, "data": updated})

    return updated


@router.post("/threads/{thread_id}/analyse")
async def analyse_single_thread(thread_id: str, db=Depends(db_dependency)):
    async with db.execute("SELECT id FROM threads WHERE id=?", (thread_id,)) as c:
        if not await c.fetchone():
            raise HTTPException(404, "Thread not found")

    from ai_pipeline import analyse_thread
    from workflow_engine import process_thread
    from routers.ws import manager

    await manager.broadcast({"event": "analysis_started", "thread_id": thread_id})
    result = await analyse_thread(db, thread_id)
    await process_thread(db, thread_id)
    await manager.broadcast({
        "event": "analysis_complete", "thread_id": thread_id, "data": result
    })
    return result


@router.get("/threads/{thread_id}/draft")
async def get_draft(thread_id: str, db=Depends(db_dependency)):
    async with db.execute(
        "SELECT draft_response FROM threads WHERE id=?", (thread_id,)
    ) as c:
        row = await c.fetchone()
    if not row:
        raise HTTPException(404, "Thread not found")
    return {"thread_id": thread_id, "draft": row[0]}


@router.get("/threads/{thread_id}/escalation-history")
async def get_escalation_history(thread_id: str, db=Depends(db_dependency)):
    async with db.execute("""
        SELECT id, old_score, new_score, old_level, new_level, reason, triggered_by, created_at
        FROM escalation_history WHERE thread_id=? ORDER BY created_at
    """, (thread_id,)) as c:
        history = [dict(r) for r in await c.fetchall()]
    return {"thread_id": thread_id, "history": history}


# ── Bulk analysis ──────────────────────────────────────────────

async def _run_bulk_analysis():
    import aiosqlite
    from ai_pipeline import analyse_all_threads
    from workflow_engine import run_portfolio_rules
    from routers.ws import manager

    async with aiosqlite.connect(DB_PATH) as db:
        import aiosqlite as _aio
        db.row_factory = _aio.Row
        await analyse_all_threads(db, ws_manager=manager)
        new_alerts = await run_portfolio_rules(db)
        for alert in new_alerts:
            await manager.broadcast({"event": "pattern_detected", "data": alert})


@router.post("/analyse/all")
async def analyse_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(_run_bulk_analysis)
    return {"status": "started", "message": "Analysis running in background. Watch WebSocket for progress."}
