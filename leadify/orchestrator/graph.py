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

run_watch and run_scout execute in parallel (fan-out from fetch_leads,
fan-in at run_reader).
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
from leadify.agents.watch_agent import WatchAgent
from leadify.agents.scout_agent import ScoutAgent
from leadify.agents.reader_agent import ReaderAgent
from leadify.agents.scorer_agent import ScorerAgent
from leadify.agents.writer_agent import WriterAgent
from leadify.agents.reviewer_agent import ReviewerAgent

from sqlalchemy import select

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────
# Shared status store — importable by the /agents/status endpoint
# and updated at the end of every cycle by the finalize node.
# ──────────────────────────────────────────────────────────────────────
agent_status_store: dict[str, Any] = {
    "last_run_at": None,
    "leads_processed": 0,
    "drafts_created": 0,
    "drafts_approved": 0,
}


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

    leads: list  # list[Lead]
    watch_events: Annotated[list, _merge_lists]
    scout_events: Annotated[list, _merge_lists]
    reader_events: list  # list[LeadEvent]
    scores: list  # list[LeadScore]
    drafts: list  # list[FollowUpDraft]
    reviewed_drafts: list  # list[FollowUpDraft]
    cycle_start: str  # ISO datetime str (must be JSON-serialisable)
    errors: Annotated[list, _merge_errors]
    # Internal: DB session reference key (not serialised — passed via config)


# ──────────────────────────────────────────────────────────────────────
# Node functions
# ──────────────────────────────────────────────────────────────────────

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
        "cycle_start": datetime.utcnow().isoformat(),
        "watch_events": [],
        "scout_events": [],
        "reader_events": [],
        "scores": [],
        "drafts": [],
        "reviewed_drafts": [],
        "errors": errors,
    }


async def run_watch(state: CycleState, config: dict) -> dict:
    """Run WatchAgent — Gmail polling for opens and replies."""
    db = config["configurable"]["db"]
    errors: list[str] = []
    events: list = []

    leads = state.get("leads", [])
    if not leads:
        logger.info("run_watch: no leads to process")
        return {"watch_events": [], "errors": []}

    try:
        agent = WatchAgent(db)
        events = await agent.run(leads)
    except Exception as exc:
        msg = f"run_watch: WatchAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)

    return {"watch_events": events, "errors": errors}


async def run_scout(state: CycleState, config: dict) -> dict:
    """Run ScoutAgent — Tavily + Gemini signal detection."""
    db = config["configurable"]["db"]
    errors: list[str] = []
    events: list = []

    leads = state.get("leads", [])
    if not leads:
        logger.info("run_scout: no leads to process")
        return {"scout_events": [], "errors": []}

    try:
        agent = ScoutAgent(db)
        events = await agent.run(leads)
    except Exception as exc:
        msg = f"run_scout: ScoutAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)

    return {"scout_events": events, "errors": errors}


async def run_reader(state: CycleState, config: dict) -> dict:
    """Run ReaderAgent — classify reply events from WatchAgent."""
    db = config["configurable"]["db"]
    errors: list[str] = []
    enriched: list = []

    # Filter only reply events from watch results
    watch_events = state.get("watch_events", [])
    reply_events = [
        ev for ev in watch_events
        if getattr(ev, "event_type", None) == LeadEventType.REPLIED
    ]

    if not reply_events:
        logger.info("run_reader: no reply events to classify")
        return {"reader_events": [], "errors": []}

    try:
        agent = ReaderAgent(db)
        enriched = await agent.run(reply_events)
    except Exception as exc:
        msg = f"run_reader: ReaderAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)

    return {"reader_events": enriched, "errors": errors}


async def run_scorer(state: CycleState, config: dict) -> dict:
    """Run ScorerAgent — score all active leads."""
    db = config["configurable"]["db"]
    errors: list[str] = []
    scores: list = []

    leads = state.get("leads", [])
    if not leads:
        logger.info("run_scorer: no leads to score")
        return {"scores": [], "errors": []}

    try:
        agent = ScorerAgent(db)
        scores = await agent.run(leads)
    except Exception as exc:
        msg = f"run_scorer: ScorerAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)

    return {"scores": scores, "errors": errors}


async def run_writer(state: CycleState, config: dict) -> dict:
    """Run WriterAgent — generate follow-up drafts."""
    db = config["configurable"]["db"]
    errors: list[str] = []
    drafts: list = []

    leads = state.get("leads", [])
    scores = state.get("scores", [])
    # Combine all events for context
    all_events = (
        state.get("watch_events", [])
        + state.get("scout_events", [])
        + state.get("reader_events", [])
    )

    if not leads or not scores:
        logger.info("run_writer: no leads or scores — skipping draft generation")
        return {"drafts": [], "errors": []}

    try:
        agent = WriterAgent(db)
        drafts = await agent.run(leads, scores, all_events)
    except Exception as exc:
        msg = f"run_writer: WriterAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)

    return {"drafts": drafts, "errors": errors}


async def run_reviewer(state: CycleState, config: dict) -> dict:
    """Run ReviewerAgent — review and QC follow-up drafts."""
    db = config["configurable"]["db"]
    errors: list[str] = []
    reviewed: list = []

    drafts = state.get("drafts", [])
    if not drafts:
        logger.info("run_reviewer: no drafts to review")
        return {"reviewed_drafts": [], "errors": []}

    try:
        agent = ReviewerAgent(db)
        reviewed = await agent.run(drafts)
    except Exception as exc:
        msg = f"run_reviewer: ReviewerAgent failed — {exc}"
        logger.error(msg)
        errors.append(msg)

    return {"reviewed_drafts": reviewed, "errors": errors}


async def finalize(state: CycleState, config: dict) -> dict:
    """Write cycle summary to logs and update the shared status store."""
    leads = state.get("leads", [])
    watch_events = state.get("watch_events", [])
    scout_events = state.get("scout_events", [])
    reader_events = state.get("reader_events", [])
    scores = state.get("scores", [])
    drafts = state.get("drafts", [])
    reviewed_drafts = state.get("reviewed_drafts", [])
    errors = state.get("errors", [])
    cycle_start = state.get("cycle_start", datetime.utcnow().isoformat())

    total_events = len(watch_events) + len(scout_events)
    drafts_approved = sum(
        1 for d in reviewed_drafts
        if getattr(d, "status", None) == FollowUpDraftStatus.APPROVED
    )

    # Update shared in-memory store (read by /agents/status)
    agent_status_store["last_run_at"] = datetime.utcnow()
    agent_status_store["leads_processed"] = len(leads)
    agent_status_store["drafts_created"] = len(drafts)
    agent_status_store["drafts_approved"] = drafts_approved

    logger.info(
        f"═══ Cycle complete ═══  "
        f"leads={len(leads)}  events={total_events}  "
        f"scores={len(scores)}  drafts={len(drafts)}  "
        f"approved={drafts_approved}  errors={len(errors)}"
    )
    if errors:
        for err in errors:
            logger.warning(f"  ⚠ {err}")

    return {"errors": errors}


# ──────────────────────────────────────────────────────────────────────
# Graph construction
# ──────────────────────────────────────────────────────────────────────

def build_graph():
    """Build and compile the LangGraph StateGraph for one agent cycle.

    Topology:
        START → fetch_leads
        fetch_leads → run_watch  (parallel branch 1)
        fetch_leads → run_scout  (parallel branch 2)
        run_watch   → run_reader (fan-in)
        run_scout   → run_reader (fan-in)
        run_reader  → run_scorer
        run_scorer  → run_writer
        run_writer  → run_reviewer
        run_reviewer → finalize
        finalize    → END
    """
    graph = StateGraph(CycleState)

    # Register nodes
    graph.add_node("fetch_leads", fetch_leads)
    graph.add_node("run_watch", run_watch)
    graph.add_node("run_scout", run_scout)
    graph.add_node("run_reader", run_reader)
    graph.add_node("run_scorer", run_scorer)
    graph.add_node("run_writer", run_writer)
    graph.add_node("run_reviewer", run_reviewer)
    graph.add_node("finalize", finalize)

    # Edges
    graph.add_edge(START, "fetch_leads")

    # Fan-out: fetch_leads → [run_watch, run_scout]
    graph.add_edge("fetch_leads", "run_watch")
    graph.add_edge("fetch_leads", "run_scout")

    # Fan-in: both parallel branches converge at run_reader
    graph.add_edge("run_watch", "run_reader")
    graph.add_edge("run_scout", "run_reader")

    # Sequential pipeline
    graph.add_edge("run_reader", "run_scorer")
    graph.add_edge("run_scorer", "run_writer")
    graph.add_edge("run_writer", "run_reviewer")
    graph.add_edge("run_reviewer", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# ──────────────────────────────────────────────────────────────────────
# Cycle runner (called by scheduler and /agents/run endpoint)
# ──────────────────────────────────────────────────────────────────────

async def run_cycle() -> AgentCycleResult:
    """Execute one full agent cycle and return the result summary.

    Creates its own DB session, runs the compiled graph, commits,
    and returns an AgentCycleResult.
    """
    compiled = build_graph()
    cycle_id = uuid.uuid4()

    logger.info(f"▶ Starting agent cycle {cycle_id}")
    start = datetime.utcnow()

    async with async_session_maker() as db:
        try:
            config = {"configurable": {"db": db}}
            final_state = await compiled.ainvoke({}, config=config)
            await db.commit()
        except Exception as exc:
            await db.rollback()
            logger.error(f"Agent cycle {cycle_id} failed: {exc}")
            return AgentCycleResult(
                cycle_id=cycle_id,
                timestamp=start,
                agents_involved=["watch", "scout", "reader", "scorer", "writer", "reviewer"],
                leads_processed=0,
                events_detected=0,
                scores_updated=0,
                drafts_created=0,
                summary=f"Cycle failed: {exc}",
                errors=[str(exc)],
            )

    # Build result from final state
    leads = final_state.get("leads", [])
    watch_events = final_state.get("watch_events", [])
    scout_events = final_state.get("scout_events", [])
    scores = final_state.get("scores", [])
    drafts = final_state.get("drafts", [])
    errors = final_state.get("errors", [])
    total_events = len(watch_events) + len(scout_events)

    elapsed = (datetime.utcnow() - start).total_seconds()

    result = AgentCycleResult(
        cycle_id=cycle_id,
        timestamp=start,
        agents_involved=["watch", "scout", "reader", "scorer", "writer", "reviewer"],
        leads_processed=len(leads),
        events_detected=total_events,
        scores_updated=len(scores),
        drafts_created=len(drafts),
        summary=(
            f"Cycle completed in {elapsed:.1f}s. "
            f"{len(leads)} leads, {total_events} events, "
            f"{len(scores)} scores, {len(drafts)} drafts."
        ),
        errors=errors,
    )

    logger.info(f"✔ Cycle {cycle_id} finished in {elapsed:.1f}s")
    return result
