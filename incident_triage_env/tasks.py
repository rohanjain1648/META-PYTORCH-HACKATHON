# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - Tasks & Graders

"""
Task Definitions and Graders.

Defines the 3 required tasks (easy → medium → hard) with programmatic graders
that produce deterministic scores in [0.0, 1.0].
"""

from typing import Any

from .reward import compute_final_score


# ═══════════════════════════════════════════════════════════════════════════════
# TASK DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

TASKS = {
    "single_incident": {
        "name": "single_incident",
        "display_name": "Single Incident Resolution",
        "difficulty": "easy",
        "description": (
            "Resolve a single production incident. The agent receives ONE alert and must: "
            "investigate the affected system, diagnose the root cause, assign correct priority, "
            "apply the right remediation, and verify the fix."
        ),
        "max_steps": 10,
        "expected_steps": 5,
        "default_scenario": "db_connection_pool_exhaustion",
        "scoring_rubric": {
            "correct_diagnosis": 0.30,
            "correct_priority": 0.15,
            "correct_remediation": 0.35,
            "successful_verification": 0.10,
            "efficiency_bonus": 0.10,
        },
    },
    "multi_incident": {
        "name": "multi_incident",
        "display_name": "Multi-Incident Triage",
        "difficulty": "medium",
        "description": (
            "Triage and resolve 2-3 simultaneous incidents. The agent must correctly prioritize "
            "which to fix first (P1 before P2), identify correlated vs independent incidents, "
            "and resolve each appropriately. Some incidents may be symptoms of a shared root cause."
        ),
        "max_steps": 20,
        "expected_steps": 12,
        "default_scenario": "memory_leak_cascade",
        "scoring_rubric": {
            "correct_triage_order": 0.20,
            "correct_diagnoses": 0.25,
            "correct_remediations": 0.30,
            "correlation_identification": 0.15,
            "time_efficiency": 0.10,
        },
    },
    "cascading_failure": {
        "name": "cascading_failure",
        "display_name": "Cascading Failure Resolution",
        "difficulty": "hard",
        "description": (
            "Resolve a cascading failure affecting multiple services. 4+ alerts fire "
            "simultaneously, including RED HERRING alerts that look alarming but are "
            "normal behavior. The agent must identify the true root cause (not just symptoms), "
            "ignore red herrings, fix in the correct order (root cause first), and verify "
            "full system recovery."
        ),
        "max_steps": 30,
        "expected_steps": 20,
        "default_scenario": "full_stack_cascade",
        "scoring_rubric": {
            "root_cause_identification": 0.30,
            "red_herrings_ignored": 0.10,
            "correct_fix_order": 0.20,
            "all_incidents_resolved": 0.25,
            "efficiency": 0.15,
        },
    },
}


def get_task(task_name: str) -> dict:
    """Get task definition by name."""
    if task_name not in TASKS:
        raise ValueError(
            f"Unknown task: {task_name}. Available tasks: {list(TASKS.keys())}"
        )
    return TASKS[task_name]


def list_tasks() -> list[dict]:
    """List all available tasks."""
    return [
        {
            "name": t["name"],
            "display_name": t["display_name"],
            "difficulty": t["difficulty"],
            "description": t["description"],
            "max_steps": t["max_steps"],
        }
        for t in TASKS.values()
    ]


# ═══════════════════════════════════════════════════════════════════════════════
# GRADERS
# ═══════════════════════════════════════════════════════════════════════════════


class TaskGrader:
    """
    Programmatic grader for incident triage tasks.

    Produces deterministic scores in [0.0, 1.0] based on the task-specific rubric.
    """

    def __init__(self, task_name: str):
        self.task_name = task_name
        self.task = get_task(task_name)

    def grade(self, scenario: dict, state: Any) -> dict:
        """
        Grade an episode's performance.

        Args:
            scenario: The scenario that was played
            state: The final environment state

        Returns:
            dict with:
                - score: float in [0.0, 1.0]
                - breakdown: dict of component scores
                - feedback: list of human-readable feedback strings
        """
        score = compute_final_score(scenario, state, self.task_name)
        score = max(0.0, min(1.0, score))  # Clamp to [0, 1]

        breakdown = self._compute_breakdown(scenario, state)
        feedback = self._generate_feedback(scenario, state, breakdown)

        return {
            "score": score,
            "breakdown": breakdown,
            "feedback": feedback,
            "task": self.task_name,
            "difficulty": self.task["difficulty"],
        }

    def _compute_breakdown(self, scenario: dict, state: Any) -> dict:
        """Compute individual scoring components."""
        incidents = scenario.get("incidents", {})
        non_herring = {k: v for k, v in incidents.items() if not v.get("is_red_herring", False)}
        total = max(len(non_herring), 1)
        expected_steps = scenario.get("expected_steps", 10)

        breakdown = {
            "diagnoses_correct": state.correct_diagnoses,
            "diagnoses_total": total,
            "priorities_correct": state.correct_priorities,
            "priorities_total": total,
            "remediations_correct": state.correct_remediations,
            "incidents_resolved": state.resolved_incidents,
            "incidents_total": state.total_incidents,
            "steps_taken": state.actions_taken,
            "steps_expected": expected_steps,
            "misdiagnoses": state.misdiagnosed,
            "red_herrings_investigated": getattr(state, "red_herrings_investigated", 0),
        }
        return breakdown

    def _generate_feedback(self, scenario: dict, state: Any, breakdown: dict) -> list[str]:
        """Generate human-readable feedback."""
        feedback = []

        if breakdown["diagnoses_correct"] == breakdown["diagnoses_total"]:
            feedback.append("✅ All incidents correctly diagnosed")
        elif breakdown["diagnoses_correct"] > 0:
            feedback.append(
                f"⚠️ {breakdown['diagnoses_correct']}/{breakdown['diagnoses_total']} incidents correctly diagnosed"
            )
        else:
            feedback.append("❌ No correct diagnoses")

        if breakdown["remediations_correct"] > 0:
            feedback.append("✅ Correct remediation applied")
        else:
            feedback.append("❌ No correct remediation applied")

        if breakdown["steps_taken"] <= breakdown["steps_expected"]:
            feedback.append(
                f"✅ Efficient: {breakdown['steps_taken']} steps (expected: {breakdown['steps_expected']})"
            )
        else:
            feedback.append(
                f"⚠️ Slow: {breakdown['steps_taken']} steps (expected: {breakdown['steps_expected']})"
            )

        if breakdown["misdiagnoses"] > 0:
            feedback.append(f"❌ {breakdown['misdiagnoses']} misdiagnosis(es)")

        if breakdown["red_herrings_investigated"] > 0:
            feedback.append(
                f"⚠️ Investigated {breakdown['red_herrings_investigated']} red herring(s)"
            )

        return feedback
