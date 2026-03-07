import json
import logging
import os

from fastapi import APIRouter, Depends
from database import db_dependency
from models import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()

PROPERTY_MAP = {
    "citynorth": "prop_001",
    "reds works": "prop_002",
    "reds": "prop_002",
    "graylings": "prop_003",
    "ilah": "prop_004",
    "thornbury": "prop_005",
}

CHAT_SYSTEM = """You are a property management AI assistant. The user asked a natural language question
about their property portfolio. You have been given matching threads from the database.

Answer their question concisely and helpfully. Return JSON:
{
  "response": "Natural language answer to the question (2-4 sentences)",
  "suggested_export": "open_issues | tenant_contacts | overdue_responses | property_report | null"
}

Respond ONLY with valid JSON."""


def _parse_query(query: str) -> dict:
    """Extract filters from a natural language query."""
    filters = {}
    q = query.lower()

    for name, pid in PROPERTY_MAP.items():
        if name in q:
            filters["property_id"] = pid
            break

    if any(w in q for w in ["critical", "emergency", "urgent"]):
        filters["urgency"] = "critical,high"
    elif "high" in q:
        filters["urgency"] = "high"
    elif "medium" in q:
        filters["urgency"] = "medium"
    elif "low" in q:
        filters["urgency"] = "low"

    if "maintenance" in q or "repair" in q or "leak" in q or "boiler" in q or "heating" in q:
        filters["category"] = "maintenance_emergency,maintenance_urgent,maintenance_routine"
    elif "legal" in q or "rtb" in q or "solicitor" in q:
        filters["category"] = "legal"
    elif "payment" in q or "rent" in q or "invoice" in q or "arrears" in q:
        filters["category"] = "payment"
    elif "complaint" in q:
        filters["category"] = "complaint"
    elif "prospect" in q or "viewing" in q:
        filters["category"] = "prospect"

    if "unresolved" in q or "open" in q or "outstanding" in q:
        filters["status"] = "open"
    elif "resolved" in q or "closed" in q:
        filters["status"] = "resolved"
    elif "in progress" in q or "in_progress" in q:
        filters["status"] = "in_progress"

    return filters


@router.post("/chat")
async def chat(body: ChatRequest, db=Depends(db_dependency)):
    from ai_pipeline import _call_gemini_with_retry as _call_claude_with_retry

    filters = _parse_query(body.query)
    conditions, params = [], []

    if filters.get("property_id"):
        conditions.append("property_id = ?")
        params.append(filters["property_id"])

    if filters.get("urgency"):
        levels = filters["urgency"].split(",")
        placeholders = ",".join("?" * len(levels))
        conditions.append(f"urgency_level IN ({placeholders})")
        params.extend(levels)

    if filters.get("category"):
        cats = filters["category"].split(",")
        placeholders = ",".join("?" * len(cats))
        conditions.append(f"category IN ({placeholders})")
        params.extend(cats)

    if filters.get("status"):
        statuses = filters["status"].split(",")
        placeholders = ",".join("?" * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)

    # Also do a text search if no filters matched
    if not conditions:
        # Search subject and summary
        words = [w for w in body.query.split() if len(w) > 3]
        if words:
            conditions.append("(subject LIKE ? OR ai_summary LIKE ?)")
            params.extend([f"%{words[0]}%", f"%{words[0]}%"])

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with db.execute(f"""
        SELECT id, subject, property_name, category, urgency_level, urgency_score,
               ai_summary, status, days_open, follow_up_count
        FROM threads {where}
        ORDER BY urgency_score DESC NULLS LAST
        LIMIT 15
    """, params) as c:
        threads = [dict(r) for r in await c.fetchall()]

    # Send to Claude for NL response
    thread_text = "\n".join(
        f"- [{t['urgency_level'] or 'unanalysed'}] {t['subject']} | {t['property_name'] or 'N/A'} | {t['ai_summary'] or 'No summary'}"
        for t in threads
    ) or "No matching threads found."

    user_msg = f"Question: {body.query}\n\nMatching threads ({len(threads)} results):\n{thread_text}"

    try:
        result = await _call_claude_with_retry(CHAT_SYSTEM, user_msg)
    except Exception as e:
        result = {"response": f"Query processed. Found {len(threads)} matching threads.", "suggested_export": None}

    return {
        "response": result.get("response", ""),
        "threads": threads,
        "filters_applied": filters,
        "suggested_export": result.get("suggested_export"),
    }
