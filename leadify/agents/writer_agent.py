"""
Writer Agent — Generates follow-up email drafts.

Stub implementation. Will be replaced with a full LLM-powered
draft generator that uses lead scores, events, and reader
classifications to craft personalised follow-up emails.
"""

import logging
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from leadify.db.models import Lead, LeadEvent, LeadScore, FollowUpDraft

logger = logging.getLogger(__name__)


class WriterAgent:
    """Generates follow-up email drafts for high-scoring leads.

    STUB — returns an empty list until fully implemented.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        leads: List[Lead],
        scores: List[LeadScore],
        events: List[LeadEvent],
    ) -> List[FollowUpDraft]:
        """Generate follow-up drafts for leads that warrant one.

        Parameters
        ----------
        leads : list[Lead]
            All active leads this cycle.
        scores : list[LeadScore]
            Scores produced by the ScorerAgent this cycle.
        events : list[LeadEvent]
            All events detected this cycle (watch + scout + reader).

        Returns
        -------
        list[FollowUpDraft]
            Newly created draft objects.
        """
        logger.warning(
            "WriterAgent is a STUB — no drafts will be generated. "
            "Replace this with a full implementation."
        )
        return []
