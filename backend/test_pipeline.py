"""
Quick smoke test: analyse 3 threads and print results.
Run: python test_pipeline.py
"""
import asyncio
import json
import aiosqlite
from database import DB_PATH
from ai_pipeline import analyse_thread


THREAD_IDS = ["thread_001", "thread_003", "thread_010"]


async def main():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        for tid in THREAD_IDS:
            print(f"\n{'='*60}")
            print(f"Analysing {tid}…")
            print('='*60)

            # Quick preview of what we're analysing
            async with db.execute(
                "SELECT subject, message_count, follow_up_count FROM threads WHERE id = ?", (tid,)
            ) as c:
                t = await c.fetchone()
            if not t:
                print(f"  Thread {tid} not found, skipping.")
                continue
            print(f"  Subject: {t['subject']}")
            print(f"  Messages: {t['message_count']}  Follow-ups: {t['follow_up_count']}")

            result = await analyse_thread(db, tid)

            if "error" in result:
                print(f"  ERROR: {result['error']}")
                continue

            print(f"\n  Category:      {result.get('category')}")
            print(f"  Urgency:       {result.get('urgency_level')} (score {result.get('urgency_score')})")
            print(f"  Sentiment:     {result.get('sentiment')} / {result.get('sentiment_trend')}")
            print(f"\n  Summary:\n    {result.get('summary')}")

            reasons = result.get("urgency_reasons", [])
            if reasons:
                print(f"\n  Urgency reasons:")
                for r in reasons:
                    print(f"    • {r}")

            actions = result.get("recommended_actions", [])
            if actions:
                print(f"\n  Recommended actions:")
                for a in actions:
                    print(f"    [{a.get('priority')}] {a.get('action')} — {a.get('deadline')}")

            flags = result.get("risk_flags", [])
            if flags:
                print(f"\n  Risk flags:")
                for f in flags:
                    print(f"    ⚠  {f}")

            draft = result.get("draft_response", "")
            if draft:
                print(f"\n  Draft response (first 200 chars):\n    {draft[:200]}…")

    print(f"\n{'='*60}")
    print("Test complete.")


if __name__ == "__main__":
    asyncio.run(main())
