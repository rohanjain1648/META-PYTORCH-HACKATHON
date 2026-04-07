# Copyright (c) 2025. All rights reserved.
# Incident Triage Environment - Reward Engine

"""
Reward Computation Engine.

Provides dense, per-step reward signals for the incident triage environment.
Rewards partial progress and penalizes undesirable behavior.

All rewards are designed so that cumulative episode reward maps to [0.0, 1.0].
"""

from typing import Any


# ═══════════════════════════════════════════════════════════════════════════════
# REWARD CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Positive rewards
REWARD_USEFUL_INVESTIGATION = 0.05
REWARD_CORRECT_DIAGNOSIS = 0.15
REWARD_ROOT_CAUSE_IDENTIFIED = 0.20
REWARD_CORRECT_PRIORITY = 0.08
REWARD_CORRECT_REMEDIATION = 0.20
REWARD_SUCCESSFUL_VERIFICATION = 0.10
REWARD_CORRELATION_IDENTIFIED = 0.10
REWARD_RED_HERRING_IGNORED = 0.05
REWARD_EFFICIENCY_BONUS_PER_STEP = 0.02

# Negative penalties
PENALTY_WRONG_DIAGNOSIS = -0.10
PENALTY_WRONG_REMEDIATION = -0.15
PENALTY_REDUNDANT_ACTION = -0.03
PENALTY_WRONG_TRIAGE_ORDER = -0.08
PENALTY_STEP_OVER_EXPECTED = -0.01
PENALTY_INVALID_ACTION = -0.05
PENALTY_RED_HERRING_REMEDIATED = -0.08


def _keyword_match(text: str, keywords: list[str]) -> bool:
    """Check if any keywords appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def compute_investigation_reward(
    action_target: str,
    action_params: dict,
    scenario: dict,
    investigations_performed: list[str],
) -> tuple[float, str]:
    """
    Compute reward for an investigation action.

    Returns:
        (reward, reason)
    """
    investigation_key = f"{action_target}:{action_params.get('aspect', 'general')}"

    # Penalize redundant investigations
    if investigation_key in investigations_performed:
        return PENALTY_REDUNDANT_ACTION, "Redundant investigation - already examined this aspect"

    # Check if the investigation target is relevant to the scenario
    relevant_services = set()
    for alert in scenario.get("initial_alerts", []):
        relevant_services.add(alert["service"])
    for service in scenario.get("investigation_data", {}).keys():
        relevant_services.add(service)

    if action_target in relevant_services:
        return REWARD_USEFUL_INVESTIGATION, "Useful investigation of a relevant system"
    else:
        return 0.0, "Investigation of an unrelated system - no useful information"


def compute_diagnosis_reward(
    incident_id: str,
    diagnosis: str,
    scenario: dict,
) -> tuple[float, str]:
    """
    Compute reward for a diagnosis action.

    Returns:
        (reward, reason)
    """
    incidents = scenario.get("incidents", {})
    if incident_id not in incidents:
        return PENALTY_INVALID_ACTION, f"Unknown incident ID: {incident_id}"

    incident = incidents[incident_id]
    keywords = incident.get("diagnosis_keywords", [])

    if _keyword_match(diagnosis, keywords):
        # Check if this is the root cause identification
        if incident.get("is_root_cause", False):
            return REWARD_ROOT_CAUSE_IDENTIFIED, "Correctly identified the ROOT CAUSE"
        elif incident.get("is_red_herring", False):
            # Correctly identified as red herring
            if any(kw in diagnosis.lower() for kw in ["red herring", "normal", "no action", "expected"]):
                return REWARD_RED_HERRING_IGNORED, "Correctly identified as red herring / normal behavior"
            else:
                return REWARD_CORRECT_DIAGNOSIS * 0.5, "Partially correct diagnosis"
        else:
            return REWARD_CORRECT_DIAGNOSIS, "Correct diagnosis"
    else:
        return PENALTY_WRONG_DIAGNOSIS, "Incorrect diagnosis - does not match expected root cause"


def compute_priority_reward(
    incident_id: str,
    priority: str,
    scenario: dict,
    priorities_assigned: dict,
) -> tuple[float, str]:
    """
    Compute reward for a prioritize action.

    Returns:
        (reward, reason)
    """
    incidents = scenario.get("incidents", {})
    if incident_id not in incidents:
        return PENALTY_INVALID_ACTION, f"Unknown incident ID: {incident_id}"

    incident = incidents[incident_id]
    expected = incident.get("expected_priority", "P3")
    priority = priority.upper().strip()

    if priority == expected:
        return REWARD_CORRECT_PRIORITY, f"Correct priority assignment: {priority}"
    elif abs(int(priority[1]) - int(expected[1])) == 1:
        # Off by one - partial credit
        return REWARD_CORRECT_PRIORITY * 0.4, f"Priority {priority} is close but expected {expected}"
    else:
        return -0.05, f"Wrong priority: assigned {priority}, expected {expected}"


def compute_remediation_reward(
    target: str,
    action_params: dict,
    scenario: dict,
    diagnoses_made: dict,
) -> tuple[float, str]:
    """
    Compute reward for a remediation action.

    Returns:
        (reward, reason)
    """
    remediation_desc = action_params.get("action", "")

    # Find which incident this remediation targets
    matched_incident = None
    for inc_id, inc_data in scenario.get("incidents", {}).items():
        if inc_data.get("is_root_cause", False):
            matched_incident = (inc_id, inc_data)
            break

    if not matched_incident:
        # Try to match by service name
        for inc_id, inc_data in scenario.get("incidents", {}).items():
            for alert in scenario.get("initial_alerts", []):
                if alert["id"] == inc_id and alert["service"] == target:
                    matched_incident = (inc_id, inc_data)
                    break

    if matched_incident:
        inc_id, inc_data = matched_incident
        keywords = inc_data.get("remediation_keywords", [])

        if inc_data.get("is_red_herring", False):
            return PENALTY_RED_HERRING_REMEDIATED, "Attempted to remediate a red herring - wasted effort"

        if _keyword_match(remediation_desc, keywords):
            return REWARD_CORRECT_REMEDIATION, "Correct remediation applied"
        else:
            return PENALTY_WRONG_REMEDIATION, f"Incorrect remediation: {remediation_desc}"
    else:
        return PENALTY_INVALID_ACTION, f"Remediation target '{target}' not associated with any known incident"


def compute_verification_reward(
    target: str,
    scenario: dict,
    remediations_applied: list[str],
) -> tuple[float, str]:
    """
    Compute reward for a verification action.

    Returns:
        (reward, reason)
    """
    if not remediations_applied:
        return -0.02, "Verification attempted before any remediation was applied"

    # Check if we remediated anything related to this target
    target_remediated = any(target.lower() in r.lower() for r in remediations_applied)

    if target_remediated:
        return REWARD_SUCCESSFUL_VERIFICATION, "Verification successful - fix confirmed"
    else:
        return 0.0, "Verification target was not remediated"


def compute_escalation_reward(
    incident_id: str,
    scenario: dict,
) -> tuple[float, str]:
    """
    Compute reward for an escalation action.

    We give a small positive reward for escalation — it's not wrong, but
    the agent should try to handle it themselves first.

    Returns:
        (reward, reason)
    """
    return 0.02, "Escalated to specialist team"


def compute_efficiency_bonus(
    steps_taken: int,
    expected_steps: int,
) -> float:
    """
    Compute efficiency bonus/penalty based on steps taken vs expected.

    Returns:
        Bonus reward (positive if faster, negative if slower)
    """
    if steps_taken <= expected_steps:
        return (expected_steps - steps_taken) * REWARD_EFFICIENCY_BONUS_PER_STEP
    else:
        return (expected_steps - steps_taken) * abs(PENALTY_STEP_OVER_EXPECTED)


def compute_final_score(
    scenario: dict,
    state: Any,
    task_name: str,
) -> float:
    """
    Compute the final episode score (0.0 to 1.0) based on task-specific grading rubric.

    This is the score reported to the hackathon evaluator.
    """
    incidents = scenario.get("incidents", {})
    total_incidents = len([i for i in incidents.values() if not i.get("is_red_herring", False)])

    if task_name == "single_incident":
        return _grade_single_incident(scenario, state)
    elif task_name == "multi_incident":
        return _grade_multi_incident(scenario, state)
    elif task_name == "cascading_failure":
        return _grade_cascading_failure(scenario, state)
    else:
        return 0.0


def _grade_single_incident(scenario: dict, state: Any) -> float:
    """
    Grade Task 1: Single Incident Resolution

    - Correct diagnosis:     +0.30
    - Correct priority:      +0.15
    - Correct remediation:   +0.35
    - Successful verify:     +0.10
    - Efficiency bonus:      +0.10
    """
    score = 0.0
    max_score = 1.0
    expected_steps = scenario.get("expected_steps", 5)

    # Diagnosis (0.30)
    if state.correct_diagnoses > 0:
        score += 0.30

    # Priority (0.15)
    if state.correct_priorities > 0:
        score += 0.15

    # Remediation (0.35)
    if state.correct_remediations > 0:
        score += 0.35

    # Verification (0.10)
    if state.resolved_incidents > 0:
        score += 0.10

    # Efficiency (0.10)
    if state.actions_taken <= expected_steps:
        score += 0.10
    elif state.actions_taken <= expected_steps * 1.5:
        score += 0.05

    return min(score, max_score)


def _grade_multi_incident(scenario: dict, state: Any) -> float:
    """
    Grade Task 2: Multi-Incident Triage

    - Correct triage order:    +0.20
    - Correct diagnoses:       +0.25
    - Correct remediations:    +0.30
    - Correlation found:       +0.15
    - Time efficiency:         +0.10
    """
    score = 0.0
    incidents = scenario.get("incidents", {})
    non_herring = {k: v for k, v in incidents.items() if not v.get("is_red_herring", False)}
    total = max(len(non_herring), 1)
    expected_steps = scenario.get("expected_steps", 12)

    # Triage order (0.20) — did they handle P1 before P2?
    if state.correct_priorities >= total:
        score += 0.20
    elif state.correct_priorities > 0:
        score += 0.10 * (state.correct_priorities / total)

    # Diagnoses (0.25)
    diagnosis_ratio = min(state.correct_diagnoses / total, 1.0)
    score += 0.25 * diagnosis_ratio

    # Remediations (0.30)
    # Only root cause needs remediation in correlated alerts
    root_causes = [k for k, v in non_herring.items() if v.get("is_root_cause", True)]
    if state.correct_remediations >= len(root_causes):
        score += 0.30
    elif state.correct_remediations > 0:
        score += 0.15

    # Correlation (0.15)
    if hasattr(state, "correlations_identified") and state.correlations_identified > 0:
        score += 0.15
    elif state.correct_diagnoses >= 2:
        # Partial: if they diagnosed multiple correctly, they likely understood correlation
        score += 0.08

    # Efficiency (0.10)
    if state.actions_taken <= expected_steps:
        score += 0.10
    elif state.actions_taken <= expected_steps * 1.5:
        score += 0.05

    return min(score, 1.0)


def _grade_cascading_failure(scenario: dict, state: Any) -> float:
    """
    Grade Task 3: Cascading Failure Resolution

    - Root cause identified:       +0.30
    - Red herrings ignored:        +0.10
    - Correct fix order:           +0.20
    - All incidents resolved:      +0.25
    - Efficiency:                  +0.15
    """
    score = 0.0
    incidents = scenario.get("incidents", {})
    non_herring = {k: v for k, v in incidents.items() if not v.get("is_red_herring", False)}
    red_herrings = {k: v for k, v in incidents.items() if v.get("is_red_herring", False)}
    expected_steps = scenario.get("expected_steps", 20)

    # Root cause (0.30)
    root_found = False
    for inc_id, inc_data in incidents.items():
        if inc_data.get("is_root_cause", False):
            if state.correct_diagnoses > 0:
                score += 0.30
                root_found = True
            break

    # Red herrings ignored (0.10)
    if len(red_herrings) > 0:
        if state.red_herrings_investigated == 0:
            score += 0.10
        elif state.red_herrings_investigated < len(red_herrings):
            score += 0.05

    # Correct fix order (0.20) — root cause fixed before trying to fix symptoms
    if state.correct_remediations > 0 and root_found:
        score += 0.20
    elif state.correct_remediations > 0:
        score += 0.10

    # All resolved (0.25)
    total_resolvable = len(non_herring)
    if state.resolved_incidents >= total_resolvable:
        score += 0.25
    elif state.resolved_incidents > 0:
        score += 0.12 * (state.resolved_incidents / max(total_resolvable, 1))

    # Efficiency (0.15)
    if state.actions_taken <= expected_steps:
        score += 0.15
    elif state.actions_taken <= expected_steps * 1.5:
        score += 0.08
    elif state.actions_taken <= expected_steps * 2:
        score += 0.03

    return min(score, 1.0)
