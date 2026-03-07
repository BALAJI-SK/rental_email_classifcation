import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from database import db_dependency
from models import ProcurementJobCreate, BookContractorRequest, ContractorCreate

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_json_field(val) -> list:
    try:
        return json.loads(val or "[]")
    except Exception:
        return []


# ── PROCUREMENT JOBS ───────────────────────────────────────────

@router.get("/procurement")
async def list_jobs(
    status: Optional[str] = None,
    property_id: Optional[str] = None,
    work_type: Optional[str] = None,
    db=Depends(db_dependency),
):
    conditions, params = [], []
    if status:
        statuses = [s.strip() for s in status.split(",")]
        placeholders = ",".join("?" * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)
    if property_id:
        conditions.append("property_id = ?")
        params.append(property_id)
    if work_type:
        conditions.append("work_type = ?")
        params.append(work_type)

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    async with db.execute(f"""
        SELECT pj.*, p.name as property_name,
               c.company_name as contractor_name
        FROM procurement_jobs pj
        LEFT JOIN properties p ON pj.property_id = p.id
        LEFT JOIN contractors c ON pj.selected_contractor_id = c.id
        {where}
        ORDER BY pj.created_at DESC
    """, params) as cur:
        jobs = [dict(r) for r in await cur.fetchall()]

    # Add quote counts
    for job in jobs:
        async with db.execute("""
            SELECT COUNT(*) as total,
                   SUM(CASE WHEN status='received' THEN 1 ELSE 0 END) as received
            FROM quotes WHERE procurement_job_id=?
        """, (job["id"],)) as c:
            qc = dict(await c.fetchone())
        job["quote_total"] = qc["total"]
        job["quote_received"] = qc["received"] or 0

    return {"jobs": jobs, "total": len(jobs)}


@router.get("/procurement/{job_id}")
async def get_job(job_id: int, db=Depends(db_dependency)):
    async with db.execute("""
        SELECT pj.*, p.name as property_name
        FROM procurement_jobs pj
        LEFT JOIN properties p ON pj.property_id = p.id
        WHERE pj.id=?
    """, (job_id,)) as c:
        job = await c.fetchone()
    if not job:
        raise HTTPException(404, "Procurement job not found")
    job = dict(job)

    # Quotes with contractor info
    async with db.execute("""
        SELECT q.*, c.company_name, c.contact_person, c.email as contractor_email,
               c.avg_rating, c.total_jobs, c.avg_price_rating
        FROM quotes q
        JOIN contractors c ON q.contractor_id = c.id
        WHERE q.procurement_job_id=?
        ORDER BY q.quoted_price ASC NULLS LAST
    """, (job_id,)) as c:
        quotes = [dict(r) for r in await c.fetchall()]

    for q in quotes:
        if q.get("ai_extracted_data"):
            try:
                q["ai_extracted_data"] = json.loads(q["ai_extracted_data"])
            except Exception:
                pass

    return {"job": job, "quotes": quotes}


@router.post("/procurement")
async def create_job(body: ProcurementJobCreate, db=Depends(db_dependency)):
    async with db.execute("SELECT id, property_id FROM threads WHERE id=?", (body.thread_id,)) as c:
        thread = await c.fetchone()
    if not thread:
        raise HTTPException(404, "Thread not found")

    now = datetime.now(timezone.utc)
    deadline = (now + timedelta(hours=48)).isoformat()

    await db.execute("""
        INSERT INTO procurement_jobs
            (thread_id, property_id, unit, work_type, work_description, urgency, quote_deadline)
        VALUES (?, ?, NULL, ?, ?, ?, ?)
    """, (body.thread_id, thread[1] or "prop_001", body.work_type,
          body.work_description, body.urgency, deadline))
    await db.commit()

    async with db.execute("SELECT last_insert_rowid()") as c:
        job_id = (await c.fetchone())[0]

    async with db.execute("SELECT * FROM procurement_jobs WHERE id=?", (job_id,)) as c:
        return dict(await c.fetchone())


@router.post("/procurement/{job_id}/compare")
async def compare_quotes(job_id: int, db=Depends(db_dependency)):
    """Trigger AI comparison of received quotes."""
    async with db.execute("SELECT * FROM procurement_jobs WHERE id=?", (job_id,)) as c:
        job = await c.fetchone()
    if not job:
        raise HTTPException(404, "Job not found")
    job = dict(job)

    async with db.execute("""
        SELECT q.*, c.company_name, c.contact_person, c.avg_rating, c.total_jobs
        FROM quotes q
        JOIN contractors c ON q.contractor_id = c.id
        WHERE q.procurement_job_id=? AND q.status='received'
    """, (job_id,)) as c:
        quotes = [dict(r) for r in await c.fetchall()]

    if not quotes:
        raise HTTPException(400, "No received quotes to compare")

    from ai_pipeline import _call_claude_with_retry

    COMPARE_SYSTEM = """You are a property management procurement assistant.
Compare these contractor quotes and return a JSON recommendation.

Return:
{
  "comparison_matrix": [
    {
      "contractor": "name",
      "price": 280,
      "availability": "date",
      "duration": "2-3 hours",
      "rating": 4.5,
      "past_jobs": 12,
      "pros": ["pro1"],
      "cons": ["con1"]
    }
  ],
  "recommendation": {
    "best_overall": "contractor name",
    "reasoning": "why",
    "best_value": "contractor name",
    "fastest": "contractor name"
  },
  "summary": "1-2 sentence summary of comparison"
}

Respond ONLY with valid JSON."""

    quote_text = "\n".join(
        f"- {q['company_name']}: €{q.get('quoted_price','?')} | "
        f"Available: {q.get('availability_date','?')} | "
        f"Duration: {q.get('estimated_duration','?')} | "
        f"Rating: {q.get('avg_rating',0)}/5 | Past jobs: {q.get('total_jobs',0)}"
        for q in quotes
    )
    user_msg = (
        f"Work: {job['work_description']}\nUrgency: {job['urgency']}\n\nQuotes:\n{quote_text}"
    )

    try:
        comparison = await _call_claude_with_retry(COMPARE_SYSTEM, user_msg)
    except Exception as e:
        raise HTTPException(500, f"Comparison failed: {e}")

    await db.execute(
        "UPDATE procurement_jobs SET status='comparing' WHERE id=?", (job_id,)
    )
    await db.commit()

    return {"job_id": job_id, "comparison": comparison}


@router.post("/procurement/{job_id}/book")
async def book_contractor(job_id: int, body: BookContractorRequest, db=Depends(db_dependency)):
    async with db.execute("SELECT * FROM procurement_jobs WHERE id=?", (job_id,)) as c:
        job = await c.fetchone()
    if not job:
        raise HTTPException(404, "Job not found")
    job = dict(job)

    async with db.execute("SELECT * FROM contractors WHERE id=?", (body.contractor_id,)) as c:
        contractor = await c.fetchone()
    if not contractor:
        raise HTTPException(404, "Contractor not found")
    contractor = dict(contractor)

    # Get quote details
    async with db.execute("""
        SELECT quoted_price, availability_date FROM quotes
        WHERE procurement_job_id=? AND contractor_id=? AND status='received'
    """, (job_id, body.contractor_id)) as c:
        quote = await c.fetchone()
    price = quote[0] if quote else None
    date = quote[1] if quote else "TBD"

    now = datetime.now(timezone.utc).isoformat()
    await db.execute("""
        UPDATE procurement_jobs SET
            status='booked',
            selected_contractor_id=?,
            selected_price=?,
            selected_date=?,
            pm_approved=1,
            updated_at=?
        WHERE id=?
    """, (body.contractor_id, price, date, now, job_id))

    # Update thread status
    await db.execute(
        "UPDATE threads SET status='in_progress' WHERE id=?", (job["thread_id"],)
    )
    await db.commit()

    booking_draft = (
        f"Dear {contractor['contact_person']},\n\n"
        f"We are pleased to confirm the booking of your services for:\n"
        f"Work: {job['work_description']}\n"
        f"Property: {job['property_id']}\nUnit: {job.get('unit','')}\n"
        f"Date: {date}\nAgreed Price: €{price or 'TBD'}\n\n"
        f"Please confirm receipt of this booking.\n\nThank you."
    )

    return {
        "status": "booked",
        "contractor": contractor["company_name"],
        "price": price,
        "date": date,
        "booking_draft": booking_draft,
    }


# ── CONTRACTORS ────────────────────────────────────────────────

@router.get("/contractors")
async def list_contractors(
    specialty: Optional[str] = None,
    emergency: Optional[bool] = None,
    min_rating: Optional[float] = None,
    db=Depends(db_dependency),
):
    conditions = ["is_active=1"]
    params = []

    if specialty:
        conditions.append("specialties LIKE ?")
        params.append(f"%{specialty}%")
    if emergency is True:
        conditions.append("is_emergency_available=1")
    if min_rating is not None:
        conditions.append("avg_rating >= ?")
        params.append(min_rating)

    where = "WHERE " + " AND ".join(conditions)

    async with db.execute(f"""
        SELECT id, company_name, contact_person, email, phone, specialties,
               service_areas, avg_rating, total_jobs, avg_response_time_hours,
               avg_price_rating, is_emergency_available
        FROM contractors {where}
        ORDER BY avg_rating DESC
    """, params) as c:
        contractors = [dict(r) for r in await c.fetchall()]

    for con in contractors:
        con["specialties"] = _parse_json_field(con.get("specialties"))
        con["service_areas"] = _parse_json_field(con.get("service_areas"))

    return {"contractors": contractors, "total": len(contractors)}


@router.post("/contractors")
async def add_contractor(body: ContractorCreate, db=Depends(db_dependency)):
    await db.execute("""
        INSERT INTO contractors
            (company_name, contact_person, email, phone, specialties, service_areas,
             avg_rating, total_jobs, avg_response_time_hours, avg_price_rating,
             is_emergency_available)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        body.company_name, body.contact_person, body.email, body.phone,
        json.dumps(body.specialties),
        json.dumps(body.service_areas or []),
        body.avg_rating, body.total_jobs, body.avg_response_time_hours,
        body.avg_price_rating, body.is_emergency_available,
    ))
    await db.commit()
    async with db.execute("SELECT last_insert_rowid()") as c:
        cid = (await c.fetchone())[0]
    async with db.execute("SELECT * FROM contractors WHERE id=?", (cid,)) as c:
        return dict(await c.fetchone())


@router.get("/contractors/{contractor_id}")
async def get_contractor(contractor_id: int, db=Depends(db_dependency)):
    async with db.execute("SELECT * FROM contractors WHERE id=?", (contractor_id,)) as c:
        row = await c.fetchone()
    if not row:
        raise HTTPException(404, "Contractor not found")
    contractor = dict(row)
    contractor["specialties"] = _parse_json_field(contractor.get("specialties"))
    contractor["service_areas"] = _parse_json_field(contractor.get("service_areas"))

    async with db.execute("""
        SELECT id, work_type, quoted_price, final_price, quality_rating,
               on_time, on_budget, created_at
        FROM contractor_performance WHERE contractor_id=?
        ORDER BY created_at DESC
    """, (contractor_id,)) as c:
        performance = [dict(r) for r in await c.fetchall()]

    return {"contractor": contractor, "performance": performance}
