"""
Real-time email processing pipeline.
Steps: identify_sender → match_thread → load_context → analyse → decide → execute → notify
"""
import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone

from dotenv import load_dotenv

from knowledge_base import get_contact_context, update_contact_from_message

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
logger = logging.getLogger(__name__)
MODEL = os.getenv("ANALYSIS_MODEL", "claude-sonnet-4-20250514")

# ──────────────────────────────────────────────────────────────
# DEMO SCENARIOS
# ──────────────────────────────────────────────────────────────

DEMO_SCENARIOS = {
    "tenant_followup": {
        "sender_name": "Eoin Byrne",
        "sender_email": "eoin.byrne@gmail.com",
        "sender_type": "tenant",
        "sender_unit": "Apt 14B",
        "to": "citynorth@manageco.ie",
        "subject": "Re: URGENT - Water leaking through ceiling in bedroom",
        "body": (
            "Hi,\n\nI still haven't heard back about the water leak. It's now been 4 days "
            "and the situation is getting worse. The ceiling plaster has started cracking and "
            "I'm genuinely worried about the structural integrity.\n\n"
            "I've been in touch with the RTB and they've advised me to document everything. "
            "I have photos and a video of the damage. If I don't hear from someone today with "
            "a concrete plan, I'll be filing a formal complaint.\n\n"
            "This needs to be resolved TODAY.\n\nEoin\n07700 100 200"
        ),
        "property_id": "prop_001",
    },
    "new_prospect": {
        "sender_name": "Sarah Kelly",
        "sender_email": "sarah.kelly.dublin@gmail.com",
        "sender_type": "prospect",
        "to": "info@graylings.ie",
        "subject": "Enquiry about 3-bed apartment availability",
        "body": (
            "Hi,\n\nI'm looking for a 3-bedroom apartment in the Graylings development. "
            "I've seen some great reviews online and it looks perfect for my family "
            "(myself, partner, and one child aged 4).\n\n"
            "Could you let me know:\n"
            "1. Do you have any 3-bed units available?\n"
            "2. What's the monthly rent?\n"
            "3. When could we arrange a viewing?\n\n"
            "We'd be looking to move in within the next 6-8 weeks.\n\nThanks,\nSarah"
        ),
        "property_id": "prop_003",
    },
    "emergency": {
        "sender_name": "Padraig Dolan",
        "sender_email": "padraig.dolan@outlook.com",
        "sender_type": "tenant",
        "sender_unit": "Apt 7A",
        "to": "reds@manageco.ie",
        "subject": "GAS SMELL IN APARTMENT - EMERGENCY",
        "body": (
            "Hello,\n\nThere is a very strong gas smell coming from my kitchen. "
            "I've turned off the gas at the mains and opened all windows but the smell is still there. "
            "I've evacuated to the hallway. My wife and two young children are with me.\n\n"
            "I've called Gas Networks Ireland (1800 20 50 50) and they said they're sending someone "
            "but said to contact the building management as well.\n\n"
            "PLEASE CALL ME IMMEDIATELY: 085 123 4567\n\nPadraig Dolan, Apt 7A"
        ),
        "property_id": "prop_002",
    },
    "contractor_invoice": {
        "sender_name": "Ronan Keane",
        "sender_email": "emergencyplumbing@dublinmaintenance.ie",
        "sender_type": "contractor",
        "to": "accounts@manageco.ie",
        "subject": "2nd Reminder: Invoice INV-2024-1847 — Emergency Plumbing Works",
        "body": (
            "Hi,\n\nThis is a second reminder for Invoice INV-2024-1847 for the emergency "
            "plumbing works carried out at Citynorth Quarter, Apt 14B on 4th February 2024.\n\n"
            "Invoice amount: €485 (inc. VAT)\n"
            "Payment terms: 30 days (due 5th March 2024)\n"
            "Now 2 days overdue\n\n"
            "Please arrange payment at your earliest convenience. "
            "We value our working relationship with ManageCo and look forward to "
            "continuing to provide our services.\n\n"
            "Bank details: IBAN IE12 BOFI 9000 0112 3456 78\n\n"
            "Ronan Keane\nDublin Maintenance Services\n+353 1 555 0101"
        ),
        "property_id": "prop_001",
    },
    "unknown_sender": {
        "sender_name": "Anonymous",
        "sender_email": "anon123@protonmail.com",
        "sender_type": "external",
        "to": "info@manageco.ie",
        "subject": "Complaint about noise and conditions",
        "body": (
            "Hello,\n\nI am writing to complain about conditions at one of your properties. "
            "There has been ongoing noise issues and I believe some tenants are having problems "
            "that aren't being addressed.\n\nI would appreciate someone looking into this.\n\nThank you"
        ),
        "property_id": None,
    },
}

# Alias for frontend
DEMO_SCENARIOS["contractor_reply"] = DEMO_SCENARIOS["contractor_invoice"]

ANALYSE_SYSTEM = """You are an expert AI assistant for Irish property management. A new email just arrived.
Analyse it with the full context provided and return a JSON decision.

RETURN THIS JSON:
{
  "category": "maintenance_emergency | maintenance_urgent | maintenance_routine | lease | payment | complaint | inquiry | contractor | landlord | legal | system_alert | prospect",
  "urgency_level": "critical | high | medium | low",
  "urgency_score": 1-10,
  "urgency_reasons": ["Specific reason 1", "Specific reason 2"],
  "summary": "2-3 sentence summary of the situation including history",
  "sentiment": "positive | neutral | negative | angry | anxious | threatening",
  "sentiment_change": "same | worse | better",
  "action_level": "pm_immediate | pm_review | auto_reply | info_only",
  "action_level_reasoning": "Why this action level",
  "recommended_actions": [{"action": "...", "priority": 1, "reasoning": "...", "deadline": "..."}],
  "risk_flags": ["..."],
  "draft_response": "Full professional draft email response",
  "auto_reply_eligible": false,
  "escalation": {
    "should_escalate": false,
    "from_level": "current level",
    "to_level": "recommended",
    "reason": "why"
  },
  "notification": {
    "push_notification": true,
    "voice_alert": false,
    "push_title": "Short title",
    "push_body": "1-2 sentence summary",
    "voice_text": "Spoken version"
  }
}

ACTION LEVEL GUIDE:
- pm_immediate: PM must see this NOW. Critical/high urgency, safety, legal deadlines.
- pm_review: PM should review draft before sending. Medium urgency, needs judgment.
- auto_reply: System can send automatically. Low urgency, simple info request, no risk.
- info_only: No response needed. FYI messages, system alerts.

Respond ONLY with valid JSON."""


class EmailProcessor:
    async def process_new_email(self, db, email: dict, ws_manager=None) -> dict:
        """Full 7-step pipeline for an incoming email."""
        try:
            contact = await self.identify_sender(db, email)
            thread_info = await self.match_thread(db, email, contact)
            context = await self.load_context(db, contact, thread_info, email)
            analysis = await self.analyse_with_context(context)
            decisions = await self.decide_action(db, analysis, context)
            await self.execute_actions(db, decisions, thread_info, analysis, ws_manager)
            await self.notify(db, ws_manager, thread_info, analysis, decisions)

            return {
                "message_id": thread_info["new_message_id"],
                "thread_id": thread_info["thread_id"],
                "is_new_thread": not thread_info["is_existing"],
                "analysis": analysis,
                "decision": decisions,
            }
        except Exception as e:
            logger.error(f"Error processing new email: {e}", exc_info=True)
            raise e

    async def identify_sender(self, db, email: dict) -> dict:
        sender_email = email.get("sender_email")
        contact = None
        logger.info(f"Identifying sender: {sender_email}")

        if sender_email:
            async with db.execute(
                "SELECT * FROM contacts WHERE email = ?", (sender_email,)
            ) as c:
                row = await c.fetchone()
            if row:
                contact = dict(row)

        if not contact:
            # Create new contact
            from ingest import _extract_phone
            phone = _extract_phone(email.get("body", ""))
            now = datetime.now(timezone.utc).isoformat()
            is_known = bool(
                sender_email and email.get("sender_name") and
                (phone or email.get("sender_unit"))
            )
            await db.execute("""
                INSERT INTO contacts
                    (name, email, phone, type, unit, property_id, is_known,
                     total_messages, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """, (
                email.get("sender_name", "Unknown"),
                sender_email,
                phone,
                email.get("sender_type", "external"),
                email.get("sender_unit"),
                email.get("property_id"),
                is_known,
                now, now,
            ))
            await db.commit()
            async with db.execute("SELECT last_insert_rowid()") as c:
                contact_id = (await c.fetchone())[0]
            async with db.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)) as c:
                contact = dict(await c.fetchone())

        missing_info = []
        if not contact.get("phone"):
            missing_info.append("phone")
        if not contact.get("unit"):
            missing_info.append("unit")

        return {
            "contact_id": contact["id"],
            "is_known": bool(contact.get("is_known")),
            "contact_profile": contact,
            "missing_info": missing_info,
        }

    async def match_thread(self, db, email: dict, contact: dict) -> dict:
        subject = email.get("subject", "")
        contact_id = contact["contact_id"]

        # Try "Re: ..." subject match
        clean_subject = re.sub(r"^(Re:\s*)+", "", subject, flags=re.I).strip()
        async with db.execute("""
            SELECT t.id, t.message_count FROM threads t
            WHERE t.subject LIKE ? AND t.primary_contact_id = ?
            ORDER BY t.last_message_at DESC LIMIT 1
        """, (f"%{clean_subject}%", contact_id)) as c:
            existing = await c.fetchone()

        if existing:
            thread_id = existing[0]
            position = existing[1] + 1
            is_existing = True
        else:
            thread_id = f"thread_{uuid.uuid4().hex[:8]}"
            position = 1
            is_existing = False

        # Insert the new message
        msg_id = f"email_{uuid.uuid4().hex[:10]}"
        now = datetime.now(timezone.utc).isoformat()
        await db.execute("""
            INSERT INTO messages
                (id, thread_id, thread_position, timestamp, sender_name, sender_email,
                 sender_type, sender_unit, property_id, contact_id, recipient, subject, body,
                 attachments, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """, (
            msg_id, thread_id, position, now,
            email.get("sender_name", ""),
            email.get("sender_email"),
            email.get("sender_type", "external"),
            email.get("sender_unit"),
            email.get("property_id"),
            contact_id,
            email.get("to"),
            subject,
            email.get("body", ""),
            json.dumps(email.get("attachments", [])),
        ))

        if not is_existing:
            # Create thread record
            prop_id = email.get("property_id")
            prop_name = None
            if prop_id:
                async with db.execute("SELECT name FROM properties WHERE id=?", (prop_id,)) as c:
                    row = await c.fetchone()
                    prop_name = row[0] if row else None

            await db.execute("""
                INSERT INTO threads
                    (id, subject, property_id, property_name, message_count,
                     primary_contact_id, first_message_at, last_message_at, is_read)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?, 0)
            """, (thread_id, subject, prop_id, prop_name, contact_id, now, now))
        else:
            await db.execute("""
                UPDATE threads SET
                    message_count = message_count + 1,
                    last_message_at = ?,
                    follow_up_count = follow_up_count + 1,
                    is_read = 0,
                    analysed_at = NULL
                WHERE id = ?
            """, (now, thread_id))

        await db.commit()

        # Fetch all prior messages
        async with db.execute("""
            SELECT thread_position, sender_name, sender_type, sender_email, timestamp, body
            FROM messages WHERE thread_id = ? ORDER BY thread_position
        """, (thread_id,)) as c:
            previous = [dict(r) for r in await c.fetchall()]

        return {
            "thread_id": thread_id,
            "is_existing": is_existing,
            "thread_position": position,
            "previous_messages": previous,
            "new_message_id": msg_id,
        }

    async def load_context(self, db, contact: dict, thread: dict, email: dict) -> dict:
        contact_profile = await get_contact_context(db, contact["contact_id"])

        property_ctx = {}
        prop_id = email.get("property_id")
        if prop_id:
            async with db.execute("SELECT * FROM properties WHERE id=?", (prop_id,)) as c:
                row = await c.fetchone()
                if row:
                    property_ctx = dict(row)
            # Count open critical/high
            async with db.execute("""
                SELECT COUNT(*) FROM threads
                WHERE property_id=? AND urgency_level IN ('critical','high') AND status='open'
            """, (prop_id,)) as c:
                property_ctx["open_critical_high"] = (await c.fetchone())[0]

        # Related open threads for this contact
        related = []
        async with db.execute("""
            SELECT id, subject, urgency_level, status FROM threads
            WHERE primary_contact_id=? AND status IN ('open','in_progress') AND id != ?
            LIMIT 3
        """, (contact["contact_id"], thread["thread_id"])) as c:
            related = [dict(r) for r in await c.fetchall()]

        return {
            "new_email": email,
            "contact_profile": contact_profile,
            "thread_history": thread["previous_messages"],
            "property_context": property_ctx,
            "related_threads": related,
        }

    async def analyse_with_context(self, context: dict) -> dict:
        from ai_pipeline import _call_gemini_with_retry

        profile = context["contact_profile"]
        prop = context["property_context"]
        history = context["thread_history"]
        email = context["new_email"]
        related = context["related_threads"]

        history_text = "\n".join(
            f"[{m.get('thread_position','')}] {m.get('sender_name','')} "
            f"({m.get('sender_type','')}): {(m.get('body') or '')[:200]}..."
            for m in history[:-1]  # exclude the new message itself
        ) or "No prior messages"

        related_text = "\n".join(
            f"- {t['subject']} ({t['urgency_level']}, {t['status']})"
            for t in related
        ) or "None"

        user_msg = f"""CONTACT PROFILE:
Name: {profile.get('name')} | Type: {profile.get('type')} | Known: {profile.get('is_known')}
Unit: {profile.get('unit') or 'unknown'} | Property: {profile.get('property') or 'unknown'}
Total messages: {profile.get('total_messages',0)} | Open threads: {profile.get('open_thread_count',0)}
Sentiment trend: {profile.get('sentiment_trend') or 'unknown'}
Missing info: {', '.join(profile.get('missing_info', [])) or 'none'}

THREAD HISTORY (previous messages):
{history_text}

PROPERTY CONTEXT:
{prop.get('name','Unknown')} ({prop.get('type','')}, {prop.get('units','')} units)
Manager: {prop.get('manager','Unknown')}
Open critical/high threads: {prop.get('open_critical_high', 0)}

RELATED OPEN THREADS FOR THIS CONTACT:
{related_text}

NEW EMAIL:
From: {email.get('sender_name')} <{email.get('sender_email','')}>
Subject: {email.get('subject','')}
Body: {email.get('body','')}"""

        try:
            return await _call_gemini_with_retry(ANALYSE_SYSTEM, user_msg)
        except Exception as e:
            logger.error(f"AI Analysis failed: {e}")
            # Fallback analysis to prevent 500 errors when quota is hit
            return {
                "category": "inquiry",
                "urgency_level": "medium",
                "urgency_score": 5,
                "urgency_reasons": ["AI analysis temporarily unavailable"],
                "summary": "New message received. AI analysis failed to generate a summary.",
                "sentiment": "neutral",
                "action_level": "pm_review",
                "recommended_actions": [{"action": "Manually review this thread", "priority": 1, "reasoning": "AI quota exceeded", "deadline": "Today"}],
                "draft_response": "Thank you for your message. Our team has received it and will respond as soon as possible.",
                "risk_flags": [],
                "auto_reply_eligible": False,
                "notification": {
                    "push_notification": True,
                    "push_title": "New Message (Analysis Failed)",
                    "push_body": "A new message arrived but analysis skipped."
                }
            }

    async def decide_action(self, db, analysis: dict, context: dict) -> dict:
        action_level = analysis.get("action_level", "pm_review")
        actions = []

        notif = analysis.get("notification", {})
        if notif.get("push_notification") or action_level == "pm_immediate":
            actions.append({
                "type": "notify_pm",
                "data": {
                    "title": notif.get("push_title", analysis.get("summary", "")[:60]),
                    "body": notif.get("push_body", ""),
                    "urgency": analysis.get("urgency_level"),
                }
            })

        if analysis.get("draft_response"):
            if action_level == "auto_reply" and analysis.get("auto_reply_eligible"):
                actions.append({"type": "auto_send", "data": {"draft": analysis["draft_response"]}})
            else:
                actions.append({"type": "queue_draft", "data": {"draft": analysis["draft_response"]}})

        escalation = analysis.get("escalation", {})
        if escalation.get("should_escalate"):
            actions.append({
                "type": "escalate_thread",
                "data": {
                    "new_level": escalation.get("to_level"),
                    "reason": escalation.get("reason"),
                }
            })

        return {"action_level": action_level, "actions": actions}

    async def execute_actions(self, db, decisions: dict, thread_info: dict, analysis: dict, ws_manager):
        thread_id = thread_info["thread_id"]
        now = datetime.now(timezone.utc).isoformat()

        for action in decisions.get("actions", []):
            atype = action["type"]

            if atype == "queue_draft":
                await db.execute("""
                    UPDATE threads SET draft_response=?, status='open' WHERE id=?
                """, (action["data"]["draft"], thread_id))

            elif atype == "auto_send":
                # Log auto-reply as a message in the thread
                async with db.execute(
                    "SELECT MAX(thread_position) FROM messages WHERE thread_id=?", (thread_id,)
                ) as c:
                    max_pos = (await c.fetchone())[0] or 0
                await db.execute("""
                    INSERT INTO messages
                        (id, thread_id, thread_position, timestamp, sender_name, sender_type,
                         subject, body, is_read)
                    VALUES (?, ?, ?, ?, 'System (Auto-Reply)', 'internal', 'Re: Auto-Reply', ?, 1)
                """, (
                    f"auto_{uuid.uuid4().hex[:8]}", thread_id, max_pos + 1, now,
                    action["data"]["draft"],
                ))

            elif atype == "escalate_thread":
                new_level = action["data"].get("new_level", "high")
                level_score = {"critical": 9, "high": 7, "medium": 5, "low": 2}
                new_score = level_score.get(new_level, 7)
                await db.execute("""
                    UPDATE threads SET urgency_level=?, urgency_score=?, escalated_at=? WHERE id=?
                """, (new_level, new_score, now, thread_id))
                await db.execute("""
                    INSERT INTO escalation_history
                        (thread_id, new_score, new_level, reason, triggered_by, created_at)
                    VALUES (?, ?, ?, ?, 'ai_analysis', ?)
                """, (thread_id, new_score, new_level, action["data"].get("reason", ""), now))

        # Update thread with AI analysis
        await db.execute("""
            UPDATE threads SET
                category=?, urgency_level=?, urgency_score=?,
                urgency_reasons=?, ai_summary=?, recommended_actions=?,
                draft_response=?, sentiment=?, risk_flags=?, analysed_at=?
            WHERE id=?
        """, (
            analysis.get("category"),
            analysis.get("urgency_level"),
            analysis.get("urgency_score"),
            json.dumps(analysis.get("urgency_reasons", [])),
            analysis.get("summary"),
            json.dumps(analysis.get("recommended_actions", [])),
            analysis.get("draft_response"),
            analysis.get("sentiment"),
            json.dumps(analysis.get("risk_flags", [])),
            now, thread_id,
        ))
        await db.commit()

    async def notify(self, db, ws_manager, thread_info: dict, analysis: dict, decisions: dict):
        if not ws_manager:
            return
        tid = thread_info["thread_id"]

        # Fetch the full thread object to send to frontend
        async with db.execute("SELECT * FROM threads WHERE id = ?", (tid,)) as c:
            row = await c.fetchone()
            thread_data = dict(row) if row else None

        if thread_data:
            # Parse JSON fields for frontend
            for field in ["recommended_actions", "risk_flags", "urgency_reasons"]:
                if thread_data.get(field) and isinstance(thread_data[field], str):
                    try:
                        thread_data[field] = json.loads(thread_data[field])
                    except:
                        thread_data[field] = []

            await ws_manager.broadcast({
                "event": "new_email",
                "data": thread_data,
            })
        
        if decisions.get("action_level") == "pm_immediate":
            await ws_manager.broadcast({
                "event": "action_required",
                "data": {
                    "thread_id": tid,
                    "title": analysis.get("summary", "")[:80],
                    "urgency": analysis.get("urgency_level"),
                }
            })
