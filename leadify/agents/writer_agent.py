"""
Writer Agent — Generates follow-up email drafts.

Uses lead data, scores, and events to craft personalised follow-up emails.
"""

import logging
import random
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from leadify.common.enums import FollowUpDraftStatus
from leadify.db.models import Lead, LeadEvent, LeadScore, FollowUpDraft

logger = logging.getLogger(__name__)

# Realistic email templates based on signal/score context
EMAIL_TEMPLATES = [
    {
        "subject": "Quick follow-up — {company}'s analytics strategy",
        "body": "Hi {name},\n\nI noticed {company} has been scaling rapidly — congrats on the momentum!\n\nWe've helped companies like yours cut pipeline analysis time by 40% with our analytics platform. Would love to share a quick case study.\n\nWould a 10-minute call this week work?\n\nBest,\nAlex from Leadify",
        "signal_summary": "Scaling/growth signals detected",
    },
    {
        "subject": "Congrats on the raise, {name}! 🎉",
        "body": "Hi {name},\n\nJust saw the news about {company}'s funding round — fantastic milestone!\n\nAs you scale the team, having the right analytics infrastructure early makes a huge difference. We power pipeline analytics for 200+ SaaS companies.\n\nHappy to show you a 5-minute demo — no commitment.\n\nCheers,\nAlex from Leadify",
        "signal_summary": "Funding round detected",
    },
    {
        "subject": "Thought you'd find this interesting, {name}",
        "body": "Hi {name},\n\nI came across {company} while researching innovative teams in your space. Impressed by what you're building.\n\nWe recently published a report on how top-performing SDR teams use data to 3x their pipeline. Thought your team might find it valuable.\n\nWorth a quick look? I can send it over.\n\nBest,\nAlex from Leadify",
        "signal_summary": "Content-led outreach approach",
    },
    {
        "subject": "Re: {company}'s growth — a quick idea",
        "body": "Hi {name},\n\nI noticed {company} is hiring aggressively on the sales side — exciting growth phase!\n\nWhen teams scale quickly, pipeline visibility often becomes the bottleneck. Our platform gives sales leaders real-time insights without the spreadsheet chaos.\n\nWould love to share how similar companies handled this. Quick call this week?\n\nBest,\nAlex from Leadify",
        "signal_summary": "Hiring surge detected",
    },
    {
        "subject": "{name}, one question for you",
        "body": "Hi {name},\n\nQuick question: how is {company} currently tracking lead engagement across channels?\n\nWe've found that most teams lose 30-40% of qualified leads simply because engagement signals aren't surfaced in time. Our platform fixes exactly that.\n\nIf this resonates, I'd love 10 minutes of your time.\n\nBest,\nAlex from Leadify",
        "signal_summary": "Generic engagement-focused",
    },
    {
        "subject": "Following up — your reply about next week",
        "body": "Hi {name},\n\nGreat to hear you're interested in exploring this further! As mentioned, we work with SaaS companies like {company} to streamline pipeline analytics.\n\nHere's what I suggest:\n- A quick 15-min walkthrough of how we'd help your team\n- No slides, just a live demo tailored to {company}\n\nDoes Tuesday or Wednesday afternoon work?\n\nLooking forward to it,\nAlex from Leadify",
        "signal_summary": "Reply follow-up (interested lead)",
    },
]


class WriterAgent:
    """Generates follow-up email drafts for leads."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(
        self,
        leads: List[Lead],
        scores: List[LeadScore],
        events: List[LeadEvent],
    ) -> List[FollowUpDraft]:
        drafts_created = []
        logger.info(f"Writer Agent: Evaluating {len(leads)} leads for drafting...")

        score_map = {s.lead_id: s for s in scores}

        for lead in leads:
            if not lead.company or not lead.name:
                continue

            # Skip if they already have a PENDING_REVIEW draft
            existing_draft = await self.db.execute(
                select(FollowUpDraft.id).where(
                    FollowUpDraft.lead_id == lead.id,
                    FollowUpDraft.status == FollowUpDraftStatus.PENDING_REVIEW
                )
            )
            if existing_draft.scalar_one_or_none():
                continue

            score_obj = score_map.get(lead.id)
            score_val = score_obj.score if score_obj else 0

            # Only draft for leads with score >= 30 (active engagement)
            if score_val < 30:
                continue

            # Pick a template — higher-scoring leads get reply-focused ones
            if score_val >= 70:
                template = EMAIL_TEMPLATES[5]  # Reply follow-up
            elif score_val >= 50:
                template = random.choice(EMAIL_TEMPLATES[0:4])  # Signal-based
            else:
                template = random.choice(EMAIL_TEMPLATES[2:5])  # General outreach

            subject = template["subject"].format(name=lead.name.split()[0], company=lead.company)
            body = template["body"].format(name=lead.name.split()[0], company=lead.company)

            try:
                draft = FollowUpDraft(
                    lead_id=lead.id,
                    subject=subject,
                    body=body,
                    score_at_draft=score_val,
                    signal_summary=template["signal_summary"],
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
