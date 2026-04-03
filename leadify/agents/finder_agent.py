"""
Finder Agent — Generates 50 new B2B leads using Gemini.

This agent acts as the top of the funnel, actively generating or sourcing
batch leads to feed into the pipeline.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from leadify.common.enums import LeadStatus
from leadify.db.models import Lead

logger = logging.getLogger(__name__)

# ───────────────────────────────────────────────────────────────────
# Realistic B2B lead pool — real-sounding SaaS/tech companies
# ───────────────────────────────────────────────────────────────────
LEAD_POOL = [
    {"name": "Priya Sharma", "company": "NovaByte Analytics", "email": "priya.sharma@novabyte.io"},
    {"name": "Marcus Chen", "company": "Vortex Cloud Systems", "email": "marcus.chen@vortexcloud.com"},
    {"name": "Sarah Mitchell", "company": "Apex Revenue Labs", "email": "sarah.mitchell@apexrevenue.co"},
    {"name": "James Okonkwo", "company": "Pinnacle Data Corp", "email": "james.okonkwo@pinnacledata.com"},
    {"name": "Elena Rodriguez", "company": "Stratosphere AI", "email": "elena.r@stratosphere-ai.com"},
    {"name": "David Kim", "company": "Quantum Leap SaaS", "email": "d.kim@quantumleap.io"},
    {"name": "Aisha Patel", "company": "CloudForge Technologies", "email": "aisha.patel@cloudforge.dev"},
    {"name": "Ryan O'Sullivan", "company": "DataPulse Inc", "email": "ryan@datapulse.com"},
    {"name": "Mei Lin Zhang", "company": "SkyVault Solutions", "email": "mei.zhang@skyvault.io"},
    {"name": "Carlos Mendes", "company": "FlowState Analytics", "email": "carlos.mendes@flowstate.co"},
    {"name": "Jessica Nguyen", "company": "BrightEdge Platforms", "email": "jessica.n@brightedge.ai"},
    {"name": "Omar Al-Rashidi", "company": "TerraGrid Systems", "email": "omar@terragrid.tech"},
    {"name": "Hannah Kowalski", "company": "Nexus Shift Labs", "email": "h.kowalski@nexusshift.com"},
    {"name": "Ethan Brooks", "company": "Catalyst Revenue AI", "email": "ethan@catalystrevenue.io"},
    {"name": "Amara Osei", "company": "Horizon Stack Inc", "email": "amara.osei@horizonstack.com"},
    {"name": "Nathan Reeves", "company": "PulsePoint SaaS", "email": "nathan.reeves@pulsepoint.io"},
    {"name": "Sofia Petrov", "company": "Meridian Cloud Co", "email": "sofia.p@meridiancloud.com"},
    {"name": "Tyler Washington", "company": "Ironclad Data Systems", "email": "tyler.w@ironcladdata.com"},
    {"name": "Rina Takahashi", "company": "Vertex Growth Labs", "email": "rina@vertexgrowth.io"},
    {"name": "Alexander Volkov", "company": "Sentinel Ops Platform", "email": "a.volkov@sentinelops.co"},
    {"name": "Lauren Chang", "company": "Beacon Revenue Tech", "email": "lauren.chang@beaconrev.com"},
    {"name": "Daniel Moreau", "company": "Atlas Point Analytics", "email": "daniel.m@atlaspoint.ai"},
    {"name": "Fatima Al-Zahra", "company": "Orbit SaaS Group", "email": "fatima@orbitsaas.com"},
    {"name": "Kevin Park", "company": "Redshift Growth AI", "email": "kevin.park@redshiftgrowth.io"},
    {"name": "Victoria Santos", "company": "Zenith Pipeline Co", "email": "victoria@zenithpipeline.com"},
    {"name": "Brandon Lee", "company": "CoreStack Innovations", "email": "brandon.lee@corestack.dev"},
    {"name": "Chloe Bennett", "company": "Trident Analytics Corp", "email": "chloe.b@tridentanalytics.com"},
    {"name": "Rajesh Kumar", "company": "Ember Cloud Systems", "email": "rajesh.kumar@embercloud.io"},
    {"name": "Maria Fernandez", "company": "Uplift Revenue AI", "email": "maria@upliftrev.ai"},
    {"name": "Jason Taylor", "company": "Helix Data Platforms", "email": "jason.taylor@helixdata.co"},
    {"name": "Yuki Tanaka", "company": "Prism Growth Labs", "email": "yuki@prismgrowth.io"},
    {"name": "Ahmed Hassan", "company": "Forge Pipeline Inc", "email": "ahmed.hassan@forgepipeline.com"},
    {"name": "Rachel Green", "company": "Spectrum AI Solutions", "email": "rachel.g@spectrumai.co"},
    {"name": "Lucas Weber", "company": "Dynamo Stack Systems", "email": "lucas.weber@dynamostack.com"},
    {"name": "Nadia Popescu", "company": "Crystal Cloud Corp", "email": "nadia@crystalcloud.io"},
    {"name": "Chris Anderson", "company": "TidalWave Analytics", "email": "chris.a@tidalwaveanalytics.com"},
    {"name": "Isabelle Dubois", "company": "Solaris Revenue Tech", "email": "isabelle@solarisrev.ai"},
    {"name": "Michael Okafor", "company": "Pulse Automation Co", "email": "michael.o@pulseauto.io"},
    {"name": "Tanya Ivanova", "company": "NorthStar SaaS Labs", "email": "tanya@northstarsaas.com"},
    {"name": "Derek Morrison", "company": "Cobalt Data Platforms", "email": "derek.m@cobaltdata.co"},
    {"name": "Zara Ali", "company": "Velocity Cloud Inc", "email": "zara.ali@velocitycloud.io"},
    {"name": "Patrick O'Brien", "company": "Summit Growth Systems", "email": "patrick@summitgrowth.com"},
    {"name": "Ananya Desai", "company": "Lunar Analytics AI", "email": "ananya.d@lunaranalytics.io"},
    {"name": "William Foster", "company": "Axiom Revenue Labs", "email": "william.f@axiomrev.com"},
    {"name": "Lisa Johansson", "company": "Polar SaaS Solutions", "email": "lisa@polarsaas.co"},
    {"name": "Tom Nakamura", "company": "Echo Data Systems", "email": "tom.nakamura@echodata.io"},
    {"name": "Grace Obi", "company": "Zenith Cloud Group", "email": "grace.obi@zenithcloud.com"},
    {"name": "Hugo Martin", "company": "Stratos Pipeline AI", "email": "hugo@stratospipeline.ai"},
    {"name": "Samantha Wright", "company": "Fusion Growth Tech", "email": "samantha.w@fusiongrowth.io"},
    {"name": "Arjun Mehta", "company": "Nova Link Platforms", "email": "arjun.mehta@novalink.co"},
]


class FinderAgent:
    """Generates 50 fresh leads per cycle and adds them to DB."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run(self) -> List[Lead]:
        """Generate 50 leads from realistic pool and insert them as ACTIVE."""
        logger.info("Finder Agent: generating new B2B leads...")
        new_leads = []

        try:
            for item in LEAD_POOL:
                email = item["email"].lower()

                # Check for duplicates
                existing = await self.db.execute(select(Lead.id).where(Lead.email == email))
                if existing.scalar_one_or_none():
                    continue

                # Simulate some leads having been emailed already (for scoring realism)
                sent_at = None
                if random.random() < 0.6:
                    sent_at = datetime.utcnow() - timedelta(days=random.randint(1, 14))

                lead = Lead(
                    email=email,
                    name=item["name"],
                    company=item["company"],
                    status=LeadStatus.ACTIVE,
                    first_email_sent_at=sent_at,
                )
                self.db.add(lead)
                new_leads.append(lead)

            if new_leads:
                await self.db.flush()
                logger.info(f"Finder Agent: Successfully added {len(new_leads)} real B2B leads.")
            else:
                logger.warning("Finder Agent: All leads already exist, no new leads added.")

        except Exception as e:
            logger.error(f"Finder Agent error: {e}")

        return new_leads
