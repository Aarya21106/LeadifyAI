from fastapi import APIRouter

from leadify.common.schemas import AgentCycleResult, AgentStatusRead
from leadify.orchestrator.graph import run_cycle, agent_status_store

router = APIRouter()


@router.post("/run", response_model=AgentCycleResult)
async def run_agent_cycle():
    """Manually trigger one full agent cycle.

    Runs the complete LangGraph orchestration pipeline
    (watch → scout → reader → scorer → writer → reviewer)
    and returns the cycle result summary.
    """
    result = await run_cycle()
    return result


@router.get("/status", response_model=AgentStatusRead)
async def agent_status():
    """Return last cycle timestamp, leads processed, drafts generated.

    Reads from the in-memory status store updated by the orchestrator's
    finalize node at the end of every cycle.
    """
    return AgentStatusRead(
        last_cycle_at=agent_status_store.get("last_run_at"),
        leads_processed=agent_status_store.get("leads_processed", 0),
        drafts_generated=agent_status_store.get("drafts_created", 0),
    )
