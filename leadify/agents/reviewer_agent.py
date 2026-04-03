"""
Reviewer Agent — Reviews and quality-checks follow-up drafts.

Stub implementation. Will be replaced with a full LLM-powered
reviewer that checks tone, factual accuracy, and provides
feedback or approval of Writer Agent drafts.
"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from leadify.db.models import FollowUpDraft

logger = logging.getLogger(__name__)


class ReviewerAgent:
    """Reviews follow-up email drafts for quality and accuracy.

    STUB — returns the input drafts unchanged until fully implemented.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, drafts: List[FollowUpDraft]) -> List[FollowUpDraft]:
        """Review each draft and provide feedback or approval.

        Parameters
        ----------
        drafts : list[FollowUpDraft]
            Drafts produced by the WriterAgent this cycle.

        Returns
        -------
        list[FollowUpDraft]
            Reviewed drafts (potentially with updated status/feedback).
        """
        if not drafts:
            logger.info("ReviewerAgent: no drafts to review")
            return []

        logger.warning(
            "ReviewerAgent is a STUB — drafts will be returned as-is. "
            "Replace this with a full implementation."
        )
        return drafts
