"""
Writer Agent — Generates follow-up email drafts using Gemini.

Uses lead data and events to craft personalised follow-up emails.
"""

import json
import logging
from typing import List

import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from leadify.common.settings import settings
from leadify.common.enums import FollowUpDraftStatus
from leadify.db.models import Lead, LeadEvent, LeadScore, FollowUpDraft

logger = logging.getLogger(__name__)

WRITER_PROMPT = """
You are an expert SDR (Sales Development Representative).
Write a cold email to {name} at {company}.
Keep it short, punchy, and professional. The goal is to set up a 10-minute discovery call around our B2B SaaS analytics platform.

Return your response strictly as a JSON object with two keys:
- "subject": The email subject line.
- "body": The main email body.
"""

class WriterAgent:
    """Generates follow-up email drafts for leads."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # genai.configure(api_key=settings.GEMINI_API_KEY)
        # self._model = genai.GenerativeModel("gemini-1.5-flash")

    async def run(
        self,
        leads: List[Lead],
        scores: List[LeadScore],
        events: List[LeadEvent],
    ) -> List[FollowUpDraft]:
        drafts_created = []

        logger.info(f"Writer Agent: Evaluating {len(leads)} leads for drafting...")

        # For mapping lead_id to their latest score and signals
        score_map = {s.lead_id: s.score for s in scores}

        for lead in leads:
            # Check if this lead already has an email sent or a pending draft
            # In a real app we'd have a more sophisticated pipeline logic state
            # For this MVP, we just generate a draft if they have a company and name
            if not lead.company or not lead.name:
                continue

            # Skip if they already have an active PENDING_REVIEW draft
            existing_draft = await self.db.execute(
                select(FollowUpDraft.id).where(
                    FollowUpDraft.lead_id == lead.id,
                    FollowUpDraft.status == FollowUpDraftStatus.PENDING_REVIEW
                )
            )
            if existing_draft.scalar_one_or_none():
                continue

            prompt = WRITER_PROMPT.format(name=lead.name, company=lead.company)
            score = score_map.get(lead.id, 0)

            try:
                draft = FollowUpDraft(
                    lead_id=lead.id,
                    subject=f"Quick question for {lead.company}",
                    body=f"Hi {lead.name},\nWe love what {lead.company} is doing. Let's connect.",
                    score_at_draft=score,
                    writer_model="gemini-1.5-flash",
                    status=FollowUpDraftStatus.PENDING_REVIEW,
                )
                self.db.add(draft)
                drafts_created.append(draft)

            except Exception as e:
                logger.error(f"Writer Agent: error generating draft for {lead.email}: {e}")

        if drafts_created:
            await self.db.flush()

        logger.info(f"Writer Agent: Generated {len(drafts_created)} drafts.")
        return drafts_created
