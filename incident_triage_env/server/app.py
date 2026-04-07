# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - FastAPI Server

"""
FastAPI application for the Incident Triage Environment.

Exposes the environment over HTTP endpoints compatible with OpenEnv.

Usage:
    uvicorn incident_triage_env.server.app:app --host 0.0.0.0 --port 8000
"""

import json
import os
import traceback
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .incident_environment import IncidentTriageEnvironment


# ═══════════════════════════════════════════════════════════════════════════════
# APP SETUP
# ═══════════════════════════════════════════════════════════════════════════════

env = IncidentTriageEnvironment()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    print("🚀 Incident Triage Environment starting up...")
    yield
    print("🛑 Incident Triage Environment shutting down...")


app = FastAPI(
    title="Incident Triage Environment",
    description="OpenEnv-compliant environment for IT/DevOps incident response triage",
    version="1.0.0",
    lifespan=lifespan,
)


# ═══════════════════════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════════════════════

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "environment": "incident_triage_env", "version": "1.0.0"}


# ═══════════════════════════════════════════════════════════════════════════════
# OPENENV API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/reset")
async def reset(request: Request):
    """
    Reset the environment for a new episode.

    Body (optional):
        {
            "task_name": "single_incident" | "multi_incident" | "cascading_failure",
            "seed": 42,
            "episode_id": "custom-id"
        }
    """
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        task_name = body.get("task_name", "single_incident")
        seed = body.get("seed", None)
        episode_id = body.get("episode_id", None)

        obs = env.reset(
            task_name=task_name,
            seed=seed,
            episode_id=episode_id,
        )

        return _observation_to_response(obs)

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()},
        )


@app.post("/step")
async def step(request: Request):
    """
    Execute one step in the environment.

    Body:
        {
            "action_type": "investigate" | "diagnose" | "prioritize" | "remediate" | "escalate" | "verify",
            "target": "service_name or incident_id",
            "parameters": { ... action-specific params ... }
        }
    """
    try:
        body = await request.json()

        action = {
            "action_type": body.get("action_type", ""),
            "target": body.get("target", ""),
            "parameters": body.get("parameters", {}),
        }

        obs = env.step(action)

        return _observation_to_response(obs)

    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e), "traceback": traceback.format_exc()},
        )


@app.get("/state")
async def get_state():
    """Get current environment state."""
    try:
        state = env.state
        return {
            "episode_id": state.episode_id,
            "step_count": state.step_count,
            "task_name": state.task_name,
            "scenario_id": state.scenario_id,
            "total_incidents": state.total_incidents,
            "resolved_incidents": state.resolved_incidents,
            "correct_diagnoses": state.correct_diagnoses,
            "misdiagnosed": state.misdiagnosed,
            "correct_priorities": state.correct_priorities,
            "correct_remediations": state.correct_remediations,
            "failed_remediations": state.failed_remediations,
            "time_elapsed": state.time_elapsed,
            "actions_taken": state.actions_taken,
            "accumulated_reward": state.accumulated_reward,
            "done": state.done,
        }
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@app.get("/tasks")
async def list_tasks():
    """List available tasks."""
    from ..tasks import list_tasks as _list_tasks
    return {"tasks": _list_tasks()}


@app.get("/grade")
async def get_grade():
    """Get the final grade for the current episode."""
    try:
        grade = env.get_grade()
        return grade
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _observation_to_response(obs) -> dict:
    """Convert an Observation to a JSON-serializable response."""
    metadata = obs.metadata if obs.metadata else {}

    return {
        "observation": {
            "alerts": metadata.get("alerts", []),
            "system_status": metadata.get("system_status", {}),
            "logs": metadata.get("logs", []),
            "investigation_results": metadata.get("investigation_results", ""),
            "time_elapsed": metadata.get("time_elapsed", 0.0),
            "incidents_resolved": metadata.get("incidents_resolved", 0),
            "incidents_remaining": metadata.get("incidents_remaining", 0),
            "last_action_error": metadata.get("last_action_error"),
            "task_name": metadata.get("task_name", ""),
            "current_step": metadata.get("current_step", 0),
            "max_steps": metadata.get("max_steps", 10),
        },
        "reward": obs.reward if obs.reward else 0.0,
        "done": obs.done if obs.done else False,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Entry point for direct execution."""
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    main()
