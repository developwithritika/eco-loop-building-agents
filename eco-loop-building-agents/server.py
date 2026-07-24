"""
server.py
---------
FastAPI server exposing the building simulation over HTTP.

Endpoints:
    GET  /state   -> returns the current building state
    POST /action  -> applies a control action and returns the updated state

Run with:
    uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import ActionRequest, ActionResponse, BuildingState
from simulator import BuildingSimulator

app = FastAPI(
    title="Eco-Loop Building Agents API",
    description="AI-powered building energy management simulation API.",
    version="1.0.0",
)

# Permissive CORS so a local dashboard or the controller script can reach
# the API without extra configuration. Tighten this for production use.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# A single shared simulator instance backs the whole API process. In a
# multi-building deployment this would instead be a registry keyed by
# building ID.
simulator = BuildingSimulator()


@app.get("/state", response_model=BuildingState, tags=["Building"])
def get_state() -> BuildingState:
    """
    Return the current building state, advancing the simulation by one
    cycle before returning it so repeated polling reflects a live system.

    Returns:
        The current BuildingState.
    """
    return simulator.generate_state()


@app.post("/action", response_model=ActionResponse, tags=["Building"])
def post_action(request: ActionRequest) -> ActionResponse:
    """
    Apply a control action to the building simulation.

    Args:
        request: The ActionRequest containing the action name and an
            optional reason.

    Returns:
        An ActionResponse containing the applied action and the
        resulting building state.

    Raises:
        HTTPException: If the action cannot be applied due to an
            unexpected internal error.
    """
    try:
        updated_state = simulator.apply_action(request.action)
    except Exception as exc:  # noqa: BLE001 - convert any failure to HTTP 500
        raise HTTPException(
            status_code=500, detail=f"Failed to apply action: {exc}"
        ) from exc

    return ActionResponse(
        applied_action=request.action,
        reason=request.reason,
        updated_state=updated_state,
    )


@app.get("/health", tags=["System"])
def health_check() -> dict:
    """
    Simple liveness probe endpoint.

    Returns:
        A small status payload.
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "server:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True,
    )
