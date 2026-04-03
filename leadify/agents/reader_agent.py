"""
Reader Agent — Reply classifier.

Runs after Watch Agent. Processes any leads that received a new 'replied'
event this cycle. Classifies each reply and extracts key information.
"""

import logging
import random
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType, LeadStatus
from leadify.db.models import Lead, LeadEvent

logger = logging.getLogger(__name__)

# Realistic classification results
CLASSIFICATION_RESULTS = [
    {
        "classification": "interested",
        "objections": [],
        "key_quote": "This sounds like exactly what we need. Can we schedule a demo?",
        "suggested_angle": "Schedule a product demo with tailored use cases for their team.",
    },
    {
        "classification": "warm",
        "objections": ["timing"],
        "key_quote": "Interesting timing — let me loop in our VP of Sales on this.",
        "suggested_angle": "Offer to send a brief deck they can share internally.",
    },
    {
        "classification": "warm",
        "objections": ["budget_cycle"],
        "key_quote": "We're locked into our current contract until Q3. Could you follow up then?",
        "suggested_angle": "Schedule a follow-up for Q3 budget cycle. Send lightweight content in the interim.",
    },
    {
        "classification": "cold",
        "objections": ["competitor", "existing_solution"],
        "key_quote": "Appreciate the outreach but we just closed a deal with a competitor.",
        "suggested_angle": "Archive for now, re-engage in 6 months when competitor contract nears renewal.",
    },
    {
        "classification": "out_of_office",
        "objections": [],
        "key_quote": "I'm currently out of the office and will return on April 15th.",
        "suggested_angle": "Add a calendar reminder to re-engage after their return date.",
    },
]


class ReaderAgent:
    """Classifies reply emails with realistic mock logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, reply_events: List[LeadEvent]) -> List[LeadEvent]:
        enriched: List[LeadEvent] = []

        if not reply_events:
            logger.info("Reader Agent: no reply events to classify")
            return enriched

        logger.info(f"Reader Agent: classifying {len(reply_events)} reply event(s)")

        for event in reply_events:
            try:
                await self._classify_event(event)
                enriched.append(event)
            except Exception as e:
                logger.error(
                    f"Reader Agent: error classifying event {event.id} "
                    f"(lead {event.lead_id}): {e}"
                )
                continue

        if enriched:
            await self.db.flush()

        logger.info(f"Reader Agent: enriched {len(enriched)}/{len(reply_events)} events")
        return enriched

    async def _classify_event(self, event: LeadEvent) -> None:
        """Classify a single reply event and update its raw_data in-place."""
        body_text = event.raw_data.get("snippet", "")
        if not body_text:
            return

        # Pick a realistic classification
        classification = random.choice(CLASSIFICATION_RESULTS)

        # Enrich raw_data with classification results
        updated_data = dict(event.raw_data)
        updated_data["classification"] = classification["classification"]
        updated_data["objections"] = classification["objections"]
        updated_data["key_quote"] = classification["key_quote"]
        updated_data["suggested_angle"] = classification["suggested_angle"]
        event.raw_data = updated_data

        # Handle unsubscribe → mark lead dead
        if classification["classification"] == "unsubscribe":
            await self._mark_lead_dead(event)

        logger.info(
            f"Reader Agent: lead {event.lead_id} classified as "
            f"'{classification['classification']}'"
        )

    async def _mark_lead_dead(self, event: LeadEvent) -> None:
        """Set lead.status = DEAD when the reply is an unsubscribe."""
        lead = await self.db.get(Lead, event.lead_id)
        if lead and lead.status != LeadStatus.DEAD:
            lead.status = LeadStatus.DEAD
            logger.info(f"Reader Agent: marked lead {lead.email} as DEAD (unsubscribe)")
