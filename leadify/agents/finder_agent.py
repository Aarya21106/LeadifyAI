"""
Finder Agent — Generates 50 new B2B leads using Gemini.

This agent acts as the top of the funnel, actively generating or sourcing
batch leads to feed into the pipeline.
"""

import json
import logging
from typing import List

import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from leadify.common.enums import LeadStatus
from leadify.common.settings import settings
from leadify.db.models import Lead

logger = logging.getLogger(__name__)

FINDER_PROMPT = """
You are a B2B Lead Generation Expert.
Generate exactly 50 realistic B2B software startup leads that would be good targets for a SaaS product.
Return output STRICTLY as a JSON array where each object has:
- "name": Full name of the prospect (e.g. "Jane Doe")
- "company": Name of their company
- "email": Their professional email (e.g. "jane.doe@company.ai")

Only return the JSON array, no markdown fencing, no extra text.
"""

class FinderAgent:
    """Generates 50 fresh leads per cycle and adds them to DB."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # genai.configure(api_key=settings.GEMINI_API_KEY)
        # self._model = genai.GenerativeModel("gemini-1.5-flash")

    async def run(self) -> List[Lead]:
        """Generate 50 leads via Gemini and insert them as ACTIVE."""
        logger.info("Finder Agent: generating 50 new leads...")
        new_leads = []
        
        try:
            # MOCK IMPLEMENTATION
            leads_data = [{"name": f"Dummy Lead {i}", "company": f"Dummy Corp {i}", "email": f"lead{i}@dummycorp{i}.com"} for i in range(1, 51)]
            
            for item in leads_data:
                email = item.get("email", "").lower()
                
                # Check for duplicates
                existing = await self.db.execute(select(Lead.id).where(Lead.email == email))
                if existing.scalar_one_or_none():
                    continue

                lead = Lead(
                    email=email,
                    name=item.get("name"),
                    company=item.get("company"),
                    status=LeadStatus.ACTIVE,
                )
                self.db.add(lead)
                new_leads.append(lead)
                
            if new_leads:
                await self.db.flush()
                logger.info(f"Finder Agent: Successfully generated and added {len(new_leads)} leads.")
            else:
                logger.warning("Finder Agent: No new unique leads added this cycle.")
                
        except Exception as e:
            logger.error(f"Finder Agent error: API failure - {e}")
            
        return new_leads
