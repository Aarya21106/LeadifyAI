import uuid
from datetime import datetime

from fastapi import APIRouter

from leadify.common.schemas import AgentCycleResult, AgentStatusRead

router = APIRouter()

# In-memory store for last cycle result (replaced by DB in Phase 3)
_last_cycle: AgentCycleResult | None = None


@router.post("/run", response_model=AgentCycleResult)
async def run_agent_cycle():
    """Manually trigger one full agent cycle (stub — returns mock data)."""
    global _last_cycle

    _last_cycle = AgentCycleResult(
        cycle_id=uuid.uuid4(),
        timestamp=datetime.utcnow(),
        agents_involved=["watch", "scout", "reader", "scorer", "writer", "reviewer"],
        leads_processed=0,
        events_detected=0,
        scores_updated=0,
        drafts_created=0,
        summary="Stub cycle — no agents implemented yet",
        errors=[],
    )
    return _last_cycle


@router.get("/status", response_model=AgentStatusRead)
async def agent_status():
    """Return last cycle timestamp, leads processed, drafts generated."""
    if _last_cycle is None:
        return AgentStatusRead()

    return AgentStatusRead(
        last_cycle_at=_last_cycle.timestamp,
        leads_processed=_last_cycle.leads_processed,
        drafts_generated=_last_cycle.drafts_created,
    )
