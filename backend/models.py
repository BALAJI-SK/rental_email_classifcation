from pydantic import BaseModel
from typing import Optional


class ThreadUpdate(BaseModel):
    status: Optional[str] = None   # open, in_progress, resolved, snoozed, escalated
    is_read: Optional[bool] = None


class ContactUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    unit: Optional[str] = None
    property_id: Optional[str] = None
    lease_start: Optional[str] = None
    lease_end: Optional[str] = None
    notes: Optional[str] = None


class ChatRequest(BaseModel):
    query: str


class IncomingEmail(BaseModel):
    sender_name: str
    sender_email: Optional[str] = None
    sender_type: str = "external"
    sender_unit: Optional[str] = None
    to: Optional[str] = None
    subject: str
    body: str
    attachments: Optional[list[str]] = None
    property_id: Optional[str] = None


class SimulateRequest(BaseModel):
    scenario: str  # tenant_followup, new_prospect, emergency, contractor_invoice, unknown_sender


class ProcurementJobCreate(BaseModel):
    thread_id: str
    work_type: str
    work_description: str
    urgency: str


class BookContractorRequest(BaseModel):
    contractor_id: int


class ContractorCreate(BaseModel):
    company_name: str
    contact_person: str
    email: str
    phone: Optional[str] = None
    specialties: list[str]
    service_areas: Optional[list[str]] = None
    avg_rating: float = 0
    total_jobs: int = 0
    avg_response_time_hours: Optional[float] = None
    avg_price_rating: Optional[str] = None
    is_emergency_available: bool = False
