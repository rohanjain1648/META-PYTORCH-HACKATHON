# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - Models

"""
Incident Triage Environment Models.

Defines the typed Action, Observation, and State models
for the incident response triage environment.
"""

from typing import Any, Optional

from pydantic import Field
from openenv.core.env_server.types import Action, Observation, State


class IncidentTriageAction(Action):
    """
    An action the agent can take in the incident triage environment.

    Action Types:
        - "investigate": Examine a system/service for more details
            target: service name (e.g., "database", "app_server", "load_balancer")
            parameters: {"aspect": "logs|metrics|connections|config"}

        - "diagnose": Declare a root cause for an incident
            target: incident_id
            parameters: {"root_cause": "<diagnosis string>"}

        - "prioritize": Assign a priority level to an incident
            target: incident_id
            parameters: {"priority": "P1|P2|P3|P4"}

        - "remediate": Execute a fix action
            target: service name
            parameters: {"action": "<remediation command>"}

        - "escalate": Escalate an incident to a specialist team
            target: incident_id
            parameters: {"team": "<team name>", "reason": "<reason>"}

        - "verify": Check if a remediation was successful
            target: service name
            parameters: {}
    """

    action_type: str = ""
    target: str = ""
    parameters: dict = Field(default_factory=dict)


class IncidentTriageObservation(Observation):
    """
    What the agent observes after each action.

    Contains current alerts, system status, logs, and action feedback.
    """

    # Active alerts
    alerts: list = Field(default_factory=list)
    # Current system health — service -> {status, cpu, memory, error_rate, latency_ms}
    system_status: dict = Field(default_factory=dict)
    # Recent log entries
    logs: list = Field(default_factory=list)
    # Result from the last investigation/action
    investigation_results: str = ""
    # Simulated time elapsed (minutes) since incident start
    time_elapsed: float = 0.0
    # Resolution progress
    incidents_resolved: int = 0
    incidents_remaining: int = 0
    # Error feedback for invalid actions
    last_action_error: Optional[str] = None
    # Task context
    task_name: str = ""
    current_step: int = 0
    max_steps: int = 0


class IncidentTriageState(State):
    """
    Internal state tracking for the environment.

    Tracks task progress, scoring components, and episode metadata.
    """

    task_name: str = ""
    scenario_id: str = ""
    total_incidents: int = 0
    resolved_incidents: int = 0
    misdiagnosed: int = 0
    correct_diagnoses: int = 0
    correct_priorities: int = 0
    wrong_priorities: int = 0
    correct_remediations: int = 0
    failed_remediations: int = 0
    red_herrings_ignored: int = 0
    red_herrings_investigated: int = 0
    time_elapsed: float = 0.0
    actions_taken: int = 0
    accumulated_reward: float = 0.0
    investigations_performed: list = Field(default_factory=list)
    done: bool = False
