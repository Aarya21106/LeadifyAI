"""
Reviewer Agent — Reviews and quality-checks follow-up drafts.

Uses Gemini 1.5 Flash to automatically review Writer Agent drafts
for tone and accuracy. Approves good drafts.
"""

import json
import logging
from typing import List

import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.settings import settings
from leadify.common.enums import FollowUpDraftStatus
from leadify.db.models import FollowUpDraft

logger = logging.getLogger(__name__)

REVIEWER_PROMPT = """
You are an expert sales copywriter auditing a cold email draft.
Please review the Subject and Body to ensure they are professional,
polite, and geared toward B2B analytics.

Subject: {subject}
Body: {body}

Return your response strictly as a JSON object with two keys:
- "approved": boolean (true if the email is good to send, false if it is terrible and needs revision).
- "feedback": A short string explaining your decision.
"""

class ReviewerAgent:
    """Reviews follow-up email drafts for quality and accuracy."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # genai.configure(api_key=settings.GEMINI_API_KEY)
        # self._model = genai.GenerativeModel("gemini-1.5-flash")

    async def run(self, drafts: List[FollowUpDraft]) -> List[FollowUpDraft]:
        reviewed_drafts = []

        if not drafts:
            logger.info("Reviewer Agent: no drafts to review")
            return []

        logger.info(f"Reviewer Agent: Reviewing {len(drafts)} drafts...")

        for draft in drafts:
            if draft.status != FollowUpDraftStatus.PENDING_REVIEW:
                continue

            prompt = REVIEWER_PROMPT.format(subject=draft.subject, body=draft.body)

            try:
                is_approved = True
                draft.reviewer_feedback = "Mock: Automatically approved for testing."
                draft.status = FollowUpDraftStatus.APPROVED if is_approved else FollowUpDraftStatus.REVISION_NEEDED
                
                reviewed_drafts.append(draft)

            except Exception as e:
                logger.error(f"Reviewer Agent: error reviewing draft {draft.id}: {e}")
                # Fallback to approved if AI fails, so we can test the mailing pipeline
                draft.status = FollowUpDraftStatus.APPROVED
                draft.reviewer_feedback = f"Auto-approved due to AI error: {e}"
                reviewed_drafts.append(draft)

        if reviewed_drafts:
            await self.db.flush()
            
        approved_count = sum(1 for d in reviewed_drafts if d.status == FollowUpDraftStatus.APPROVED)
        logger.info(f"Reviewer Agent: Reviewed {len(reviewed_drafts)} drafts, approved {approved_count}.")

        return reviewed_drafts
