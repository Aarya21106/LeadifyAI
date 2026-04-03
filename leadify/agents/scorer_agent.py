"""
Scorer Agent — Gemini 1.5 Flash buy-probability scoring engine.

Runs after Reader Agent. Processes ALL active leads (not just those with
new events this cycle). Calculates a 0–100 buy-probability score and a
delta from the previous score. The delta is the most important output:
leads with large positive deltas are prioritised for follow-up drafts.

Writes a new LeadScore row for every lead every cycle.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import google.generativeai as genai
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType, LeadStatus
from leadify.common.settings import settings
from leadify.db.models import Lead, LeadEvent, LeadScore

logger = logging.getLogger(__name__)

SCORING_SYSTEM_PROMPT = (
    "You are a B2B sales scoring engine. Given the signals below, "
    "calculate a buy probability score.\n"
    "Rules:\n"
    "- Score 0–100 representing likelihood to convert in next 30 days\n"
    "- A reply classified as 'interested' should push score above 70\n"
    "- A funding signal + no reply = score 40–55 range\n"
    "- No activity after 14 days = score decays by 5 points per cycle\n"
    "- An 'out_of_office' reply should not significantly change score\n"
    "- Leads with score delta > +20 this cycle are HIGH PRIORITY\n"
    'Return JSON only: { "score": integer, "delta": integer, '
    '"reasoning": "string (max 2 sentences)" }'
)


class ScorerAgent:
    """Scores every active lead using Gemini 1.5 Flash."""

    def __init__(self, db: AsyncSession):
        self.db = db
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self._model = genai.GenerativeModel(
            "gemini-1.5-flash",
            system_instruction=SCORING_SYSTEM_PROMPT,
        )

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def run(self, leads: List[Lead]) -> List[LeadScore]:
        """Score every active lead and persist new LeadScore rows.

        Parameters
        ----------
        leads : list[Lead]
            All active leads to score this cycle.

        Returns
        -------
        list[LeadScore]
            Newly created LeadScore objects (one per lead).
        """
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
                logger.error(
                    f"Scorer Agent: error scoring lead {lead.email}: {e}"
                )
                continue

        if scores_created:
            await self.db.flush()

        logger.info(
            f"Scorer Agent: created {len(scores_created)} score(s) "
            f"({self._high_priority_count(scores_created)} high-priority)"
        )
        return scores_created

    # ------------------------------------------------------------------
    # Per-lead scoring
    # ------------------------------------------------------------------
    async def _score_lead(self, lead: Lead) -> Optional[LeadScore]:
        """Gather context for a lead, call Gemini, and persist the score."""

        # 1. Fetch recent events (last 7 days)
        recent_events = await self._get_recent_events(lead.id)

        # 2. Fetch previous score
        prev_score = await self._get_previous_score(lead.id)

        # 3. Calculate lead age
        lead_age_days = self._calculate_lead_age(lead)

        # 4. Extract reader classifications from recent reply events
        classifications = self._extract_classifications(recent_events)

        # 5. Build context prompt
        context = self._build_context(
            lead=lead,
            recent_events=recent_events,
            prev_score=prev_score,
            lead_age_days=lead_age_days,
            classifications=classifications,
        )

        # 6. Call Gemini
        result = await self._call_gemini(context, lead)
        if result is None:
            return None

        # 7. Compute authoritative delta server-side
        new_score = max(0, min(100, result.get("score", 0)))
        prev_value = prev_score.score if prev_score else 0
        delta = new_score - prev_value

        # 8. Persist
        score_obj = LeadScore(
            lead_id=lead.id,
            score=new_score,
            delta=delta,
            reasoning=result.get("reasoning", ""),
        )
        self.db.add(score_obj)

        logger.info(
            f"Scorer Agent: {lead.email} → score {new_score} "
            f"(Δ{'+' if delta >= 0 else ''}{delta})"
        )
        return score_obj

    # ------------------------------------------------------------------
    # Data fetching helpers
    # ------------------------------------------------------------------
    async def _get_recent_events(self, lead_id) -> List[LeadEvent]:
        """Fetch lead events from the last 7 days, most recent first."""
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

    @staticmethod
    def _calculate_lead_age(lead: Lead) -> int:
        """Days since first_email_sent_at, or 0 if not set."""
        if not lead.first_email_sent_at:
            return 0
        delta = datetime.utcnow() - lead.first_email_sent_at
        return max(0, delta.days)

    @staticmethod
    def _extract_classifications(events: List[LeadEvent]) -> List[dict]:
        """Pull reader-agent classification data from reply events."""
        classifications = []
        for event in events:
            if event.event_type != LeadEventType.REPLIED:
                continue
            raw = event.raw_data or {}
            classification = raw.get("classification")
            if classification:
                classifications.append(
                    {
                        "classification": classification,
                        "objections": raw.get("objections", []),
                        "key_quote": raw.get("key_quote"),
                        "suggested_angle": raw.get("suggested_angle"),
                        "detected_at": (
                            event.detected_at.isoformat()
                            if event.detected_at
                            else None
                        ),
                    }
                )
        return classifications

    # ------------------------------------------------------------------
    # Context builder
    # ------------------------------------------------------------------
    def _build_context(
        self,
        lead: Lead,
        recent_events: List[LeadEvent],
        prev_score: Optional[LeadScore],
        lead_age_days: int,
        classifications: List[dict],
    ) -> str:
        """Build a structured text prompt with all scoring signals."""
        sections: List[str] = []

        # Lead overview
        sections.append(
            f"## Lead\n"
            f"- Email: {lead.email}\n"
            f"- Company: {lead.company or 'Unknown'}\n"
            f"- Status: {lead.status.value}\n"
            f"- Lead age: {lead_age_days} day(s) since first email"
        )

        # Previous score
        if prev_score:
            sections.append(
                f"## Previous Score\n"
                f"- Score: {prev_score.score}\n"
                f"- Delta last cycle: {prev_score.delta}\n"
                f"- Reasoning: {prev_score.reasoning or 'N/A'}\n"
                f"- Scored at: {prev_score.scored_at.isoformat()}"
            )
        else:
            sections.append("## Previous Score\nNo previous score (first cycle).")

        # Recent events summary
        if recent_events:
            event_lines = []
            for ev in recent_events:
                ts = ev.detected_at.isoformat() if ev.detected_at else "?"
                snippet = ""
                if ev.raw_data:
                    snippet = ev.raw_data.get("snippet", "")[:120]
                event_lines.append(
                    f"- [{ts}] {ev.event_type.value}"
                    + (f": {snippet}" if snippet else "")
                )
            sections.append(
                f"## Events (last 7 days): {len(recent_events)}\n"
                + "\n".join(event_lines)
            )
        else:
            sections.append("## Events (last 7 days)\nNo events detected.")

        # Reader classifications
        if classifications:
            cls_lines = []
            for c in classifications:
                cls_lines.append(
                    f"- Classification: {c['classification']}\n"
                    f"  Objections: {', '.join(c['objections']) if c['objections'] else 'none'}\n"
                    f"  Key quote: {c['key_quote'] or 'N/A'}\n"
                    f"  Suggested angle: {c['suggested_angle'] or 'N/A'}"
                )
            sections.append(
                "## Reply Classifications\n" + "\n".join(cls_lines)
            )

        # Days since last activity (for decay detection)
        if recent_events:
            most_recent = recent_events[0].detected_at
            days_since = (datetime.utcnow() - most_recent).days if most_recent else None
            if days_since is not None:
                sections.append(
                    f"## Activity Recency\n"
                    f"Days since last event: {days_since}"
                )
        else:
            sections.append(
                f"## Activity Recency\n"
                f"No events in the last 7 days. Lead age is {lead_age_days} day(s)."
            )

        return "\n\n".join(sections)

    # ------------------------------------------------------------------
    # Gemini call
    # ------------------------------------------------------------------
    async def _call_gemini(self, context: str, lead: Lead) -> Optional[dict]:
        """Send scoring context to Gemini and return parsed JSON result."""
        try:
            response = await self._model.generate_content_async(
                context,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )

            raw_text = response.text.strip()
            result = json.loads(raw_text)

            # Validate required fields
            if "score" not in result:
                logger.error(
                    f"Gemini response missing 'score' for {lead.email}"
                )
                return None

            # Coerce score to int within bounds
            result["score"] = max(0, min(100, int(result["score"])))

            return result

        except json.JSONDecodeError as e:
            logger.error(
                f"Gemini returned invalid JSON for {lead.email}: {e}"
            )
            return None
        except Exception as e:
            logger.error(f"Gemini API error for {lead.email}: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _high_priority_count(scores: List[LeadScore]) -> int:
        """Count leads with delta > +20 (high priority for follow-ups)."""
        return sum(1 for s in scores if s.delta > 20)
