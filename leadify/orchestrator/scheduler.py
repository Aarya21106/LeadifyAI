"""
Scheduler — APScheduler-based recurring agent cycle runner.

Uses AsyncIOScheduler to run the LangGraph agent cycle at a
configurable interval (default: every 60 minutes).

On startup:
    1. Run one immediate cycle
    2. Schedule recurring cycles

The scheduler is started/stopped from FastAPI's lifespan handler.
"""

from __future__ import annotations

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from leadify.orchestrator.graph import run_cycle, agent_status_store

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: AsyncIOScheduler | None = None


def _get_cycle_minutes() -> int:
    """Read the cycle interval from the environment (default 60)."""
    raw = os.getenv("AGENT_CYCLE_MINUTES", "60")
    try:
        minutes = int(raw)
        return max(1, minutes)  # Floor at 1 minute
    except ValueError:
        logger.warning(
            f"Invalid AGENT_CYCLE_MINUTES='{raw}', falling back to 60"
        )
        return 60


async def _run_scheduled_cycle() -> None:
    """Wrapper called by APScheduler — runs one agent cycle and logs the result."""
    try:
        logger.info("Scheduler: starting scheduled agent cycle")
        result = await run_cycle()
        logger.info(
            f"Scheduler: cycle finished — "
            f"leads={result.leads_processed}, "
            f"events={result.events_detected}, "
            f"drafts={result.drafts_created}, "
            f"errors={len(result.errors)}"
        )
    except Exception as exc:
        logger.error(f"Scheduler: cycle crashed — {exc}", exc_info=True)


async def start_scheduler() -> None:
    """Start the APScheduler and run one immediate cycle.

    Call this from FastAPI's lifespan handler on startup.
    """
    global _scheduler

    interval_minutes = _get_cycle_minutes()
    logger.info(
        f"Scheduler: initialising (interval={interval_minutes} min)"
    )

    _scheduler = AsyncIOScheduler()

    # Schedule the recurring job
    _scheduler.add_job(
        _run_scheduled_cycle,
        trigger=IntervalTrigger(minutes=interval_minutes),
        id="agent_cycle",
        name="Leadify Agent Cycle",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler: started")

    # Run one immediate cycle (fire-and-forget so startup isn't blocked)
    asyncio.create_task(_run_scheduled_cycle())


async def stop_scheduler() -> None:
    """Gracefully shut down the scheduler.

    Call this from FastAPI's lifespan handler on shutdown.
    """
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler: stopped")
        _scheduler = None
