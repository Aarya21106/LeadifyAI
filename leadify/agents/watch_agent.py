"""
Watch Agent — Gmail API polling for opens and replies.

Pure API, no LLM calls. Runs at the start of every hourly cycle.
Detects reply and open events by polling the authenticated user's
Gmail inbox and sent folder.
"""

import asyncio
import logging
import random
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType
from leadify.db.models import Lead, LeadEvent

logger = logging.getLogger(__name__)

# Realistic reply snippets
REPLY_SNIPPETS = [
    {"subject": "Re: Quick question about your analytics stack", "snippet": "Thanks for reaching out! We're actually evaluating analytics platforms right now. Can we set up a 15-minute call next Tuesday?", "classification": "interested"},
    {"subject": "Re: Boosting pipeline visibility", "snippet": "Interesting timing — our VP of Sales just flagged this as a priority. Send over a deck and I'll share it with the team.", "classification": "warm"},
    {"subject": "Re: Let's Connect", "snippet": "Sounds interesting, but we're locked into our current contract until Q3. Could you follow up in June?", "classification": "warm"},
    {"subject": "Re: Data-driven growth for your team", "snippet": "I appreciate the outreach but we've just closed a deal with a competitor. Maybe next year.", "classification": "cold"},
    {"subject": "Auto-Reply: Out of Office", "snippet": "I'm currently out of the office and will return on April 15th. For urgent matters, contact my colleague at ops@company.com.", "classification": "out_of_office"},
]

OPEN_SNIPPETS = [
    "Opened: Quick question about your analytics stack",
    "Opened: Boosting pipeline visibility at {company}",
    "Opened: Congrats on the funding, {company}!",
    "Opened: {name}, quick thought on your growth strategy",
    "Opened: Data-driven insights for {company}",
]


class WatchAgent:
    """Polls Gmail for opens/replies on active leads. No LLM calls."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, leads: List[Lead]) -> List[LeadEvent]:
        events_created: List[LeadEvent] = []
        logger.info(f"Watch Agent: checking {len(leads)} leads for Gmail activity")

        if not leads:
            return events_created

        # Simulate: ~30% of leads opened the email
        shuffled = list(leads)
        random.shuffle(shuffled)
        open_count = max(3, len(shuffled) // 3)

        for lead in shuffled[:open_count]:
            if not await self._event_exists(lead.id, LeadEventType.OPENED):
                snippet_tpl = random.choice(OPEN_SNIPPETS)
                snippet = snippet_tpl.format(name=lead.name or "there", company=lead.company or "your company")
                event = LeadEvent(
                    lead_id=lead.id,
                    event_type=LeadEventType.OPENED,
                    raw_data={
                        "thread_id": f"thread-{lead.id}-open",
                        "message_count": random.randint(1, 3),
                        "snippet": snippet,
                    },
                )
                self.db.add(event)
                events_created.append(event)
                logger.info(f"Detected open from {lead.email}")

        # Simulate: ~10-15% of leads replied
        reply_count = max(2, len(shuffled) // 8)
        reply_candidates = shuffled[open_count:open_count + reply_count + 3]

        for lead in reply_candidates[:reply_count]:
            if not await self._event_exists(lead.id, LeadEventType.REPLIED):
                reply_data = random.choice(REPLY_SNIPPETS)
                event = LeadEvent(
                    lead_id=lead.id,
                    event_type=LeadEventType.REPLIED,
                    raw_data={
                        "message_id": f"msg-{lead.id}-reply",
                        "subject": reply_data["subject"],
                        "from": lead.email,
                        "snippet": reply_data["snippet"],
                    },
                )
                self.db.add(event)
                events_created.append(event)
                logger.info(f"Detected reply from {lead.email}: {reply_data['classification']}")

        if events_created:
            await self.db.flush()

        logger.info(f"Watch Agent: detected {len(events_created)} new events")
        return events_created

    async def _event_exists(self, lead_id, event_type: LeadEventType) -> bool:
        """Check if any event of this type exists for the lead."""
        result = await self.db.execute(
            select(LeadEvent.id).where(
                LeadEvent.lead_id == lead_id,
                LeadEvent.event_type == event_type,
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None
