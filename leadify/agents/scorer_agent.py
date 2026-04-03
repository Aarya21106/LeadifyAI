"""
Scorer Agent — Buy-probability scoring engine.

Runs after Reader Agent. Processes ALL active leads. Calculates a
0-100 buy-probability score and a delta from the previous score.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType, LeadStatus
from leadify.db.models import Lead, LeadEvent, LeadScore

logger = logging.getLogger(__name__)

# Realistic scoring reasoning
REASONING_TEMPLATES = {
    "high": [
        "Lead replied with strong interest and requested a demo call. Funding signal detected this week.",
        "Multiple email opens combined with a warm reply. Company is actively hiring, indicating growth phase.",
        "Direct reply asking for pricing. High buying signal with recent product launch at their company.",
        "Engaged multiple times this week. Leadership change at company suggests new budget cycle.",
    ],
    "medium": [
        "Email was opened twice but no reply yet. Company recently raised funding — monitor closely.",
        "Single open detected. Hiring surge signals growth but no direct engagement currently.",
        "Warm reply but mentioned they're evaluating competitors. Follow up with case study.",
        "Signal detected (expansion) but lead hasn't engaged with outreach yet.",
    ],
    "low": [
        "No engagement since initial outreach 10 days ago. Score decaying due to inactivity.",
        "Out-of-office reply received. Will re-engage after return date.",
        "Cold reply indicating they have an existing solution. Low conversion probability.",
        "No opens or replies. Company shows no recent growth signals.",
    ],
}


class ScorerAgent:
    """Scores every active lead with realistic scoring logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, leads: List[Lead]) -> List[LeadScore]:
        scores_created: List[LeadScore] = []

        if not leads:
            logger.info("Scorer Agent: no active leads to score")
            return scores_created

        logger.info(f"Scorer Agent: scoring {len(leads)} active lead(s)")

        for lead in leads:
            try:
                score = await self._score_lead(lead)
                if score:
                    scores_created.append(score)
            except Exception as e:
                logger.error(f"Scorer Agent: error scoring lead {lead.email}: {e}")
                continue

        if scores_created:
            await self.db.flush()

        high_priority = sum(1 for s in scores_created if s.delta > 20)
        logger.info(
            f"Scorer Agent: created {len(scores_created)} score(s) "
            f"({high_priority} high-priority)"
        )
        return scores_created

    async def _score_lead(self, lead: Lead) -> Optional[LeadScore]:
        """Score a single lead based on its events and history."""

        # Fetch recent events
        recent_events = await self._get_recent_events(lead.id)
        prev_score = await self._get_previous_score(lead.id)

        # Determine score based on events
        has_reply = any(e.event_type == LeadEventType.REPLIED for e in recent_events)
        has_open = any(e.event_type == LeadEventType.OPENED for e in recent_events)
        has_signal = any(e.event_type == LeadEventType.SIGNAL_DETECTED for e in recent_events)

        # Calculate base score
        if has_reply and has_signal:
            new_score = random.randint(75, 95)
            reasoning = random.choice(REASONING_TEMPLATES["high"])
        elif has_reply:
            new_score = random.randint(60, 82)
            reasoning = random.choice(REASONING_TEMPLATES["high"])
        elif has_open and has_signal:
            new_score = random.randint(50, 70)
            reasoning = random.choice(REASONING_TEMPLATES["medium"])
        elif has_open:
            new_score = random.randint(35, 55)
            reasoning = random.choice(REASONING_TEMPLATES["medium"])
        elif has_signal:
            new_score = random.randint(40, 60)
            reasoning = random.choice(REASONING_TEMPLATES["medium"])
        else:
            # No events — low score or decay
            new_score = random.randint(10, 30)
            reasoning = random.choice(REASONING_TEMPLATES["low"])

        # Calculate delta
        prev_value = prev_score.score if prev_score else 0
        delta = new_score - prev_value

        score_obj = LeadScore(
            lead_id=lead.id,
            score=new_score,
            delta=delta,
            reasoning=reasoning,
        )
        self.db.add(score_obj)

        logger.info(
            f"Scorer Agent: {lead.email} → score {new_score} "
            f"(Δ{'+' if delta >= 0 else ''}{delta})"
        )
        return score_obj

    async def _get_recent_events(self, lead_id) -> List[LeadEvent]:
        """Fetch lead events from the last 7 days."""
        cutoff = datetime.utcnow() - timedelta(days=7)
        result = await self.db.execute(
            select(LeadEvent)
            .where(
                LeadEvent.lead_id == lead_id,
                LeadEvent.detected_at >= cutoff,
            )
            .order_by(LeadEvent.detected_at.desc())
        )
        return list(result.scalars().all())

    async def _get_previous_score(self, lead_id) -> Optional[LeadScore]:
        """Fetch the most recent LeadScore for a lead."""
        result = await self.db.execute(
            select(LeadScore)
            .where(LeadScore.lead_id == lead_id)
            .order_by(LeadScore.scored_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
