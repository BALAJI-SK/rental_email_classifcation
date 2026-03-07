import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

SCORE_TO_LEVEL = {
    range(9, 11): "critical",
    range(7, 9): "high",
    range(4, 7): "medium",
    range(1, 4): "low",
}


def _level(score: int) -> str:
    if score is None:
        return "low"
    for rng, level in SCORE_TO_LEVEL.items():
        if score in rng:
            return level
    return "low" if score < 1 else "critical"


async def process_thread(db, thread_id: str):
    """
    Apply auto-escalation rules after AI analysis.
    Logs changes to escalation_history. Updates contact sentiment.
    """
    async with db.execute("SELECT * FROM threads WHERE id = ?", (thread_id,)) as c:
        thread = await c.fetchone()
    if not thread:
        return
    thread = dict(thread)

    score = thread.get("urgency_score")
    if score is None:
        return  # Not analysed yet

    original_score = score
    reasons = []

    risk_flags_raw = thread.get("risk_flags") or "[]"
    try:
        risk_flags = json.loads(risk_flags_raw)
    except Exception:
        risk_flags = []
    risk_text = " ".join(risk_flags).lower()

    # ── Rule 1: follow_up_count >= 3 and urgency < 7 ──
    if (thread.get("follow_up_count") or 0) >= 3 and score < 7:
        score = 7
        reasons.append(
            f"Auto-escalated: {thread['follow_up_count']} follow-up messages from same sender — persistent unresolved issue"
        )

    # ── Rule 2: days_open > 5, open, urgency < 6 ──
    if (thread.get("days_open") or 0) > 5 and thread.get("status") == "open" and score < 6:
        score = min(score + 2, 10)
        reasons.append(
            f"Auto-escalated: thread open for {thread['days_open']} days with no resolution"
        )

    # ── Rule 3: threatening sentiment or legal risk flags ──
    sentiment = (thread.get("sentiment") or "").lower()
    has_legal = any(
        kw in risk_text for kw in ("legal", "rtb", "solicitor", "tribunal", "breach", "court")
    )
    if (sentiment == "threatening" or has_legal) and score < 8:
        score = max(score, 8)
        trigger = "threatening sentiment" if sentiment == "threatening" else "legal risk flag"
        reasons.append(f"Auto-escalated: {trigger} detected — minimum score 8 applied")

    # ── Apply changes if score changed ──
    if score != original_score and reasons:
        new_level = _level(score)
        old_level = _level(original_score)
        now = datetime.now(timezone.utc).isoformat()

        await db.execute(
            """UPDATE threads SET
                previous_urgency_score = ?,
                urgency_score = ?,
                urgency_level = ?,
                escalated_at = ?
               WHERE id = ?""",
            (original_score, score, new_level, now, thread_id),
        )

        for reason in reasons:
            await db.execute(
                """INSERT INTO escalation_history
                   (thread_id, old_score, new_score, old_level, new_level, reason, triggered_by, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, 'system_pattern', ?)""",
                (thread_id, original_score, score, old_level, new_level, reason, now),
            )

        await db.commit()
        logger.info(
            f"Thread {thread_id} escalated {original_score}→{score} ({old_level}→{new_level})"
        )

    # ── Update contact sentiment_avg and last_seen ──
    contact_id = thread.get("primary_contact_id")
    if contact_id and thread.get("sentiment"):
        await db.execute(
            "UPDATE contacts SET sentiment_avg = ?, last_seen = ? WHERE id = ?",
            (thread["sentiment"], datetime.now(timezone.utc).isoformat(), contact_id),
        )
        await db.commit()


async def run_portfolio_rules(db):
    """
    Run portfolio-wide pattern detection rules.
    Inserts into pattern_alerts table.
    """
    from collections import defaultdict
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()
    cutoff_7d = (now - timedelta(days=7)).isoformat()
    new_alerts = []

    # ── Rule 1: 3+ maintenance threads at same property in last 7 days ──
    async with db.execute("""
        SELECT property_id, property_name, COUNT(*) as cnt
        FROM threads
        WHERE category LIKE 'maintenance%'
          AND first_message_at >= ?
          AND property_id IS NOT NULL
        GROUP BY property_id
        HAVING cnt >= 3
    """, (cutoff_7d,)) as c:
        clusters = await c.fetchall()

    for row in clusters:
        prop_id, prop_name, cnt = row[0], row[1], row[2]
        # Avoid duplicate alerts
        async with db.execute("""
            SELECT id FROM pattern_alerts
            WHERE pattern_type='systemic_maintenance' AND property_id=? AND is_dismissed=0
        """, (prop_id,)) as c:
            if await c.fetchone():
                continue

        async with db.execute("""
            SELECT id FROM threads
            WHERE category LIKE 'maintenance%' AND property_id=? AND first_message_at >= ?
        """, (prop_id, cutoff_7d)) as c:
            tids = json.dumps([r[0] for r in await c.fetchall()])

        await db.execute("""
            INSERT INTO pattern_alerts
                (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "systemic_maintenance",
            f"Maintenance cluster at {prop_name or prop_id}",
            f"{cnt} maintenance issues raised at {prop_name or prop_id} in the last 7 days. "
            f"This may indicate a systemic problem (e.g., building-wide heating failure, structural issue). "
            f"A property inspection is recommended.",
            "high" if cnt >= 5 else "medium",
            prop_id, tids, now_iso,
        ))
        async with db.execute("SELECT last_insert_rowid()") as c:
            new_id = (await c.fetchone())[0]
            new_alerts.append({"id": new_id, "title": f"Maintenance cluster at {prop_name or prop_id}", "severity": "medium"})

    # ── Rule 2: Property with >20% HIGH/CRITICAL threads ──
    async with db.execute("""
        SELECT property_id, property_name,
               COUNT(*) as total,
               SUM(CASE WHEN urgency_level IN ('critical','high') THEN 1 ELSE 0 END) as hc
        FROM threads
        WHERE property_id IS NOT NULL AND analysed_at IS NOT NULL
        GROUP BY property_id
    """) as c:
        prop_stats = await c.fetchall()

    for row in prop_stats:
        prop_id, prop_name, total, hc = row[0], row[1], row[2], row[3] or 0
        if total < 3 or hc / total <= 0.2:
            continue

        async with db.execute("""
            SELECT id FROM pattern_alerts
            WHERE pattern_type='escalation_cluster' AND property_id=? AND is_dismissed=0
        """, (prop_id,)) as c:
            if await c.fetchone():
                continue

        pct = int(hc / total * 100)
        title = f"{prop_name or prop_id} requires attention"
        await db.execute("""
            INSERT INTO pattern_alerts
                (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "escalation_cluster",
            title,
            f"{pct}% of threads at {prop_name or prop_id} are high or critical priority "
            f"({hc} of {total} threads). A direct review of this property is recommended.",
            "high" if pct > 40 else "medium",
            prop_id, "[]", now_iso,
        ))
        async with db.execute("SELECT last_insert_rowid()") as c:
            new_id = (await c.fetchone())[0]
            new_alerts.append({"id": new_id, "title": title, "severity": "medium"})

    # ── Rule 3: Contact with 3+ open threads ──
    async with db.execute("""
        SELECT primary_contact_id, COUNT(*) as cnt
        FROM threads
        WHERE status='open' AND primary_contact_id IS NOT NULL
        GROUP BY primary_contact_id
        HAVING cnt >= 3
    """) as c:
        freq = await c.fetchall()

    for row in freq:
        cid, cnt = row[0], row[1]
        async with db.execute("SELECT name FROM contacts WHERE id=?", (cid,)) as c:
            contact = await c.fetchone()
        if not contact:
            continue
        name = contact[0]

        async with db.execute("""
            SELECT id FROM pattern_alerts
            WHERE pattern_type='response_gaps' AND description LIKE ? AND is_dismissed=0
        """, (f"%{name}%",)) as c:
            if await c.fetchone():
                continue

        async with db.execute(
            "SELECT id FROM threads WHERE primary_contact_id=? AND status='open'", (cid,)
        ) as c:
            tids = json.dumps([r[0] for r in await c.fetchall()])

        title = f"Frequent contact — {name}"
        await db.execute("""
            INSERT INTO pattern_alerts
                (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
            VALUES (?, ?, ?, ?, NULL, ?, ?)
        """, (
            "response_gaps",
            title,
            f"{name} has {cnt} open threads. This contact may be experiencing persistent "
            f"unresolved issues. A direct PM call is recommended to address concerns holistically.",
            "medium", tids, now_iso,
        ))
        async with db.execute("SELECT last_insert_rowid()") as c:
            new_id = (await c.fetchone())[0]
            new_alerts.append({"id": new_id, "title": title, "severity": "medium"})

    # ── Rule 4: Threads >7 days open with no internal reply ──
    async with db.execute("""
        SELECT t.id, t.subject, t.property_name
        FROM threads t
        WHERE t.status = 'open'
          AND t.days_open > 7
          AND NOT EXISTS (
              SELECT 1 FROM messages m
              WHERE m.thread_id = t.id AND m.sender_type IN ('internal')
          )
          AND t.analysed_at IS NOT NULL
        LIMIT 10
    """) as c:
        overdue = await c.fetchall()

    if overdue:
        tids = json.dumps([r[0] for r in overdue])
        async with db.execute("""
            SELECT id FROM pattern_alerts
            WHERE pattern_type='response_gaps' AND title='Response overdue' AND is_dismissed=0
        """) as c:
            if not await c.fetchone():
                title = "Response overdue"
                await db.execute("""
                    INSERT INTO pattern_alerts
                        (pattern_type, title, description, severity, property_id, related_thread_ids, created_at)
                    VALUES (?, ?, ?, ?, NULL, ?, ?)
                """, (
                    "response_gaps",
                    title,
                    f"{len(overdue)} threads have been open for more than 7 days with no internal response. "
                    f"Tenants are waiting. Prioritise these threads to avoid escalation.",
                    "high", tids, now_iso,
                ))
                async with db.execute("SELECT last_insert_rowid()") as c:
                    new_id = (await c.fetchone())[0]
                    new_alerts.append({"id": new_id, "title": title, "severity": "high"})
    await db.commit()
    logger.info(f"Portfolio rules applied. {len(new_alerts)} new alerts created.")
    return new_alerts
