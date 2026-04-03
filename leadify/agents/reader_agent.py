"""
Reader Agent — Gemini 1.5 Flash reply classifier.

Runs after Watch Agent. Processes any leads that received a new 'replied'
event this cycle. Classifies each reply (interested / warm / cold /
out_of_office / unsubscribe), extracts objections, a key quote, and a
suggested follow-up angle.

Stores the classification result back into the LeadEvent raw_data and
marks leads as dead on unsubscribe.
"""

import json
import logging
from typing import List

import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType, LeadStatus
from leadify.common.settings import settings
from leadify.db.models import Lead, LeadEvent

logger = logging.getLogger(__name__)

CLASSIFICATION_SYSTEM_PROMPT = """You are analyzing a reply to a cold sales email. Classify the reply and extract key information.
Return JSON only:
{
  "classification": "interested" | "warm" | "cold" | "out_of_office" | "unsubscribe",
  "objections": string[],  // list of specific objections raised, empty array if none
  "key_quote": string | null,  // the single most important sentence from the reply
  "suggested_angle": string | null  // what should the follow-up address?
}"""


class ReaderAgent:
    """Classifies reply emails using Gemini 1.5 Flash."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # genai.configure(api_key=settings.GEMINI_API_KEY)
        # self._model = genai.GenerativeModel(
        #     "gemini-1.5-flash",
        #     system_instruction=CLASSIFICATION_SYSTEM_PROMPT,
        # )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def run(self, reply_events: List[LeadEvent]) -> List[LeadEvent]:
        """Classify each reply event and enrich its raw_data.

        Parameters
        ----------
        reply_events : list[LeadEvent]
            LeadEvent objects with event_type == REPLIED produced by the
            Watch Agent in the current cycle.

        Returns
        -------
        list[LeadEvent]
            The same events, now enriched with classification data inside
            their raw_data JSONB.
        """
        enriched: List[LeadEvent] = []

        if not reply_events:
            logger.info("Reader Agent: no reply events to classify")
            return enriched

        logger.info(
            f"Reader Agent: classifying {len(reply_events)} reply event(s)"
        )

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

        logger.info(
            f"Reader Agent: enriched {len(enriched)}/{len(reply_events)} events"
        )
        return enriched

    # ------------------------------------------------------------------
    # Per-event classification
    # ------------------------------------------------------------------
    async def _classify_event(self, event: LeadEvent) -> None:
        """Classify a single reply event and update its raw_data in-place."""
        # Extract email body text from the event's stored data.
        # Watch Agent stores the reply snippet in raw_data['snippet'].
        body_text = event.raw_data.get("snippet", "")
        subject = event.raw_data.get("subject", "")

        if not body_text:
            logger.warning(
                f"Reader Agent: empty body for event {event.id}, skipping"
            )
            return

        # Build user prompt with the actual email content
        user_prompt = (
            f"Subject: {subject}\n\n"
            f"Email body:\n{body_text}"
        )

        classification = await self._call_gemini(user_prompt, event.lead_id)
        if classification is None:
            return

        # ---- Enrich raw_data with classification results ----
        # SQLAlchemy JSONB mutation: replace the dict so the ORM detects
        # the change (in-place dict mutation is not tracked).
        updated_data = dict(event.raw_data)
        updated_data["classification"] = classification.get("classification")
        updated_data["objections"] = classification.get("objections", [])
        updated_data["key_quote"] = classification.get("key_quote")
        updated_data["suggested_angle"] = classification.get("suggested_angle")
        event.raw_data = updated_data

        # ---- Handle unsubscribe → mark lead dead ----
        if classification.get("classification") == "unsubscribe":
            await self._mark_lead_dead(event)

        logger.info(
            f"Reader Agent: lead {event.lead_id} classified as "
            f"'{classification.get('classification')}'"
        )

    # ------------------------------------------------------------------
    # Gemini call
    # ------------------------------------------------------------------
    async def _call_gemini(self, user_prompt: str, lead_id) -> dict | None:
        """Mock Gemini."""
        return {
            "classification": "warm",
            "objections": [],
            "key_quote": "Sounds interesting, let's talk next week.",
            "suggested_angle": "Suggest times for next week."
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    async def _mark_lead_dead(self, event: LeadEvent) -> None:
        """Set lead.status = DEAD when the reply is an unsubscribe."""
        lead = await self.db.get(Lead, event.lead_id)
        if lead and lead.status != LeadStatus.DEAD:
            lead.status = LeadStatus.DEAD
            logger.info(
                f"Reader Agent: marked lead {lead.email} as DEAD "
                f"(unsubscribe detected)"
            )
