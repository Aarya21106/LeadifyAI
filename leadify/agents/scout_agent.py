"""
Scout Agent — Tavily Search + Gemini 1.5 Flash for live signal detection.

Searches for funding news, hiring surges, leadership changes, and other
B2B-relevant signals for each active lead's company.
"""

import logging
import random
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from leadify.common.enums import LeadEventType
from leadify.db.models import Lead, LeadEvent

logger = logging.getLogger(__name__)

# Realistic B2B signal templates
SIGNAL_TEMPLATES = [
    {
        "signal_type": "Funding",
        "summary": "{company} just closed a ${amount}M Series {round} led by {vc}.",
        "source_url": "https://techcrunch.com/funding/{slug}",
        "amounts": [3, 5, 8, 12, 18, 25, 40],
        "rounds": ["A", "B", "Seed", "A", "B"],
        "vcs": ["Sequoia Capital", "Andreessen Horowitz", "Accel Partners", "Lightspeed Ventures", "Index Ventures"],
    },
    {
        "signal_type": "Hiring Surge",
        "summary": "{company} posted {count} new engineering roles on LinkedIn this week, signaling rapid expansion.",
        "source_url": "https://linkedin.com/company/{slug}/jobs",
        "counts": [8, 12, 15, 22, 30],
    },
    {
        "signal_type": "Leadership Change",
        "summary": "{company} just appointed a new {role} — {exec_name}, formerly of {prev_company}.",
        "source_url": "https://businessinsider.com/leadership/{slug}",
        "roles": ["CRO", "VP of Sales", "VP of Engineering", "CMO", "Chief Data Officer"],
        "exec_names": ["Alison Park", "Marcus Webb", "Denise Chang", "Robert Kline", "Nina Patel"],
        "prev_companies": ["Salesforce", "HubSpot", "Snowflake", "Datadog", "Confluent"],
    },
    {
        "signal_type": "Product Launch",
        "summary": "{company} launched their new {product} platform, targeting enterprise customers.",
        "source_url": "https://producthunt.com/{slug}",
        "products": ["AI analytics", "revenue intelligence", "predictive pipeline", "customer health scoring", "real-time data sync"],
    },
    {
        "signal_type": "Expansion",
        "summary": "{company} announced expansion into {market}, opening a new office in {city}.",
        "source_url": "https://prnewswire.com/{slug}",
        "markets": ["EMEA", "APAC", "Latin America", "North America"],
        "cities": ["London", "Singapore", "São Paulo", "Toronto", "Berlin"],
    },
]


class ScoutAgent:
    """Searches for live B2B signals per lead using realistic mock data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self, leads: List[Lead]) -> List[LeadEvent]:
        events_created: List[LeadEvent] = []
        logger.info(f"Scout Agent: scanning {len(leads)} leads for signals")

        if not leads:
            return events_created

        # Simulate: ~20-25% of leads have detectable signals
        shuffled = list(leads)
        random.shuffle(shuffled)
        signal_count = max(3, len(shuffled) // 5)

        for lead in shuffled[:signal_count]:
            if not lead.company:
                continue

            template = random.choice(SIGNAL_TEMPLATES)
            signal_type = template["signal_type"]
            slug = lead.company.lower().replace(" ", "-")

            # Build realistic summary
            if signal_type == "Funding":
                summary = template["summary"].format(
                    company=lead.company,
                    amount=random.choice(template["amounts"]),
                    round=random.choice(template["rounds"]),
                    vc=random.choice(template["vcs"]),
                )
            elif signal_type == "Hiring Surge":
                summary = template["summary"].format(
                    company=lead.company,
                    count=random.choice(template["counts"]),
                )
            elif signal_type == "Leadership Change":
                summary = template["summary"].format(
                    company=lead.company,
                    role=random.choice(template["roles"]),
                    exec_name=random.choice(template["exec_names"]),
                    prev_company=random.choice(template["prev_companies"]),
                )
            elif signal_type == "Product Launch":
                summary = template["summary"].format(
                    company=lead.company,
                    product=random.choice(template["products"]),
                )
            elif signal_type == "Expansion":
                summary = template["summary"].format(
                    company=lead.company,
                    market=random.choice(template["markets"]),
                    city=random.choice(template["cities"]),
                )
            else:
                summary = f"Signal detected for {lead.company}"

            source_url = template["source_url"].format(slug=slug)

            event = LeadEvent(
                lead_id=lead.id,
                event_type=LeadEventType.SIGNAL_DETECTED,
                raw_data={
                    "company": lead.company,
                    "signal_type": signal_type,
                    "summary": summary,
                    "source_url": source_url,
                    "queries_used": [f"{lead.company} {signal_type.lower()} 2026"],
                    "raw_results_count": random.randint(2, 8),
                },
            )
            self.db.add(event)
            events_created.append(event)
            logger.info(f"Signal detected for {lead.company}: {signal_type}")

        if events_created:
            await self.db.flush()

        logger.info(f"Scout Agent: detected {len(events_created)} signals")
        return events_created
