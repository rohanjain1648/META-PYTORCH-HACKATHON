# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - Core Environment Implementation

"""
Incident Triage Environment.

Core environment implementation for the incident response triage simulator.
Implements the OpenEnv Environment interface: reset(), step(), state.
"""

import copy
import json
from typing import Any, Optional
from uuid import uuid4

from openenv.core.env_server.types import Action, Observation, State

from ..models import IncidentTriageAction, IncidentTriageObservation, IncidentTriageState
from ..scenarios import get_scenario_for_task, get_initial_system_status, HEALTHY_SERVICES
from ..tasks import get_task, TASKS, TaskGrader
from ..reward import (
    compute_investigation_reward,
    compute_diagnosis_reward,
    compute_priority_reward,
    compute_remediation_reward,
    compute_verification_reward,
    compute_escalation_reward,
    compute_efficiency_bonus,
    PENALTY_INVALID_ACTION,
)


VALID_ACTION_TYPES = {
    "investigate", "diagnose", "prioritize",
    "remediate", "escalate", "verify",
}

TIME_PER_STEP = 2.0  # Simulated minutes per step


class IncidentTriageEnvironment:
    """
    Incident Response Triage Environment.

    Simulates a real-world on-call incident management scenario where an AI agent
    must diagnose, prioritize, and resolve production incidents.

    Supports 3 tasks:
        - single_incident (easy): One alert, straightforward diagnosis and fix
        - multi_incident (medium): 2-3 concurrent alerts, correlations
        - cascading_failure (hard): 4+ alerts, red herrings, cascading failures

    Environment API:
        - reset(task_name, seed): Start a new episode for the given task
        - step(action): Execute an action and return observation + reward
        - state: Get current episode state
    """

    def __init__(self):
        """Initialize the environment."""
        self._state = IncidentTriageState(episode_id=str(uuid4()), step_count=0)
        self._scenario = None
        self._task = None
        self._grader = None
        self._system_status = copy.deepcopy(HEALTHY_SERVICES)
        self._active_alerts = []
        self._diagnoses_made = {}
        self._priorities_assigned = {}
        self._remediations_applied = []
        self._resolved_incidents = set()
        self._investigations_performed = []
        self._done = False
        self._last_reward = 0.0

    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        task_name: str = "single_incident",
        **kwargs: Any,
    ) -> Observation:
        """
        Reset the environment for a new episode.

        Args:
            seed: Random seed for scenario selection (default: None for deterministic first scenario)
            episode_id: Optional episode ID
            task_name: One of "single_incident", "multi_incident", "cascading_failure"

        Returns:
            Initial observation with alerts and system status
        """
        # Load task and scenario
        self._task = get_task(task_name)
        self._scenario = get_scenario_for_task(task_name, seed)
        self._grader = TaskGrader(task_name)

        # Initialize state
        non_herring_count = len([
            inc for inc in self._scenario.get("incidents", {}).values()
            if not inc.get("is_red_herring", False)
        ])

        self._state = IncidentTriageState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            task_name=task_name,
            scenario_id=self._scenario["id"],
            total_incidents=non_herring_count,
            resolved_incidents=0,
            misdiagnosed=0,
            correct_diagnoses=0,
            correct_priorities=0,
            wrong_priorities=0,
            correct_remediations=0,
            failed_remediations=0,
            red_herrings_ignored=0,
            red_herrings_investigated=0,
            time_elapsed=0.0,
            actions_taken=0,
            accumulated_reward=0.0,
            investigations_performed=[],
            done=False,
        )

        # Initialize system and alerts
        self._system_status = get_initial_system_status(self._scenario)
        self._active_alerts = copy.deepcopy(self._scenario.get("initial_alerts", []))
        self._diagnoses_made = {}
        self._priorities_assigned = {}
        self._remediations_applied = []
        self._resolved_incidents = set()
        self._investigations_performed = []
        self._done = False
        self._last_reward = 0.0

        # Build initial observation
        return self._build_observation(
            investigation_results=(
                f"INCIDENT RESPONSE ACTIVATED — Task: {self._task['display_name']} ({self._task['difficulty'].upper()})\n"
                f"You are the on-call engineer. {len(self._active_alerts)} alert(s) firing.\n"
                f"Available actions: investigate, diagnose, prioritize, remediate, escalate, verify.\n"
                f"Maximum steps: {self._task['max_steps']}. Resolve all incidents."
            ),
            last_action_error=None,
        )

    def step(
        self,
        action: Any,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> Observation:
        """
        Execute an action in the environment.

        Args:
            action: IncidentTriageAction or dict with action_type, target, parameters

        Returns:
            Observation with updated state, reward, and done flag
        """
        if self._done:
            return self._build_observation(
                investigation_results="Episode is already complete. Call reset() to start a new episode.",
                last_action_error="Episode already done",
            )

        # Parse action
        if isinstance(action, dict):
            action_type = action.get("action_type", "")
            target = action.get("target", "")
            parameters = action.get("parameters", {})
        elif hasattr(action, "action_type"):
            action_type = action.action_type
            target = action.target
            parameters = action.parameters if action.parameters else {}
        else:
            return self._build_observation(
                investigation_results="Invalid action format. Expected {action_type, target, parameters}.",
                last_action_error="Invalid action format",
            )

        # Validate action type
        if action_type not in VALID_ACTION_TYPES:
            self._state.step_count += 1
            self._state.actions_taken += 1
            self._state.time_elapsed += TIME_PER_STEP
            reward = PENALTY_INVALID_ACTION
            self._state.accumulated_reward += reward
            self._last_reward = reward

            return self._build_observation(
                investigation_results=(
                    f"Invalid action type: '{action_type}'. "
                    f"Valid actions: {', '.join(sorted(VALID_ACTION_TYPES))}"
                ),
                last_action_error=f"Invalid action type: {action_type}",
                reward=reward,
            )

        # Increment step
        self._state.step_count += 1
        self._state.actions_taken += 1
        self._state.time_elapsed += TIME_PER_STEP

        # Dispatch action
        reward = 0.0
        investigation_results = ""
        error = None

        if action_type == "investigate":
            reward, investigation_results, error = self._handle_investigate(target, parameters)
        elif action_type == "diagnose":
            reward, investigation_results, error = self._handle_diagnose(target, parameters)
        elif action_type == "prioritize":
            reward, investigation_results, error = self._handle_prioritize(target, parameters)
        elif action_type == "remediate":
            reward, investigation_results, error = self._handle_remediate(target, parameters)
        elif action_type == "escalate":
            reward, investigation_results, error = self._handle_escalate(target, parameters)
        elif action_type == "verify":
            reward, investigation_results, error = self._handle_verify(target, parameters)

        # Update reward
        self._state.accumulated_reward += reward
        self._last_reward = reward

        # Check if done
        max_steps = self._task.get("max_steps", 10)
        all_resolved = self._state.resolved_incidents >= self._state.total_incidents

        if all_resolved or self._state.actions_taken >= max_steps:
            self._done = True
            self._state.done = True

            # Add efficiency bonus/penalty
            efficiency = compute_efficiency_bonus(
                self._state.actions_taken,
                self._scenario.get("expected_steps", max_steps),
            )
            self._state.accumulated_reward += efficiency

            # Compute final grade
            grade_result = self._grader.grade(self._scenario, self._state)

            if all_resolved:
                investigation_results += f"\n\n🎉 ALL INCIDENTS RESOLVED! Final score: {grade_result['score']:.2f}"
            else:
                investigation_results += f"\n\n⏰ MAX STEPS REACHED. Final score: {grade_result['score']:.2f}"

            investigation_results += "\n" + "\n".join(grade_result["feedback"])

        return self._build_observation(
            investigation_results=investigation_results,
            last_action_error=error,
            reward=reward,
        )

    @property
    def state(self) -> IncidentTriageState:
        """Get current environment state."""
        return self._state

    # ═══════════════════════════════════════════════════════════════════════════
    # ACTION HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _handle_investigate(self, target: str, params: dict) -> tuple[float, str, Optional[str]]:
        """Handle investigation action."""
        aspect = params.get("aspect", "logs")
        investigation_key = f"{target}:{aspect}"

        # Compute reward
        reward, reason = compute_investigation_reward(
            target, params, self._scenario, self._investigations_performed
        )

        # Record investigation
        self._investigations_performed.append(investigation_key)
        self._state.investigations_performed.append(investigation_key)

        # Check if investigating a red herring
        for alert in self._active_alerts:
            if alert["service"] == target and alert.get("is_red_herring", False):
                self._state.red_herrings_investigated += 1

        # Get investigation data
        inv_data = self._scenario.get("investigation_data", {}).get(target, {})

        if not inv_data:
            return reward, f"No data available for service '{target}'. Service not found in incident scope.", None

        result_text = f"=== Investigation: {target} ({aspect}) ===\n"

        if aspect == "logs" and "logs" in inv_data:
            result_text += "Recent Logs:\n"
            for log_line in inv_data["logs"]:
                result_text += f"  {log_line}\n"
        elif aspect == "metrics" and "metrics" in inv_data:
            result_text += f"Metrics: {inv_data['metrics']}\n"
        elif aspect == "connections" and "connections" in inv_data:
            result_text += f"Connections: {inv_data['connections']}\n"
        elif aspect == "config" and "config" in inv_data:
            result_text += f"Configuration: {inv_data['config']}\n"
        else:
            # Return all available data for the service
            result_text += "Available data:\n"
            for key, value in inv_data.items():
                if isinstance(value, list):
                    result_text += f"\n{key.upper()}:\n"
                    for item in value:
                        result_text += f"  {item}\n"
                else:
                    result_text += f"{key}: {value}\n"

        result_text += f"\n({reason})"
        return reward, result_text, None

    def _handle_diagnose(self, target: str, params: dict) -> tuple[float, str, Optional[str]]:
        """Handle diagnosis action."""
        root_cause = params.get("root_cause", "")

        if not root_cause:
            return PENALTY_INVALID_ACTION, "Diagnosis requires 'root_cause' in parameters.", "Missing root_cause parameter"

        # Find the incident
        incident_id = target
        if incident_id not in self._scenario.get("incidents", {}):
            # Try to match by alert ID
            for alert in self._active_alerts:
                if alert["service"] == target or alert["id"] == target:
                    incident_id = alert["id"]
                    break

        reward, reason = compute_diagnosis_reward(incident_id, root_cause, self._scenario)

        if reward > 0:
            self._state.correct_diagnoses += 1
            self._diagnoses_made[incident_id] = {"diagnosis": root_cause, "correct": True}
        else:
            self._state.misdiagnosed += 1
            self._diagnoses_made[incident_id] = {"diagnosis": root_cause, "correct": False}

        result_text = f"Diagnosis for {incident_id}: {root_cause}\nResult: {reason}"
        return reward, result_text, None

    def _handle_prioritize(self, target: str, params: dict) -> tuple[float, str, Optional[str]]:
        """Handle prioritize action."""
        priority = params.get("priority", "")

        if not priority or priority.upper() not in ("P1", "P2", "P3", "P4"):
            return PENALTY_INVALID_ACTION, "Priority must be P1, P2, P3, or P4.", "Invalid priority value"

        incident_id = target
        if incident_id not in self._scenario.get("incidents", {}):
            for alert in self._active_alerts:
                if alert["service"] == target or alert["id"] == target:
                    incident_id = alert["id"]
                    break

        reward, reason = compute_priority_reward(
            incident_id, priority, self._scenario, self._priorities_assigned
        )

        if reward > 0:
            self._state.correct_priorities += 1
        else:
            self._state.wrong_priorities += 1

        self._priorities_assigned[incident_id] = priority.upper()

        result_text = f"Priority for {incident_id}: {priority.upper()}\nResult: {reason}"
        return reward, result_text, None

    def _handle_remediate(self, target: str, params: dict) -> tuple[float, str, Optional[str]]:
        """Handle remediation action."""
        action_desc = params.get("action", "")

        if not action_desc:
            return PENALTY_INVALID_ACTION, "Remediation requires 'action' in parameters.", "Missing action parameter"

        reward, reason = compute_remediation_reward(
            target, params, self._scenario, self._diagnoses_made
        )

        remediation_key = f"{target}:{action_desc}"
        self._remediations_applied.append(remediation_key)

        if reward > 0:
            self._state.correct_remediations += 1

            # Apply post-remediation status
            post_status = self._scenario.get("post_remediation_status", {})
            for service, new_status in post_status.items():
                if service in self._system_status:
                    self._system_status[service].update(new_status)

            # Mark incidents as resolved
            incidents = self._scenario.get("incidents", {})
            for inc_id, inc_data in incidents.items():
                if inc_data.get("is_root_cause", False) and not inc_data.get("is_red_herring", False):
                    self._resolved_incidents.add(inc_id)
                    # Also resolve cascading incidents
                    for other_id, other_data in incidents.items():
                        if other_data.get("resolves_with") == inc_id:
                            self._resolved_incidents.add(other_id)

            # Update resolved count
            non_herring_resolved = len([
                inc_id for inc_id in self._resolved_incidents
                if not incidents.get(inc_id, {}).get("is_red_herring", False)
            ])
            self._state.resolved_incidents = non_herring_resolved

            # Update alerts
            for alert in self._active_alerts:
                if alert["id"] in self._resolved_incidents:
                    alert["severity"] = "resolved"
                    alert["message"] = "[RESOLVED] " + alert["message"]

            result_text = f"✅ Remediation applied to {target}: {action_desc}\nResult: {reason}"
        else:
            self._state.failed_remediations += 1
            result_text = f"❌ Remediation attempted on {target}: {action_desc}\nResult: {reason}"

        return reward, result_text, None

    def _handle_escalate(self, target: str, params: dict) -> tuple[float, str, Optional[str]]:
        """Handle escalation action."""
        team = params.get("team", "unknown")
        reason_text = params.get("reason", "no reason provided")

        reward, reason = compute_escalation_reward(target, self._scenario)

        result_text = f"Escalated {target} to team '{team}': {reason_text}\nResult: {reason}"
        return reward, result_text, None

    def _handle_verify(self, target: str, params: dict) -> tuple[float, str, Optional[str]]:
        """Handle verification action."""
        reward, reason = compute_verification_reward(
            target, self._scenario, self._remediations_applied
        )

        # Show current system status for the verified service
        service_status = self._system_status.get(target, {})
        status_str = json.dumps(service_status, indent=2) if service_status else "Service not found"

        result_text = f"Verification of {target}:\n{reason}\n\nCurrent status:\n{status_str}"
        return reward, result_text, None

    # ═══════════════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════════════

    def _build_observation(
        self,
        investigation_results: str = "",
        last_action_error: Optional[str] = None,
        reward: float = 0.0,
    ) -> Observation:
        """Build an observation object."""
        max_steps = self._task.get("max_steps", 10) if self._task else 10

        obs = Observation(
            done=self._done,
            reward=reward,
            metadata={
                "alerts": self._active_alerts,
                "system_status": self._system_status,
                "logs": [],
                "investigation_results": investigation_results,
                "time_elapsed": self._state.time_elapsed,
                "incidents_resolved": self._state.resolved_incidents,
                "incidents_remaining": self._state.total_incidents - self._state.resolved_incidents,
                "last_action_error": last_action_error,
                "task_name": self._state.task_name,
                "current_step": self._state.actions_taken,
                "max_steps": max_steps,
            },
        )

        return obs

    def get_grade(self) -> dict:
        """Get the final grade for the current episode."""
        if self._grader and self._scenario:
            return self._grader.grade(self._scenario, self._state)
        return {"score": 0.0, "breakdown": {}, "feedback": ["No episode completed"]}
