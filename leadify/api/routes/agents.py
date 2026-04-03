from fastapi import APIRouter, WebSocket, WebSocketDisconnect, BackgroundTasks

from leadify.api.ws_manager import agent_status_manager
from leadify.common.schemas import AgentCycleResult
from leadify.orchestrator.graph import run_cycle

router = APIRouter()


@router.post("/run")
async def run_agent_cycle(background_tasks: BackgroundTasks):
    """Manually trigger one full agent cycle in the background.

    Runs the complete LangGraph orchestration pipeline
    (watch → scout → reader → scorer → writer → reviewer)
    and broadcasts the progress over WebSocket.
    """
    background_tasks.add_task(run_cycle)
    return {"status": "started", "message": "Agent cycle initiated. Connect via WebSocket for real-time status."}

@router.get("/status")
async def agent_status():
    """Return fallback HTTP status tracking active cycles.

    Reads from the ws_manager's last_cycle_status.
    """
    return agent_status_manager.last_cycle_status

@router.websocket("/ws")
async def agent_websocket(websocket: WebSocket):
    await agent_status_manager.connect(websocket)
    try:
        while True:
            # We don't expect messages from the client in this one-way broadcast,
            # but we need to receive to handle disconnects cleanly.
            await websocket.receive_text()
    except WebSocketDisconnect:
        agent_status_manager.disconnect(websocket)
