import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from database import db_dependency

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/dashboard")
async def get_dashboard(db=Depends(db_dependency)):
    """Stats, urgency counts, top 5 priorities, pattern alerts, morning brief."""

    # Try cache first
    async with db.execute("SELECT * FROM dashboard_cache WHERE id=1") as c:
        cache = await c.fetchone()

    if cache:
        cache = dict(cache)
    else:
        cache = {}

    # Live counts (always fresh)
    async with db.execute("SELECT COUNT(*) FROM messages") as c:
        total_messages = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM messages WHERE is_read=0") as c:
        unread_messages = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM threads") as c:
        total_threads = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM threads WHERE analysed_at IS NOT NULL") as c:
        analysed = (await c.fetchone())[0]

    # Urgency counts from threads
    async with db.execute("""
        SELECT urgency_level, COUNT(*) FROM threads
        WHERE urgency_level IS NOT NULL
        GROUP BY urgency_level
    """) as c:
        urg_rows = await c.fetchall()
    urg = {r[0]: r[1] for r in urg_rows}

    # Top 5 threads by urgency
    async with db.execute("""
        SELECT id, subject, property_name, category, urgency_level, urgency_score,
               ai_summary, sentiment, follow_up_count, days_open, status,
               last_message_at, is_read, risk_flags
        FROM threads
        WHERE urgency_score IS NOT NULL
        ORDER BY urgency_score DESC NULLS LAST
        LIMIT 5
    """) as c:
        top = [dict(r) for r in await c.fetchall()]

    for t in top:
        for field in ("risk_flags",):
            try:
                t[field] = json.loads(t.get(field) or "[]")
            except Exception:
                t[field] = []

    # Active pattern alerts
    async with db.execute("""
        SELECT id, pattern_type, title, description, severity, property_id,
               related_thread_ids, created_at
        FROM pattern_alerts
        WHERE is_dismissed=0
        ORDER BY created_at DESC
        LIMIT 10
    """) as c:
        alerts = [dict(r) for r in await c.fetchall()]

    return {
        "stats": {
            "total_messages": total_messages,
            "unread_messages": unread_messages,
            "total_threads": total_threads,
            "analysed": analysed,
            "unanalysed": total_threads - analysed,
            "critical": urg.get("critical", 0),
            "high": urg.get("high", 0),
            "medium": urg.get("medium", 0),
            "low": urg.get("low", 0),
            "pattern_alerts": len(alerts),
        },
        "top_priorities": top,
        "pattern_alerts": alerts,
        "morning_brief": cache.get("morning_brief"),
        "voice_script": cache.get("voice_script"),
        "updated_at": cache.get("updated_at"),
    }


@router.get("/dashboard/morning-brief")
async def get_morning_brief(db=Depends(db_dependency)):
    async with db.execute("SELECT morning_brief, voice_script, updated_at FROM dashboard_cache WHERE id=1") as c:
        row = await c.fetchone()
    if not row or not row[0]:
        return {"morning_brief": None, "voice_script": None, "updated_at": None}
    return {"morning_brief": row[0], "voice_script": row[1], "updated_at": row[2]}


@router.post("/dashboard/morning-brief")
async def generate_morning_brief(db=Depends(db_dependency)):
    from ai_pipeline import generate_morning_brief as _generate
    result = await _generate(db)
    return result


@router.get("/dashboard/patterns")
async def get_patterns(db=Depends(db_dependency)):
    async with db.execute("""
        SELECT id, pattern_type, title, description, severity, property_id,
               related_thread_ids, is_dismissed, created_at
        FROM pattern_alerts
        WHERE is_dismissed=0
        ORDER BY created_at DESC
    """) as c:
        alerts = [dict(r) for r in await c.fetchall()]
    return {"alerts": alerts, "total": len(alerts)}


@router.post("/dashboard/patterns/{alert_id}/dismiss")
async def dismiss_pattern(alert_id: int, db=Depends(db_dependency)):
    async with db.execute("SELECT id FROM pattern_alerts WHERE id=?", (alert_id,)) as c:
        if not await c.fetchone():
            raise HTTPException(404, "Alert not found")
    await db.execute(
        "UPDATE pattern_alerts SET is_dismissed=1 WHERE id=?", (alert_id,)
    )
    await db.commit()
    return {"status": "dismissed"}
