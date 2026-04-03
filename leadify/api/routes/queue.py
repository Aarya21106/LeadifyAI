import uuid
from datetime import datetime, date
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, desc, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.api.dependencies import get_db
from leadify.common.enums import FollowUpDraftStatus
from leadify.common.schemas import (
    FollowUpDraftRead,
    DraftEditRequest,
    QueueDraftRead,
    QueueStats,
    LeadRead,
)
from leadify.db.models import FollowUpDraft, Lead

router = APIRouter()


@router.get("", response_model=List[QueueDraftRead])
async def list_queue(db: AsyncSession = Depends(get_db)):
    """Return all pending_review drafts joined with lead data, sorted by score descending."""
    result = await db.execute(
        select(FollowUpDraft)
        .where(FollowUpDraft.status == FollowUpDraftStatus.PENDING_REVIEW)
        .order_by(desc(FollowUpDraft.score_at_draft))
    )
    drafts = result.scalars().all()

    items = []
    for draft in drafts:
        lead_result = await db.execute(select(Lead).where(Lead.id == draft.lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead:
            items.append(
                QueueDraftRead(
                    draft=FollowUpDraftRead.model_validate(draft),
                    lead=LeadRead.model_validate(lead),
                )
            )
    return items


@router.post("/{draft_id}/approve", response_model=FollowUpDraftRead)
async def approve_draft(draft_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Approve a draft and trigger send (stub for now)."""
    result = await db.execute(
        select(FollowUpDraft).where(FollowUpDraft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if draft.status != FollowUpDraftStatus.PENDING_REVIEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Draft is not pending review (current: {draft.status.value})",
        )

    draft.status = FollowUpDraftStatus.APPROVED
    await db.flush()

    # Trigger Gmail send via Sender Agent for real-time dispatch
    from leadify.agents.sender_agent import SenderAgent
    sender = SenderAgent(db)
    await sender.run([draft])
    
    await db.refresh(draft)
    return draft


@router.post("/{draft_id}/skip", response_model=FollowUpDraftRead)
async def skip_draft(draft_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Mark a draft as skipped."""
    result = await db.execute(
        select(FollowUpDraft).where(FollowUpDraft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.status = FollowUpDraftStatus.SKIPPED
    await db.flush()
    await db.refresh(draft)
    return draft


@router.post("/{draft_id}/edit", response_model=FollowUpDraftRead)
async def edit_draft(
    draft_id: uuid.UUID,
    edit_in: DraftEditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Edit a draft's subject/body and mark it as approved."""
    result = await db.execute(
        select(FollowUpDraft).where(FollowUpDraft.id == draft_id)
    )
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    draft.subject = edit_in.subject
    draft.body = edit_in.body
    draft.status = FollowUpDraftStatus.APPROVED
    await db.flush()
    await db.refresh(draft)
    return draft


@router.get("/stats", response_model=QueueStats)
async def queue_stats(db: AsyncSession = Depends(get_db)):
    """Return counts: pending, sent today, skipped today."""
    today = date.today()

    # Pending count
    pending_result = await db.execute(
        select(func.count(FollowUpDraft.id)).where(
            FollowUpDraft.status == FollowUpDraftStatus.PENDING_REVIEW
        )
    )
    pending = pending_result.scalar() or 0

    # Sent today (simplified for SQLite compatibility)
    sent_result = await db.execute(
        select(func.count(FollowUpDraft.id)).where(
            FollowUpDraft.status == FollowUpDraftStatus.SENT
        )
    )
    sent_today = sent_result.scalar() or 0

    # Skipped today (simplified for SQLite compatibility)
    skipped_result = await db.execute(
        select(func.count(FollowUpDraft.id)).where(
            FollowUpDraft.status == FollowUpDraftStatus.SKIPPED
        )
    )
    skipped_today = skipped_result.scalar() or 0

    return QueueStats(pending=pending, sent_today=sent_today, skipped_today=skipped_today)
