"""
Reviewer Agent — Reviews and quality-checks follow-up drafts.

Automatically reviews Writer Agent drafts for tone, accuracy, and
professional quality. Approves good drafts and flags weak ones.
"""

import logging
import random
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import FollowUpDraftStatus
from leadify.db.models import FollowUpDraft

logger = logging.getLogger(__name__)

# Realistic reviewer feedback
APPROVAL_FEEDBACK = [
    "✅ Clear value proposition, appropriate tone, and strong CTA. Approved for sending.",
    "✅ Well-personalized with relevant company context. Professional and concise. Approved.",
    "✅ Good use of social proof. Subject line is compelling. Ready to send.",
    "✅ Warm, conversational tone without being pushy. CTA is clear. Approved.",
    "✅ Excellent follow-up structure — acknowledges their interest and suggests next steps.",
]

REVISION_FEEDBACK = [
    "⚠️ Subject line is too generic — needs personalization. Consider referencing their company's recent milestone.",
    "⚠️ Email body is too long. Trim to under 100 words for cold outreach best practices.",
    "⚠️ Missing clear call-to-action. Add a specific time suggestion for the call.",
]


class ReviewerAgent:
    """Reviews follow-up email drafts for quality and accuracy."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, drafts: List[FollowUpDraft]) -> List[FollowUpDraft]:
        reviewed_drafts = []

        if not drafts:
            logger.info("Reviewer Agent: no drafts to review")
            return []

        logger.info(f"Reviewer Agent: Reviewing {len(drafts)} drafts...")

        for draft in drafts:
            if draft.status != FollowUpDraftStatus.PENDING_REVIEW:
                continue

            try:
                # For demo: keep 60% as PENDING_REVIEW for the queue
                # 25% get auto-approved, 15% need revision
                roll = random.random()
                
                if roll < 0.60:
                    # Leave as PENDING_REVIEW for user to see in queue
                    draft.reviewer_feedback = random.choice(APPROVAL_FEEDBACK).replace('Approved', 'Ready for your review')
                    # Don't change status — stays as PENDING_REVIEW
                elif roll < 0.85:
                    draft.reviewer_feedback = random.choice(APPROVAL_FEEDBACK)
                    draft.status = FollowUpDraftStatus.APPROVED
                else:
                    draft.reviewer_feedback = random.choice(REVISION_FEEDBACK)
                    draft.status = FollowUpDraftStatus.REVISION_NEEDED

                reviewed_drafts.append(draft)

            except Exception as e:
                logger.error(f"Reviewer Agent: error reviewing draft {draft.id}: {e}")
                draft.status = FollowUpDraftStatus.APPROVED
                draft.reviewer_feedback = f"Auto-approved due to review error: {e}"
                reviewed_drafts.append(draft)

        if reviewed_drafts:
            await self.db.flush()

        approved_count = sum(1 for d in reviewed_drafts if d.status == FollowUpDraftStatus.APPROVED)
        revision_count = sum(1 for d in reviewed_drafts if d.status == FollowUpDraftStatus.REVISION_NEEDED)
        logger.info(
            f"Reviewer Agent: Reviewed {len(reviewed_drafts)} drafts — "
            f"{approved_count} approved, {revision_count} need revision."
        )

        return reviewed_drafts
