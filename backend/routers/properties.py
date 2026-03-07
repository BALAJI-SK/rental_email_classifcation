import json
import logging
from fastapi import APIRouter, Depends, HTTPException
from database import db_dependency

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/properties")
async def list_properties(db=Depends(db_dependency)):
    async with db.execute("SELECT * FROM properties ORDER BY name") as c:
        props = [dict(r) for r in await c.fetchall()]

    for prop in props:
        pid = prop["id"]
        async with db.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN urgency_level='critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN urgency_level='high' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN urgency_level='medium' THEN 1 ELSE 0 END) as medium,
                SUM(CASE WHEN urgency_level='low' THEN 1 ELSE 0 END) as low,
                SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) as unread,
                SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) as open_count
            FROM threads WHERE property_id=?
        """, (pid,)) as c:
            stats = dict(await c.fetchone())
        prop["thread_stats"] = stats

    return {"properties": props}


@router.get("/properties/{property_id}")
async def get_property(property_id: str, db=Depends(db_dependency)):
    async with db.execute("SELECT * FROM properties WHERE id=?", (property_id,)) as c:
        prop = await c.fetchone()
    if not prop:
        raise HTTPException(404, "Property not found")
    prop = dict(prop)

    async with db.execute("""
        SELECT id, subject, category, urgency_level, urgency_score, status,
               ai_summary, message_count, days_open, follow_up_count,
               last_message_at, is_read
        FROM threads
        WHERE property_id=?
        ORDER BY urgency_score DESC NULLS LAST
    """, (property_id,)) as c:
        threads = [dict(r) for r in await c.fetchall()]

    async with db.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN urgency_level='critical' THEN 1 ELSE 0 END) as critical,
               SUM(CASE WHEN urgency_level='high' THEN 1 ELSE 0 END) as high,
               SUM(CASE WHEN urgency_level='medium' THEN 1 ELSE 0 END) as medium,
               SUM(CASE WHEN urgency_level='low' THEN 1 ELSE 0 END) as low
        FROM threads WHERE property_id=?
    """, (property_id,)) as c:
        stats = dict(await c.fetchone())

    async with db.execute("""
        SELECT id, name, email, phone, unit, type, is_known, total_messages
        FROM contacts WHERE property_id=?
        ORDER BY type, name
    """, (property_id,)) as c:
        contacts = [dict(r) for r in await c.fetchall()]

    return {
        "property": prop,
        "threads": threads,
        "thread_stats": stats,
        "contacts": contacts,
    }


@router.get("/properties/{property_id}/health")
async def property_health(property_id: str, db=Depends(db_dependency)):
    async with db.execute("SELECT name FROM properties WHERE id=?", (property_id,)) as c:
        row = await c.fetchone()
    if not row:
        raise HTTPException(404, "Property not found")

    async with db.execute("""
        SELECT urgency_level, COUNT(*) as cnt
        FROM threads WHERE property_id=? AND analysed_at IS NOT NULL
        GROUP BY urgency_level
    """, (property_id,)) as c:
        urg = {r[0]: r[1] for r in await c.fetchall()}

    total = sum(urg.values())
    critical = urg.get("critical", 0)
    high = urg.get("high", 0)
    if total == 0:
        health_score = 100
    else:
        health_score = max(0, 100 - (critical * 20 + high * 10))

    async with db.execute("""
        SELECT category, COUNT(*) as cnt FROM threads
        WHERE property_id=? GROUP BY category ORDER BY cnt DESC LIMIT 3
    """, (property_id,)) as c:
        top_categories = [dict(r) for r in await c.fetchall()]

    async with db.execute("""
        SELECT id FROM pattern_alerts
        WHERE property_id=? AND is_dismissed=0
    """, (property_id,)) as c:
        alert_count = len(await c.fetchall())

    return {
        "property_id": property_id,
        "property_name": row[0],
        "health_score": health_score,
        "urgency_breakdown": urg,
        "total_threads": total,
        "top_categories": top_categories,
        "active_alerts": alert_count,
    }
