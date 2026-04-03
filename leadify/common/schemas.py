import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from leadify.common.enums import LeadStatus, LeadEventType, FollowUpDraftStatus

# Base Schema
class BaseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

# Lead Schemas
class LeadBase(BaseSchema):
    email: EmailStr
    name: Optional[str] = None
    company: Optional[str] = None
    status: LeadStatus = LeadStatus.ACTIVE

class LeadCreate(LeadBase):
    first_email_sent_at: Optional[datetime] = None

class LeadUpdate(BaseSchema):
    email: Optional[EmailStr] = None
    name: Optional[str] = None
    company: Optional[str] = None
    status: Optional[LeadStatus] = None
    first_email_sent_at: Optional[datetime] = None

class LeadRead(LeadBase):
    id: uuid.UUID
    first_email_sent_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

# Lead Score Schemas
class LeadScoreRead(BaseSchema):
    id: uuid.UUID
    lead_id: uuid.UUID
    score: int
    delta: int
    reasoning: Optional[str] = None
    scored_at: datetime

# Follow-up Draft Schemas
class FollowUpDraftBase(BaseSchema):
    subject: str
    body: str
    score_at_draft: int
    signal_summary: Optional[str] = None
    writer_model: str
    status: FollowUpDraftStatus = FollowUpDraftStatus.PENDING_REVIEW

class FollowUpDraftUpdate(BaseSchema):
    subject: Optional[str] = None
    body: Optional[str] = None
    reviewer_feedback: Optional[str] = None
    status: Optional[FollowUpDraftStatus] = None

class FollowUpDraftRead(FollowUpDraftBase):
    id: uuid.UUID
    lead_id: uuid.UUID
    reviewer_feedback: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Agent Cycle Result
class AgentCycleResult(BaseSchema):
    cycle_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    timestamp: datetime = Field(default_factory=datetime.now)
    agents_involved: List[str]
    leads_processed: int
    events_detected: int
    scores_updated: int
    drafts_created: int
    summary: str
    errors: List[str] = []


# --- Phase 2: API Schemas ---

# Lead Event Read
class LeadEventRead(BaseSchema):
    id: uuid.UUID
    lead_id: uuid.UUID
    event_type: LeadEventType
    raw_data: Dict[str, Any]
    detected_at: datetime


# Lead Detail (single lead + latest score + recent events)
class LeadDetailRead(LeadRead):
    latest_score: Optional["LeadScoreRead"] = None
    recent_events: List[LeadEventRead] = []


# Lead History (all scores + events + drafts for timeline)
class LeadHistoryRead(BaseSchema):
    scores: List[LeadScoreRead] = []
    events: List[LeadEventRead] = []
    drafts: List[FollowUpDraftRead] = []


# Queue: draft joined with its lead
class QueueDraftRead(BaseSchema):
    draft: FollowUpDraftRead
    lead: LeadRead


# Queue: edit request body
class DraftEditRequest(BaseSchema):
    subject: str
    body: str


# Queue: dashboard stats
class QueueStats(BaseSchema):
    pending: int
    sent_today: int
    skipped_today: int


# Auth: Gmail connection status
class GmailStatus(BaseSchema):
    connected: bool
    email: Optional[str] = None


# Agents: last cycle status
class AgentStatusRead(BaseSchema):
    last_cycle_at: Optional[datetime] = None
    leads_processed: int = 0
    drafts_generated: int = 0
