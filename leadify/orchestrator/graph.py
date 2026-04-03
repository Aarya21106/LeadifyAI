"""
LangGraph Orchestrator — Multi-agent cycle graph for Leadify AI.

Defines a StateGraph that runs the six agents in the correct order:

    fetch_leads ─┬─► run_watch ──┐
                 └─► run_scout ──┤
                                 ▼
                             run_reader
                                 ▼
                             run_scorer
                                 ▼
                             run_writer
                                 ▼
                            run_reviewer
                                 ▼
                               finalize
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Annotated, Any, List, TypedDict

from langgraph.graph import END, START, StateGraph

from leadify.common.enums import LeadEventType, LeadStatus, FollowUpDraftStatus
from leadify.common.schemas import AgentCycleResult
from leadify.db.models import FollowUpDraft, Lead, LeadEvent, LeadScore
from leadify.db.session import async_session_maker

# Agent imports
from leadify.agents.finder_agent import FinderAgent
from leadify.agents.watch_agent import WatchAgent
from leadify.agents.scout_agent import ScoutAgent
from leadify.agents.reader_agent import ReaderAgent
from leadify.agents.scorer_agent import ScorerAgent
from leadify.agents.writer_agent import WriterAgent
from leadify.agents.reviewer_agent import ReviewerAgent
from leadify.agents.sender_agent import SenderAgent

from sqlalchemy import select
from leadify.api.ws_manager import agent_status_manager

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# WebSocket Helper
# ──────────────────────────────────────────────────────────────────────
async def update_agent_status(cycle_id: str, agent_name: str, status: str, summary: str = None):
    """Centralized helper to update an agent's status and broadcast via WebSocket."""
    current_state = agent_status_manager.last_cycle_status
    if not current_state or current_state.get("cycle_id") != cycle_id:
        return
    
    agent = current_state["agents"][agent_name]
    agent["status"] = status
    if status == "running":
        agent["started_at"] = datetime.utcnow().isoformat()
    elif status in ("done", "error"):
        agent["finished_at"] = datetime.utcnow().isoformat()
    
    if summary is not None:
        agent["summary"] = summary
        
    await agent_status_manager.broadcast(current_state)


# ──────────────────────────────────────────────────────────────────────
# State definition
# ──────────────────────────────────────────────────────────────────────
def _merge_lists(a: list, b: list) -> list:
    """Reducer that merges two lists (used for fan-in on parallel branches)."""
    return a + b


def _merge_errors(a: list[str], b: list[str]) -> list[str]:
    """Reducer for error accumulation across nodes."""
    return a + b


class CycleState(TypedDict, total=False):
    """State flowing through the LangGraph orchestration cycle."""
    cycle_id: str
    leads: list  # list[Lead]
    watch_events: Annotated[list, _merge_lists]
    scout_events: Annotated[list, _merge_lists]
    reader_events: list  # list[LeadEvent]
    scores: list  # list[LeadScore]
    drafts: list  # list[FollowUpDraft]
    reviewed_drafts: list  # list[FollowUpDraft]
    cycle_start: str  # ISO datetime str (must be JSON-serialisable)
    errors: Annotated[list, _merge_errors]


# ──────────────────────────────────────────────────────────────────────
# Node functions
# ──────────────────────────────────────────────────────────────────────

async def run_finder(state: CycleState, config: dict) -> dict:
    """Generate new leads to feed into the pipeline."""
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []

    await update_agent_status(cycle_id, "finder", "running")
    try:
        agent = FinderAgent(db)
        new_leads = await agent.run()
        await update_agent_status(cycle_id, "finder", "done", f"{len(new_leads)} created")
    except Exception as exc:
        msg = f"run_finder: FinderAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "finder", "error", str(exc))

    return {"errors": errors}

async def fetch_leads(state: CycleState, config: dict) -> dict:
    """Load all active leads from the database."""
    db = config["configurable"]["db"]
    errors: list[str] = []

    try:
        result = await db.execute(
            select(Lead).where(Lead.status == LeadStatus.ACTIVE)
        )
        leads = list(result.scalars().all())
        logger.info(f"fetch_leads: loaded {len(leads)} active lead(s)")
    except Exception as exc:
        msg = f"fetch_leads: failed to load leads — {exc}"
        logger.error(msg)
        leads = []
        errors.append(msg)

    return {
        "leads": leads,
        "watch_events": [],
        "scout_events": [],
        "reader_events": [],
        "scores": [],
        "drafts": [],
        "reviewed_drafts": [],
        "errors": errors,
    }


async def run_watch(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []
    events: list = []

    leads = state.get("leads", [])
    if not leads:
        await update_agent_status(cycle_id, "watch", "done", "No leads to process")
        return {"watch_events": [], "errors": []}

    await update_agent_status(cycle_id, "watch", "running")
    try:
        agent = WatchAgent(db)
        events = await agent.run(leads)
        await update_agent_status(cycle_id, "watch", "done", f"{len(events)} events detected")
    except Exception as exc:
        msg = f"run_watch: WatchAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "watch", "error", str(exc))

    return {"watch_events": events, "errors": errors}


async def run_scout(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []
    events: list = []

    leads = state.get("leads", [])
    if not leads:
        await update_agent_status(cycle_id, "scout", "done", "No leads to process")
        return {"scout_events": [], "errors": []}

    await update_agent_status(cycle_id, "scout", "running")
    try:
        agent = ScoutAgent(db)
        events = await agent.run(leads)
        await update_agent_status(cycle_id, "scout", "done", f"{len(events)} signals detected")
    except Exception as exc:
        msg = f"run_scout: ScoutAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "scout", "error", str(exc))

    return {"scout_events": events, "errors": errors}


async def run_reader(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []
    enriched: list = []

    watch_events = state.get("watch_events", [])
    reply_events = [
        ev for ev in watch_events
        if getattr(ev, "event_type", None) == LeadEventType.REPLIED
    ]

    if not reply_events:
        await update_agent_status(cycle_id, "reader", "done", "No replies to classify")
        return {"reader_events": [], "errors": []}

    await update_agent_status(cycle_id, "reader", "running")
    try:
        agent = ReaderAgent(db)
        enriched = await agent.run(reply_events)
        await update_agent_status(cycle_id, "reader", "done", f"{len(enriched)} replies read")
    except Exception as exc:
        msg = f"run_reader: ReaderAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "reader", "error", str(exc))

    return {"reader_events": enriched, "errors": errors}


async def run_scorer(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []
    scores: list = []

    leads = state.get("leads", [])
    if not leads:
        await update_agent_status(cycle_id, "scorer", "done", "No leads to score")
        return {"scores": [], "errors": []}

    await update_agent_status(cycle_id, "scorer", "running")
    try:
        agent = ScorerAgent(db)
        scores = await agent.run(leads)
        await update_agent_status(cycle_id, "scorer", "done", f"{len(scores)} scores updated")
    except Exception as exc:
        msg = f"run_scorer: ScorerAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "scorer", "error", str(exc))

    return {"scores": scores, "errors": errors}


async def run_writer(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []
    drafts: list = []

    leads = state.get("leads", [])
    scores = state.get("scores", [])
    all_events = (
        state.get("watch_events", [])
        + state.get("scout_events", [])
        + state.get("reader_events", [])
    )

    if not leads or not scores:
        await update_agent_status(cycle_id, "writer", "done", "Skipped generation")
        return {"drafts": [], "errors": []}

    await update_agent_status(cycle_id, "writer", "running")
    try:
        agent = WriterAgent(db)
        drafts = await agent.run(leads, scores, all_events)
        await update_agent_status(cycle_id, "writer", "done", f"{len(drafts)} drafts created")
    except Exception as exc:
        msg = f"run_writer: WriterAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "writer", "error", str(exc))

    return {"drafts": drafts, "errors": errors}


async def run_reviewer(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []
    reviewed: list = []

    drafts = state.get("drafts", [])
    if not drafts:
        await update_agent_status(cycle_id, "reviewer", "done", "No drafts to review")
        return {"reviewed_drafts": [], "errors": []}

    await update_agent_status(cycle_id, "reviewer", "running")
    try:
        agent = ReviewerAgent(db)
        reviewed = await agent.run(drafts)
        await update_agent_status(cycle_id, "reviewer", "done", f"{len(reviewed)} drafts reviewed")
    except Exception as exc:
        msg = f"run_reviewer: ReviewerAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "reviewer", "error", str(exc))

    return {"reviewed_drafts": reviewed, "errors": errors}


async def run_sender(state: CycleState, config: dict) -> dict:
    db = config["configurable"]["db"]
    cycle_id = state.get("cycle_id")
    errors: list[str] = []

    reviewed_drafts = state.get("reviewed_drafts", [])
    if not reviewed_drafts:
        await update_agent_status(cycle_id, "sender", "done", "No approved drafts to send")
        return {"errors": []}

    await update_agent_status(cycle_id, "sender", "running")
    try:
        agent = SenderAgent(db)
        sent_count = await agent.run(reviewed_drafts)
        await update_agent_status(cycle_id, "sender", "done", f"{sent_count} emails sent")
    except Exception as exc:
        msg = f"run_sender: SenderAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)
        await update_agent_status(cycle_id, "sender", "error", str(exc))

    return {"errors": errors}


async def finalize(state: CycleState, config: dict) -> dict:
    """Mark the cycle complete and broadcast."""
    cycle_id = state.get("cycle_id")
    errors = state.get("errors", [])
    
    current_state = agent_status_manager.last_cycle_status
    if current_state and current_state.get("cycle_id") == cycle_id:
        current_state["cycle_complete"] = True
        await agent_status_manager.broadcast(current_state)

    logger.info(f"═══ Cycle complete ═══ errors={len(errors)}")
    if errors:
        for err in errors:
            logger.warning(f"  ⚠ {err}")

    return {"errors": errors}


# ──────────────────────────────────────────────────────────────────────
# Graph construction
# ──────────────────────────────────────────────────────────────────────

def build_graph():
    graph = StateGraph(CycleState)

    graph.add_node("run_finder", run_finder)
    graph.add_node("fetch_leads", fetch_leads)
    graph.add_node("run_watch", run_watch)
    graph.add_node("run_scout", run_scout)
    graph.add_node("run_reader", run_reader)
    graph.add_node("run_scorer", run_scorer)
    graph.add_node("run_writer", run_writer)
    graph.add_node("run_reviewer", run_reviewer)
    graph.add_node("run_sender", run_sender)
    graph.add_node("finalize", finalize)

    graph.add_edge(START, "run_finder")
    graph.add_edge("run_finder", "fetch_leads")

    graph.add_edge("fetch_leads", "run_watch")
    graph.add_edge("fetch_leads", "run_scout")

    graph.add_edge("run_watch", "run_reader")
    graph.add_edge("run_scout", "run_reader")

    graph.add_edge("run_reader", "run_scorer")
    graph.add_edge("run_scorer", "run_writer")
    graph.add_edge("run_writer", "run_reviewer")
    graph.add_edge("run_reviewer", "run_sender")
    graph.add_edge("run_sender", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# ──────────────────────────────────────────────────────────────────────
# Cycle runner
# ──────────────────────────────────────────────────────────────────────

async def run_cycle() -> AgentCycleResult:
    compiled = build_graph()
    cycle_id = str(uuid.uuid4())
    start = datetime.utcnow()

    logger.info(f"▶ Starting agent cycle {cycle_id}")
    
    # Broadcast initial reset state
    initial_status = {
        "cycle_id": cycle_id,
        "cycle_start": start.isoformat(),
        "agents": {
            "finder":   { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "watch":    { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "scout":    { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "reader":   { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "scorer":   { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "writer":   { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "reviewer": { "status": "idle", "summary": None, "started_at": None, "finished_at": None },
            "sender":   { "status": "idle", "summary": None, "started_at": None, "finished_at": None }
        },
        "cycle_complete": False
    }
    await agent_status_manager.broadcast(initial_status)

    async with async_session_maker() as db:
        try:
            config = {"configurable": {"db": db}}
            initial_state = {
                "cycle_id": cycle_id,
                "leads": [],
                "watch_events": [],
                "scout_events": [],
                "reader_events": [],
                "scores": [],
                "drafts": [],
                "reviewed_drafts": [],
                "cycle_start": start.isoformat(),
                "errors": [],
            }
            final_state = await compiled.ainvoke(initial_state, config=config)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Agent cycle {cycle_id} failed: {exc}")
            # Mark cycle as complete but failed
            initial_status["cycle_complete"] = True
            await agent_status_manager.broadcast(initial_status)
            
            return AgentCycleResult(
                cycle_id=uuid.UUID(cycle_id),
                timestamp=start,
                agents_involved=["watch"], leads_processed=0, events_detected=0, scores_updated=0, drafts_created=0,
                summary=f"Cycle failed: {exc}", errors=[str(exc)]
            )

    leads = final_state.get("leads", [])
    watch_events = final_state.get("watch_events", [])
    scout_events = final_state.get("scout_events", [])
    scores = final_state.get("scores", [])
    drafts = final_state.get("drafts", [])
    errors = final_state.get("errors", [])
    elapsed = (datetime.utcnow() - start).total_seconds()

    return AgentCycleResult(
        cycle_id=uuid.UUID(cycle_id),
        timestamp=start,
        agents_involved=["watch", "scout", "reader", "scorer", "writer", "reviewer"],
        leads_processed=len(leads),
        events_detected=len(watch_events) + len(scout_events),
        scores_updated=len(scores),
        drafts_created=len(drafts),
        summary=f"Cycle completed in {elapsed:.1f}s.",
        errors=errors,
    )
