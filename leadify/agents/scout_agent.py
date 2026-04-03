"""
Scout Agent — Tavily Search + Gemini 1.5 Flash for live signal detection.

Searches for funding news, hiring surges, leadership changes, and other
B2B-relevant signals for each active lead's company. Uses Gemini to
extract structured signal data from raw search results.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import List, Optional

import google.generativeai as genai
from tavily import TavilyClient
from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType
from leadify.common.settings import settings
from leadify.db.models import Lead, LeadEvent

logger = logging.getLogger(__name__)

# Gemini extraction prompt
SIGNAL_EXTRACTION_PROMPT = """Given these search results about {company}, extract any significant signals relevant to a B2B sale.
A signal is: funding news, expansion plans, leadership changes, hiring surges, or product launches.
If no meaningful signal exists, return null.

Search results:
{results}

Return JSON: {{ "signal_found": bool, "summary": string|null, "signal_type": string|null, "source_url": string|null }}"""


class ScoutAgent:
    """Searches for live B2B signals per lead using Tavily + Gemini 1.5 Flash."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # self._tavily = TavilyClient(api_key=settings.TAVILY_API_KEY)
        # genai.configure(api_key=settings.GEMINI_API_KEY)
        # self._model = genai.GenerativeModel("gemini-1.5-flash")

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    async def run(self, leads: List[Lead]) -> List[LeadEvent]:
        events_created: List[LeadEvent] = []
        logger.info(f"Scout Agent: scanning {len(leads)} leads for signals")

        # Mock: 5 dummy signals
        for lead in leads[10:15]:
            if not lead.company:
                continue
            event = LeadEvent(
                lead_id=lead.id,
                event_type=LeadEventType.SIGNAL_DETECTED,
                raw_data={
                    "company": lead.company,
                    "signal_type": "Funding",
                    "summary": f"{lead.company} just raised a $5M seed round.",
                    "source_url": "https://dummytechcrunch.com/funding",
                    "queries_used": [],
                    "raw_results_count": 1,
                },
            )
            self.db.add(event)
            events_created.append(event)
            logger.info(f"Signal detected for {lead.company}")

        if events_created:
            await self.db.flush()

        logger.info(f"Scout Agent: detected {len(events_created)} signals")
        return events_created

    # ------------------------------------------------------------------
    # Per-lead scouting
    # ------------------------------------------------------------------
    async def _scout_lead(self, lead: Lead) -> Optional[LeadEvent]:
        """Run search queries for a lead, analyse with Gemini, create event if signal found."""
        current_year = datetime.utcnow().year
        company = lead.company

        queries = [
            f"{company} funding OR investment OR raised {current_year}",
            f"{company} hiring OR job opening site:linkedin.com/jobs OR site:indeed.com",
        ]

        # Collect search results from both queries
        all_results: List[dict] = []
        for query in queries:
            results = await self._search(query)
            all_results.extend(results)

        if not all_results:
            logger.debug(f"No search results for {company}")
            return None

        # Format results for Gemini
        results_text = self._format_results(all_results)

        # Extract signal via Gemini
        signal = await self._extract_signal(company, results_text)
        if not signal or not signal.get("signal_found"):
            logger.debug(f"No signal detected for {company}")
            return None

        # Create LeadEvent
        event = LeadEvent(
            lead_id=lead.id,
            event_type=LeadEventType.SIGNAL_DETECTED,
            raw_data={
                "company": company,
                "signal_type": signal.get("signal_type"),
                "summary": signal.get("summary"),
                "source_url": signal.get("source_url"),
                "queries_used": queries,
                "raw_results_count": len(all_results),
            },
        )
        self.db.add(event)
        logger.info(
            f"Signal detected for {company}: "
            f"{signal.get('signal_type')} — {signal.get('summary', '')[:80]}"
        )
        return event

    # ------------------------------------------------------------------
    # Tavily search
    # ------------------------------------------------------------------
    async def _search(self, query: str) -> List[dict]:
        """Run a Tavily search query. Returns list of result dicts."""
        try:
            response = await asyncio.to_thread(
                self._tavily.search,
                query=query,
                max_results=5,
                search_depth="basic",
            )
            return response.get("results", [])
        except Exception as e:
            logger.error(f"Tavily search error for '{query}': {e}")
            return []

    @staticmethod
    def _format_results(results: List[dict]) -> str:
        """Format Tavily results into a readable string for the LLM."""
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "Untitled")
            url = r.get("url", "")
            content = r.get("content", "")[:300]
            lines.append(f"[{i}] {title}\n    URL: {url}\n    {content}\n")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Gemini signal extraction
    # ------------------------------------------------------------------
    async def _extract_signal(self, company: str, results_text: str) -> Optional[dict]:
        """Send search results to Gemini 1.5 Flash for signal extraction.

        Returns parsed JSON dict or None on failure.
        """
        prompt = SIGNAL_EXTRACTION_PROMPT.format(
            company=company,
            results=results_text,
        )

        try:
            response = await self._model.generate_content_async(
                prompt,
                generation_config=genai.GenerationConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )

            raw_text = response.text.strip()
            signal = json.loads(raw_text)
            return signal

        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned invalid JSON for {company}: {e}")
            return None
        except Exception as e:
            logger.error(f"Gemini API error for {company}: {e}")
            return None
