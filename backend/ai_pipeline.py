import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

logger = logging.getLogger(__name__)

MODEL = os.getenv("ANALYSIS_MODEL", "gemini-3-flash-preview")
BATCH_SIZE = int(os.getenv("ANALYSIS_BATCH_SIZE", "5"))

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


# ──────────────────────────────────────────────────────────────
# JSON PARSING HELPERS
# ──────────────────────────────────────────────────────────────

def _strip_markdown(text: str) -> str:
    """Remove ```json ... ``` or ``` ... ``` wrappers Claude sometimes returns."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json(text: str) -> dict:
    """Parse JSON, stripping markdown wrapper if needed."""
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        cleaned = _strip_markdown(text)
        return json.loads(cleaned)


# ──────────────────────────────────────────────────────────────
# THREAD ANALYSIS
# ──────────────────────────────────────────────────────────────

THREAD_SYSTEM_PROMPT = """You are an expert AI assistant for Irish property management (BTR and PRS sectors).
Analyse this email thread and return a JSON response.

CONTEXT:
- Property: {property_name} ({property_type}, {units} units)
- Manager: {manager_name}
- Thread has {message_count} messages over {days_span} days
- Contact "{primary_contact_name}" has sent {follow_up_count} follow-up messages
- Contact's overall history: {total_messages_from_contact} total messages, sentiment trend: {contact_sentiment}

RETURN THIS EXACT JSON STRUCTURE:
{{
  "category": "One of: maintenance_emergency, maintenance_urgent, maintenance_routine, lease, payment, complaint, inquiry, contractor, landlord, legal, system_alert, prospect",
  "urgency_level": "One of: critical, high, medium, low",
  "urgency_score": 1-10 integer,
  "urgency_reasons": ["Reason 1 with specific details from messages", "Reason 2", "Reason 3"],
  "summary": "2-3 sentence narrative. Include WHO, WHAT, WHERE (property+unit), WHEN, and CURRENT STATUS. Write for a busy PM with 10 seconds.",
  "sentiment": "One of: positive, neutral, negative, angry, anxious, threatening",
  "sentiment_trend": "One of: improving, stable, declining",
  "recommended_actions": [
    {{
      "action": "Specific concrete action (e.g., 'Call Dublin Maintenance at emergencyplumbing@dublinmaintenance.ie to confirm arrival time')",
      "priority": 1,
      "reasoning": "Why this matters — reference specific details",
      "deadline": "Immediately / Today / Within 48 hours / Before [date]"
    }}
  ],
  "draft_response": "Professional draft email reply to the most recent sender. Address them by first name. Reference specific details. Match appropriate tone — urgent for emergencies, empathetic for complaints, professional for legal, helpful for prospects. If the contact is KNOWN, use their details naturally. If UNKNOWN, include a request for their contact details and unit number.",
  "risk_flags": ["Specific risks (e.g., 'Electrical hazard — water through light fitting', 'RTB complaint deadline approaching')"],
  "auto_escalation_recommendation": "none / escalate / de-escalate — with reasoning if not 'none'"
}}

URGENCY SCORING GUIDE:
- 9-10 CRITICAL: Safety hazard, active damage, legal deadline imminent, security breach
- 7-8 HIGH: Significant issue needing same-day action, legal risk, angry tenant with multiple follow-ups
- 4-6 MEDIUM: Important but not time-critical, standard maintenance, routine inquiries needing response
- 1-3 LOW: Informational, FYI messages, low-priority requests, resolved items

ESCALATION SIGNALS — increase urgency if:
- Multiple follow-ups from same person (persistence = frustration)
- Sentiment declining across messages
- Legal terms mentioned (solicitor, RTB, rights, tribunal, breach)
- Safety keywords (gas, flood, fire, electrical, locked out, mould)
- Time since first message > 3 days with no resolution
- Tenant mentions children, elderly, disability, or health conditions

Respond ONLY with valid JSON. No markdown code blocks, no explanation text."""


def _build_thread_system_prompt(ctx: dict) -> str:
    return THREAD_SYSTEM_PROMPT.format(
        property_name=ctx.get("property_name") or "Unknown Property",
        property_type=ctx.get("property_type") or "BTR",
        units=ctx.get("units") or "N/A",
        manager_name=ctx.get("manager_name") or "Property Manager",
        message_count=ctx.get("message_count", 1),
        days_span=ctx.get("days_span", 0),
        primary_contact_name=ctx.get("primary_contact_name") or "Unknown",
        follow_up_count=ctx.get("follow_up_count", 0),
        total_messages_from_contact=ctx.get("total_messages_from_contact", 1),
        contact_sentiment=ctx.get("contact_sentiment") or "unknown",
    )


def _build_thread_user_message(thread_id: str, subject: str, messages: list[dict]) -> str:
    lines = [f"Thread: {thread_id}", f"Subject: {subject}", ""]
    for msg in messages:
        lines.append(f"--- Message {msg['thread_position']} ---")
        sender_part = f"{msg['sender_name']} ({msg['sender_type']})"
        if msg.get("sender_email"):
            sender_part += f" <{msg['sender_email']}>"
        lines.append(f"From: {sender_part}")
        lines.append(f"Date: {msg['timestamp']}")
        lines.append("")
        lines.append(msg["body"])
        lines.append("")
    return "\n".join(lines)


async def _call_gemini_with_retry(system: str, user: str, max_retries: int = 3) -> dict:
    """Call Gemini API with exponential backoff. Returns parsed JSON dict."""
    # Compatibility aliases
    return await _call_gemini_real(system, user, max_retries)

async def _call_claude_with_retry(system: str, user: str, max_retries: int = 3) -> dict:
    return await _call_gemini_real(system, user, max_retries)


async def _call_gemini_real(system: str, user: str, max_retries: int = 3) -> dict:
    client = get_client()
    delay = 2.0
    last_error = None

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=MODEL,
                contents=user,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    max_output_tokens=2048,
                ),
            )
            raw = response.text
            return _parse_json(raw)
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"JSON parse error (attempt {attempt + 1}): {e}")
        except Exception as e:
            last_error = e
            logger.warning(f"API error (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)
                delay *= 6

    raise RuntimeError(f"Gemini API failed after {max_retries} attempts: {last_error}")


async def analyse_thread(db, thread_id: str) -> dict:
    """
    Fetch thread + messages from DB, call Claude, persist results.
    Returns the analysis dict.
    """
    import aiosqlite  # local import to avoid circular

    db.row_factory = aiosqlite.Row

    # Fetch thread
    async with db.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)) as c:
        thread = await c.fetchone()
    if not thread:
        raise ValueError(f"Thread {thread_id} not found")
    thread = dict(thread)

    # Fetch messages ordered by position
    async with db.execute(
        "SELECT * FROM messages WHERE thread_id = ? ORDER BY thread_position",
        (thread_id,),
    ) as c:
        messages = [dict(r) for r in await c.fetchall()]

    # Fetch property context
    property_ctx = {}
    if thread.get("property_id"):
        async with db.execute(
            "SELECT * FROM properties WHERE id = ?", (thread["property_id"],)
        ) as c:
            prop = await c.fetchone()
            if prop:
                property_ctx = dict(prop)

    # Fetch primary contact context
    contact_ctx = {}
    if thread.get("primary_contact_id"):
        async with db.execute(
            "SELECT * FROM contacts WHERE id = ?", (thread["primary_contact_id"],)
        ) as c:
            contact = await c.fetchone()
            if contact:
                contact_ctx = dict(contact)

    # Calculate days_span
    try:
        first_dt = datetime.fromisoformat(
            thread["first_message_at"].replace("Z", "+00:00")
        )
        last_dt = datetime.fromisoformat(
            thread["last_message_at"].replace("Z", "+00:00")
        )
        days_span = (last_dt - first_dt).days
    except Exception:
        days_span = 0

    ctx = {
        "property_name": property_ctx.get("name") or thread.get("property_name"),
        "property_type": property_ctx.get("type"),
        "units": property_ctx.get("units"),
        "manager_name": property_ctx.get("manager"),
        "message_count": thread["message_count"],
        "days_span": days_span,
        "primary_contact_name": contact_ctx.get("name") or messages[0]["sender_name"],
        "follow_up_count": thread.get("follow_up_count", 0),
        "total_messages_from_contact": contact_ctx.get("total_messages", 1),
        "contact_sentiment": contact_ctx.get("sentiment_avg"),
    }

    system_prompt = _build_thread_system_prompt(ctx)
    user_message = _build_thread_user_message(
        thread_id, thread["subject"], messages
    )

    try:
        analysis = await _call_gemini_with_retry(system_prompt, user_message)
    except Exception as e:
        logger.error(f"Analysis failed for {thread_id}: {e}")
        # Standard fallback for failed analysis
        analysis = {
            "category": "maintenance_routine",
            "urgency_level": "medium",
            "urgency_score": 5,
            "urgency_reasons": ["AI analysis failed"],
            "summary": "Automatic analysis failed for this thread. Please review manually.",
            "sentiment": "neutral",
            "sentiment_trend": "stable",
            "recommended_actions": [{"action": "Manually review", "priority": 1, "reasoning": "AI error", "deadline": "Today"}],
            "draft_response": "Analysis failed, please draft manually.",
            "risk_flags": ["Analysis Failed"],
            "auto_escalation_recommendation": "none"
        }
        await db.execute(
            "UPDATE threads SET status = 'analysis_failed', analysed_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), thread_id),
        )
        await db.commit()
        return {"thread_id": thread_id, "error": str(e)}

    now = datetime.now(timezone.utc).isoformat()

    await db.execute(
        """UPDATE threads SET
            category = ?,
            urgency_level = ?,
            urgency_score = ?,
            urgency_reasons = ?,
            ai_summary = ?,
            recommended_actions = ?,
            draft_response = ?,
            sentiment = ?,
            sentiment_trend = ?,
            risk_flags = ?,
            analysed_at = ?
           WHERE id = ?""",
        (
            analysis.get("category"),
            analysis.get("urgency_level"),
            analysis.get("urgency_score"),
            json.dumps(analysis.get("urgency_reasons", [])),
            analysis.get("summary"),
            json.dumps(analysis.get("recommended_actions", [])),
            analysis.get("draft_response"),
            analysis.get("sentiment"),
            analysis.get("sentiment_trend"),
            json.dumps(analysis.get("risk_flags", [])),
            now,
        ),
    )
    await db.commit()

    analysis["thread_id"] = thread_id
    return analysis


# ──────────────────────────────────────────────────────────────
# BULK ANALYSIS
# ──────────────────────────────────────────────────────────────

async def analyse_all_threads(db, ws_manager=None) -> dict:
    """
    Analyse all unanalysed threads in batches of BATCH_SIZE.
    Broadcasts progress via ws_manager if provided.
    After all threads done, generates morning brief.
    """
    import aiosqlite
    db.row_factory = aiosqlite.Row

    async with db.execute(
        "SELECT id FROM threads WHERE analysed_at IS NULL ORDER BY id"
    ) as c:
        rows = await c.fetchall()
    thread_ids = [r[0] for r in rows]
    total = len(thread_ids)

    if total == 0:
        logger.info("All threads already analysed.")
        return {"completed": 0, "total": 0, "errors": 0}

    logger.info(f"Analysing {total} threads in batches of {BATCH_SIZE}…")
    completed = 0
    errors = 0

    # Broadcast start
    if ws_manager:
        await ws_manager.broadcast({"event": "analysis_progress", "completed": 0, "total": total})

    for i in range(0, total, BATCH_SIZE):
        batch = thread_ids[i: i + BATCH_SIZE]

        async def _analyse_one(tid):
            if ws_manager:
                await ws_manager.broadcast({"event": "analysis_started", "thread_id": tid})
            result = await analyse_thread(db, tid)
            return tid, result

        results = await asyncio.gather(*[_analyse_one(tid) for tid in batch], return_exceptions=True)

        for res in results:
            if isinstance(res, Exception):
                errors += 1
                logger.error(f"Batch error: {res}")
                continue
            tid, analysis = res
            completed += 1
            if "error" in analysis:
                errors += 1
            if ws_manager:
                await ws_manager.broadcast({
                    "event": "analysis_complete",
                    "thread_id": tid,
                    "data": analysis,
                })

        if ws_manager:
            await ws_manager.broadcast({
                "event": "analysis_progress",
                "completed": completed,
                "total": total,
            })

        # Small inter-batch pause to respect rate limits
        if i + BATCH_SIZE < total:
            await asyncio.sleep(1)

    logger.info(f"Analysis complete: {completed} done, {errors} errors")

    # Generate morning brief after all threads done
    brief_result = await generate_morning_brief(db)
    if ws_manager:
        await ws_manager.broadcast({
            "event": "morning_brief_ready",
            "data": brief_result,
        })

    return {"completed": completed, "total": total, "errors": errors}


# ──────────────────────────────────────────────────────────────
# MORNING BRIEF
# ──────────────────────────────────────────────────────────────

MORNING_BRIEF_SYSTEM = """You are a property management AI assistant. Generate a morning briefing.

Given the analysis of all current threads across the portfolio, write TWO versions:

1. "morning_brief" — A written briefing (under 400 words):
   - Status line: X critical, Y high, Z medium, W low priority threads
   - Top 5 priorities with what to do about each
   - Any deadlines or time-sensitive items today/this week
   - Portfolio patterns (multiple similar complaints, systemic issues, trends)
   - One-line portfolio mood summary

2. "voice_script" — A spoken version optimised for text-to-speech (under 200 words):
   - Conversational tone, as if a smart assistant is briefing you
   - Only the top 3 priorities with clear actions
   - Use spoken language: "Priority one" not "1.", say numbers as words
   - Avoid abbreviations that TTS handles poorly

Return as JSON: { "morning_brief": "...", "voice_script": "..." }"""


async def generate_morning_brief(db) -> dict:
    """
    Summarise all analysed threads into a morning brief + voice script.
    Stores result in dashboard_cache. Returns {morning_brief, voice_script}.
    """
    import aiosqlite
    db.row_factory = aiosqlite.Row

    async with db.execute("""
        SELECT id, subject, property_name, urgency_level, urgency_score,
               category, ai_summary, recommended_actions, risk_flags,
               sentiment, follow_up_count, days_open
        FROM threads
        WHERE analysed_at IS NOT NULL
        ORDER BY urgency_score DESC
    """) as c:
        threads = [dict(r) for r in await c.fetchall()]

    if not threads:
        return {"morning_brief": "No threads have been analysed yet.", "voice_script": ""}

    # Count by urgency
    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    for t in threads:
        lvl = (t.get("urgency_level") or "low").lower()
        if lvl in counts:
            counts[lvl] += 1

    # Build a compact summary for Claude
    thread_summaries = []
    for t in threads[:30]:  # cap at 30 to keep prompt manageable
        actions = []
        try:
            actions = json.loads(t.get("recommended_actions") or "[]")
        except Exception:
            pass
        top_action = actions[0]["action"] if actions else "No action specified"
        thread_summaries.append(
            f"[{t['urgency_level'] or 'unknown'}] {t['subject']} | {t['property_name'] or 'N/A'} | "
            f"Summary: {t['ai_summary'] or 'N/A'} | Action: {top_action}"
        )

    user_content = (
        f"Portfolio status: {counts['critical']} critical, {counts['high']} high, "
        f"{counts['medium']} medium, {counts['low']} low priority threads.\n\n"
        + "\n".join(thread_summaries)
    )

    try:
        result = await _call_gemini_with_retry(MORNING_BRIEF_SYSTEM, user_content)
    except Exception as e:
        logger.error(f"Morning brief generation failed: {e}")
        return {"morning_brief": f"Brief generation failed: {e}", "voice_script": ""}

    morning_brief = result.get("morning_brief", "")
    voice_script = result.get("voice_script", "")

    # Persist to dashboard_cache
    now = datetime.now(timezone.utc).isoformat()
    total_threads = len(threads)

    async with db.execute("SELECT COUNT(*) FROM messages") as c:
        total_messages = (await c.fetchone())[0]
    async with db.execute("SELECT COUNT(*) FROM messages WHERE is_read = 0") as c:
        unread_messages = (await c.fetchone())[0]

    await db.execute("""
        INSERT INTO dashboard_cache
            (id, total_messages, unread_messages, total_threads,
             critical_count, high_count, medium_count, low_count,
             morning_brief, voice_script, updated_at)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            total_messages = excluded.total_messages,
            unread_messages = excluded.unread_messages,
            total_threads = excluded.total_threads,
            critical_count = excluded.critical_count,
            high_count = excluded.high_count,
            medium_count = excluded.medium_count,
            low_count = excluded.low_count,
            morning_brief = excluded.morning_brief,
            voice_script = excluded.voice_script,
            updated_at = excluded.updated_at
    """, (
        total_messages, unread_messages, total_threads,
        counts["critical"], counts["high"], counts["medium"], counts["low"],
        morning_brief, voice_script, now,
    ))
    await db.commit()

    logger.info("Morning brief generated and cached.")
    return {"morning_brief": morning_brief, "voice_script": voice_script}


# ──────────────────────────────────────────────────────────────
# PATTERN DETECTION
# ──────────────────────────────────────────────────────────────

PATTERN_SYSTEM = """You are a property management AI. Analyse this cluster of related threads and describe the pattern.

Return JSON:
{
  "title": "Short descriptive title (e.g., 'Multiple heating complaints at Graylings')",
  "description": "2-3 sentences explaining the pattern, why it matters, and what the PM should do.",
  "severity": "critical | high | medium | low"
}

Respond ONLY with valid JSON."""


async def detect_patterns(db) -> list[dict]:
    """
    Scan analysed threads for portfolio-wide patterns.
    Inserts pattern_alerts rows and returns the list.
    """
    import aiosqlite
    db.row_factory = aiosqlite.Row

    async with db.execute("""
        SELECT id, subject, property_id, property_name, category, urgency_level,
               urgency_score, ai_summary, follow_up_count, days_open,
               first_message_at, sentiment
        FROM threads
        WHERE analysed_at IS NOT NULL
        ORDER BY property_id, category
    """) as c:
        threads = [dict(r) for r in await c.fetchall()]

    now = datetime.now(timezone.utc).isoformat()
    alerts_created = []

    # ── PATTERN 1: Recurring maintenance issues per property ──
    from collections import defaultdict
    maintenance_by_prop: dict[str, list] = defaultdict(list)
    for t in threads:
        cat = t.get("category") or ""
        if cat.startswith("maintenance") and t.get("property_id"):
            maintenance_by_prop[t["property_id"]].append(t)

    for prop_id, prop_threads in maintenance_by_prop.items():
        if len(prop_threads) < 3:
            continue
        prop_name = prop_threads[0]["property_name"] or prop_id
        thread_ids = [t["id"] for t in prop_threads]
        cluster_text = "\n".join(
            f"- {t['subject']}: {t['ai_summary'] or 'No summary'}" for t in prop_threads[:8]
        )
        user_msg = (
            f"PATTERN TYPE: Recurring maintenance issues at {prop_name}\n"
            f"Number of maintenance threads: {len(prop_threads)}\n\n"
            f"Threads:\n{cluster_text}"
        )
        try:
            result = await _call_gemini_with_retry(PATTERN_SYSTEM, user_msg)
            await db.execute("""
                INSERT INTO pattern_alerts
                    (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "systemic_maintenance",
                result.get("title", f"Multiple maintenance issues at {prop_name}"),
                result.get("description", ""),
                result.get("severity", "medium"),
                prop_id,
                json.dumps(thread_ids),
                now,
            ))
            alerts_created.append(result)
        except Exception as e:
            logger.error(f"Pattern detection error for {prop_id}: {e}")

    await db.commit()

    # ── PATTERN 2: Properties with >20% high/critical threads ──
    from collections import Counter
    prop_counts: dict[str, Counter] = defaultdict(Counter)
    prop_total: dict[str, int] = defaultdict(int)
    for t in threads:
        pid = t.get("property_id")
        if pid:
            prop_total[pid] += 1
            lvl = t.get("urgency_level") or "low"
            prop_counts[pid][lvl] += 1

    for pid, counts in prop_counts.items():
        total = prop_total[pid]
        high_critical = counts.get("critical", 0) + counts.get("high", 0)
        if total > 0 and high_critical / total > 0.2:
            prop_name = next((t["property_name"] for t in threads if t.get("property_id") == pid), pid)
            pct = int(high_critical / total * 100)
            thread_ids = [t["id"] for t in threads if t.get("property_id") == pid]
            await db.execute("""
                INSERT INTO pattern_alerts
                    (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                "escalation_cluster",
                f"{prop_name} requires attention",
                f"{pct}% of threads at {prop_name} are high or critical priority ({high_critical} of {total}). This property has a disproportionate share of urgent issues and may need a direct PM review.",
                "high" if pct > 40 else "medium",
                pid,
                json.dumps(thread_ids),
                now,
            ))
            alerts_created.append({"title": f"{prop_name} requires attention"})

    # ── PATTERN 3: Contacts with 3+ open threads ──
    async with db.execute("""
        SELECT primary_contact_id, COUNT(*) as cnt
        FROM threads
        WHERE status = 'open' AND primary_contact_id IS NOT NULL
        GROUP BY primary_contact_id
        HAVING cnt >= 3
    """) as c:
        frequent_contacts = await c.fetchall()

    for row in frequent_contacts:
        cid, cnt = row[0], row[1]
        async with db.execute("SELECT name, email FROM contacts WHERE id = ?", (cid,)) as c:
            contact = await c.fetchone()
        if not contact:
            continue
        name = contact[0]
        async with db.execute(
            "SELECT id FROM threads WHERE primary_contact_id = ? AND status = 'open'", (cid,)
        ) as c:
            t_ids = [r[0] for r in await c.fetchall()]
        await db.execute("""
            INSERT INTO pattern_alerts
                (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?)
        """, (
            "response_gaps",
            f"Frequent contact — {name}",
            f"{name} has {cnt} open threads. This contact may be experiencing unresolved issues and a direct PM call is recommended to address their concerns holistically.",
            "medium",
            json.dumps(t_ids),
            now,
        ))
        alerts_created.append({"title": f"Frequent contact — {name}"})

    await db.commit()
    logger.info(f"Pattern detection complete: {len(alerts_created)} alerts created.")
    return alerts_created
