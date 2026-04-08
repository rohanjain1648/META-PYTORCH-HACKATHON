"""
Inference Script — Incident Triage Environment
===================================
MANDATORY
- Before submitting, ensure the following variables are defined in your environment configuration:
    API_BASE_URL   The API endpoint for the LLM.
    MODEL_NAME     The model identifier to use for inference.
    HF_TOKEN       Your Hugging Face / API key.
    LOCAL_IMAGE_NAME The name of the local image to use for the environment

- Defaults are set for API_BASE_URL and MODEL_NAME:
    API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")

- The inference script must be named `inference.py` and placed in the root directory

STDOUT FORMAT
- The script emits exactly three line types to stdout:
    [START] task=<task_name> env=<benchmark> model=<model_name>
    [STEP]  step=<n> action=<action_str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<score> rewards=<r1,r2,...,rn>
"""

import json
import os
import sys
import textwrap
import time
import traceback
from typing import Any, List, Optional

import requests
from openai import OpenAI


# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

# From hackathon checklist: Defaults only for API_BASE_URL and MODEL_NAME
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")

# Optional - for local image testing
LOCAL_IMAGE_NAME = os.getenv("LOCAL_IMAGE_NAME")

# Environment configuration
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:8000")
BENCHMARK = "incident_triage_env"

# Tasks to run: easy → medium → hard
TASKS = [
    {"name": "single_incident", "max_steps": 10},
    {"name": "multi_incident", "max_steps": 20},
    {"name": "cascading_failure", "max_steps": 30},
]

TEMPERATURE = 0.3
MAX_TOKENS = 500


# ═══════════════════════════════════════════════════════════════════════════════
# LOGGING — Mandatory stdout format
# ═══════════════════════════════════════════════════════════════════════════════

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    # Truncate action to avoid excessively long lines
    action_short = action[:120].replace("\n", " ") if action else "null"
    print(
        f"[STEP] step={step} action={action_short} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = textwrap.dedent("""
You are an expert on-call DevOps/SRE engineer responding to production incidents.
You interact with an incident triage environment using structured actions.

AVAILABLE ACTIONS (respond with exactly one JSON object per turn):

1. {"action_type": "investigate", "target": "<service_name>", "parameters": {"aspect": "logs|metrics|connections|config"}}
   - Examine a system for more details. Start here to gather information.

2. {"action_type": "diagnose", "target": "<incident_id>", "parameters": {"root_cause": "<your diagnosis>"}}
   - Declare the root cause of an incident after investigation.

3. {"action_type": "prioritize", "target": "<incident_id>", "parameters": {"priority": "P1|P2|P3|P4"}}
   - Assign severity. P1 = critical/outage, P2 = high/degraded, P3 = moderate, P4 = low/cosmetic.

4. {"action_type": "remediate", "target": "<service_name>", "parameters": {"action": "<fix description>"}}
   - Apply a fix to a service (e.g., "restart app server", "kill stale connections", "renew certificate").

5. {"action_type": "escalate", "target": "<incident_id>", "parameters": {"team": "<team_name>", "reason": "<reason>"}}
   - Escalate to a specialist team if you can't resolve it.

6. {"action_type": "verify", "target": "<service_name>", "parameters": {}}
   - Verify that a remediation was successful.

STRATEGY:
- First INVESTIGATE relevant services to gather information
- Then DIAGNOSE the root cause (look for the underlying issue, not just symptoms)
- PRIORITIZE incidents by severity (handle P1 before P2)
- REMEDIATE the root cause (fixing the root cause often resolves cascading symptoms)
- VERIFY the fix worked

For cascading failures: identify the ROOT CAUSE, not just symptoms. Some alerts may be RED HERRINGS.

RESPOND WITH ONLY ONE JSON OBJECT. No explanation, no markdown, just the JSON.
""").strip()


# ═══════════════════════════════════════════════════════════════════════════════
# ENVIRONMENT CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class EnvClient:
    """Simple HTTP client for the incident triage environment."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def reset(self, task_name: str) -> dict:
        resp = requests.post(
            f"{self.base_url}/reset",
            json={"task_name": task_name},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def step(self, action: dict) -> dict:
        resp = requests.post(
            f"{self.base_url}/step",
            json=action,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def state(self) -> dict:
        resp = requests.get(f"{self.base_url}/state", timeout=10)
        resp.raise_for_status()
        return resp.json()

    def grade(self) -> dict:
        resp = requests.get(f"{self.base_url}/grade", timeout=10)
        resp.raise_for_status()
        return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# LLM INTERACTION
# ═══════════════════════════════════════════════════════════════════════════════

def build_user_prompt(observation: dict, step_num: int, history: List[str]) -> str:
    """Build the user prompt from the current observation."""
    obs = observation.get("observation", observation)

    # Format alerts
    alerts_text = ""
    for alert in obs.get("alerts", []):
        alerts_text += (
            f"  [{alert.get('severity', 'unknown').upper()}] {alert.get('id', '?')} — "
            f"{alert.get('service', '?')}: {alert.get('title', '?')}\n"
            f"    {alert.get('message', '')}\n"
        )

    # Format system status (summarized)
    status_summary = ""
    for svc, data in obs.get("system_status", {}).items():
        svc_status = data.get("status", "unknown")
        if svc_status != "healthy":
            status_summary += f"  {svc}: {svc_status} (error_rate={data.get('error_rate', 0)}, latency={data.get('latency_ms', 0)}ms)\n"

    # Investigation results
    inv_results = obs.get("investigation_results", "")

    # Recent history
    history_text = "\n".join(history[-4:]) if history else "None"

    prompt = textwrap.dedent(f"""
STEP {step_num}/{obs.get('max_steps', 10)} | Time elapsed: {obs.get('time_elapsed', 0):.0f} min | Resolved: {obs.get('incidents_resolved', 0)}/{obs.get('incidents_resolved', 0) + obs.get('incidents_remaining', 0)}

ACTIVE ALERTS:
{alerts_text if alerts_text else '  No active alerts'}

DEGRADED SERVICES:
{status_summary if status_summary else '  All services healthy'}

LAST ACTION RESULT:
{inv_results if inv_results else 'No action taken yet'}

RECENT HISTORY:
{history_text}

Respond with exactly one JSON action object.
""").strip()

    return prompt


def get_model_action(client: OpenAI, observation: dict, step_num: int, history: List[str]) -> dict:
    """Get an action from the LLM."""
    user_prompt = build_user_prompt(observation, step_num, history)

    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS,
            stream=False,
        )
        text = (completion.choices[0].message.content or "").strip()

        # Parse JSON from response — handle markdown code blocks
        if "```" in text:
            # Extract JSON from code block
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                text = text[start:end]

        # Try to parse as JSON
        action = json.loads(text)

        # Validate required fields
        if "action_type" not in action:
            action = {"action_type": "investigate", "target": "database_primary", "parameters": {"aspect": "logs"}}

        if "target" not in action:
            action["target"] = ""
        if "parameters" not in action:
            action["parameters"] = {}

        return action

    except json.JSONDecodeError:
        print(f"[DEBUG] Failed to parse LLM response as JSON: {text[:200]}", flush=True)
        return {"action_type": "investigate", "target": "database_primary", "parameters": {"aspect": "logs"}}
    except Exception as exc:
        print(f"[DEBUG] Model request failed: {exc}", flush=True)
        return {"action_type": "investigate", "target": "database_primary", "parameters": {"aspect": "logs"}}


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN INFERENCE LOOP
# ═══════════════════════════════════════════════════════════════════════════════

def run_task(llm_client: OpenAI, env_client: EnvClient, task_config: dict) -> dict:
    """
    Run a single task and return results.

    Returns:
        dict with success, steps, score, rewards
    """
    task_name = task_config["name"]
    max_steps = task_config["max_steps"]

    history: List[str] = []
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task_name, env=BENCHMARK, model=MODEL_NAME)

    try:
        # Reset environment
        result = env_client.reset(task_name)

        for step_num in range(1, max_steps + 1):
            if result.get("done", False):
                break

            # Get action from LLM
            action = get_model_action(llm_client, result, step_num, history)

            # Execute action
            result = env_client.step(action)

            reward = result.get("reward", 0.0)
            done = result.get("done", False)
            error = result.get("observation", {}).get("last_action_error")

            rewards.append(reward)
            steps_taken = step_num

            # Format action string for logging
            action_str = f"{action.get('action_type', '?')}({action.get('target', '?')})"

            log_step(
                step=step_num,
                action=action_str,
                reward=reward,
                done=done,
                error=error,
            )

            # Add to history
            history.append(f"Step {step_num}: {action_str} → reward={reward:+.2f}")

            if done:
                break

        # Get final grade
        try:
            grade = env_client.grade()
            score = grade.get("score", 0.0)
        except Exception:
            # Fall back to accumulated rewards
            score = sum(max(r, 0) for r in rewards) / max(sum(abs(r) for r in rewards), 1.0) if rewards else 0.0

        score = max(0.01, min(0.99, score))
        success = score >= 0.1

    except Exception as e:
        print(f"[DEBUG] Task {task_name} failed: {e}", flush=True)
        traceback.print_exc()

    finally:
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return {
        "task": task_name,
        "success": success,
        "steps": steps_taken,
        "score": score,
        "rewards": rewards,
    }


def main():
    """Run inference on all 3 tasks."""
    print(f"[DEBUG] Starting inference with model={MODEL_NAME}, env={ENV_BASE_URL}", flush=True)

    # Initialize LLM client
    llm_client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    # Initialize environment client
    env_client = EnvClient(ENV_BASE_URL)

    # Verify environment is running
    try:
        health = requests.get(f"{ENV_BASE_URL}/health", timeout=5)
        health.raise_for_status()
        print(f"[DEBUG] Environment health: {health.json()}", flush=True)
    except Exception as e:
        print(f"[DEBUG] Environment not reachable at {ENV_BASE_URL}: {e}", flush=True)
        print(f"[DEBUG] Please start the environment first:", flush=True)
        print(f"[DEBUG]   cd incident_triage_env && uvicorn server.app:app --host 0.0.0.0 --port 8000", flush=True)
        sys.exit(1)

    # Run all 3 tasks
    all_results = []
    for task_config in TASKS:
        print(f"\n{'='*60}", flush=True)
        print(f"[DEBUG] Running task: {task_config['name']}", flush=True)
        print(f"{'='*60}", flush=True)

        result = run_task(llm_client, env_client, task_config)
        all_results.append(result)

        # Brief pause between tasks
        time.sleep(1)

    # Summary
    print(f"\n{'='*60}", flush=True)
    print("[DEBUG] FINAL RESULTS SUMMARY", flush=True)
    print(f"{'='*60}", flush=True)
    for r in all_results:
        status = "✅" if r["success"] else "❌"
        print(
            f"  {status} {r['task']:25s} score={r['score']:.2f} steps={r['steps']}",
            flush=True,
        )

    avg_score = sum(r["score"] for r in all_results) / len(all_results) if all_results else 0.0
    print(f"\n  Average score: {avg_score:.2f}", flush=True)


if __name__ == "__main__":
    main()
