import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.api.dependencies import get_db
from leadify.common.enums import LeadStatus
from leadify.common.schemas import (
    LeadCreate,
    LeadRead,
    LeadUpdate,
    LeadDetailRead,
    LeadScoreRead,
    LeadEventRead,
    LeadHistoryRead,
)
from leadify.db.models import Lead, LeadScore, LeadEvent

router = APIRouter()


@router.post("/", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
async def create_lead(lead_in: LeadCreate, db: AsyncSession = Depends(get_db)):
    """Create a new lead."""
    # Check for duplicate email
    existing = await db.execute(select(Lead).where(Lead.email == lead_in.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A lead with this email already exists",
        )

    lead = Lead(
        email=lead_in.email,
        name=lead_in.name,
        company=lead_in.company,
        status=lead_in.status,
        first_email_sent_at=lead_in.first_email_sent_at,
    )
    db.add(lead)
    await db.flush()
    await db.refresh(lead)
    return lead


@router.get("/", response_model=List[LeadRead])
async def list_leads(
    lead_status: Optional[LeadStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
):
    """List all leads, optionally filtered by status."""
    query = select(Lead).order_by(desc(Lead.created_at))
    if lead_status is not None:
        query = query.where(Lead.status == lead_status)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{lead_id}", response_model=LeadDetailRead)
async def get_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Get a single lead with its latest score and last 5 events."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Latest score
    score_result = await db.execute(
        select(LeadScore)
        .where(LeadScore.lead_id == lead_id)
        .order_by(desc(LeadScore.scored_at))
        .limit(1)
    )
    latest_score = score_result.scalar_one_or_none()

    # Last 5 events
    events_result = await db.execute(
        select(LeadEvent)
        .where(LeadEvent.lead_id == lead_id)
        .order_by(desc(LeadEvent.detected_at))
        .limit(5)
    )
    recent_events = events_result.scalars().all()

    return LeadDetailRead(
        id=lead.id,
        email=lead.email,
        name=lead.name,
        company=lead.company,
        status=lead.status,
        first_email_sent_at=lead.first_email_sent_at,
        created_at=lead.created_at,
        updated_at=lead.updated_at,
        latest_score=latest_score,
        recent_events=recent_events,
    )


@router.patch("/{lead_id}", response_model=LeadRead)
async def update_lead(
    lead_id: uuid.UUID,
    lead_in: LeadUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a lead (status, name, company, etc.)."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    update_data = lead_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(lead, field, value)

    await db.flush()
    await db.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Soft-delete a lead by setting status to dead."""
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead.status = LeadStatus.DEAD
    await db.flush()
    return None


@router.get("/{lead_id}/history", response_model=LeadHistoryRead)
async def get_lead_history(lead_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Return all scores and events for a lead, sorted by time descending."""
    # Verify lead exists
    result = await db.execute(select(Lead).where(Lead.id == lead_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Lead not found")

    scores_result = await db.execute(
        select(LeadScore)
        .where(LeadScore.lead_id == lead_id)
        .order_by(desc(LeadScore.scored_at))
    )
    events_result = await db.execute(
        select(LeadEvent)
        .where(LeadEvent.lead_id == lead_id)
        .order_by(desc(LeadEvent.detected_at))
    )

    return LeadHistoryRead(
        scores=scores_result.scalars().all(),
        events=events_result.scalars().all(),
    )
