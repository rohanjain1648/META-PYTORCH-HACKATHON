# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - Client

"""
Incident Triage Environment Client.

Provides a client for connecting to the Incident Triage Environment server
via HTTP. Supports both async and sync usage.

Example:
    >>> import asyncio, aiohttp
    >>> async def main():
    ...     client = IncidentTriageEnvClient("http://localhost:8000")
    ...     result = await client.reset(task_name="single_incident")
    ...     print(result["observation"]["investigation_results"])
    ...     result = await client.step("investigate", "database_primary", {"aspect": "logs"})
    ...     print(result["observation"]["investigation_results"])
    >>> asyncio.run(main())
"""

import asyncio
import json
from typing import Any, Optional

import requests


class IncidentTriageEnvClient:
    """
    HTTP Client for the Incident Triage Environment.

    Provides a simple interface for interacting with the environment server
    over HTTP REST endpoints.
    """

    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize client.

        Args:
            base_url: URL of the environment server
        """
        self.base_url = base_url.rstrip("/")

    def reset(
        self,
        task_name: str = "single_incident",
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
    ) -> dict:
        """
        Reset the environment.

        Args:
            task_name: Task to run ("single_incident", "multi_incident", "cascading_failure")
            seed: Random seed for reproducibility
            episode_id: Optional custom episode ID

        Returns:
            Response dict with observation, reward, done
        """
        body = {"task_name": task_name}
        if seed is not None:
            body["seed"] = seed
        if episode_id is not None:
            body["episode_id"] = episode_id

        resp = requests.post(f"{self.base_url}/reset", json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def step(
        self,
        action_type: str,
        target: str,
        parameters: Optional[dict] = None,
    ) -> dict:
        """
        Execute one step.

        Args:
            action_type: One of "investigate", "diagnose", "prioritize", "remediate", "escalate", "verify"
            target: Service name or incident ID
            parameters: Action-specific parameters

        Returns:
            Response dict with observation, reward, done
        """
        body = {
            "action_type": action_type,
            "target": target,
            "parameters": parameters or {},
        }
        resp = requests.post(f"{self.base_url}/step", json=body, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict:
        """Get current environment state."""
        resp = requests.get(f"{self.base_url}/state", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def grade(self) -> dict:
        """Get the final grade for the current episode."""
        resp = requests.get(f"{self.base_url}/grade", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> dict:
        """Check server health."""
        resp = requests.get(f"{self.base_url}/health", timeout=5)
        resp.raise_for_status()
        return resp.json()

    def tasks(self) -> list:
        """List available tasks."""
        resp = requests.get(f"{self.base_url}/tasks", timeout=10)
        resp.raise_for_status()
        return resp.json().get("tasks", [])

    def close(self):
        """Clean up (no-op for HTTP client)."""
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
