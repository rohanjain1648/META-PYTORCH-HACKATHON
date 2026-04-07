# 🚨 Incident Triage Environment

> An OpenEnv-compliant environment simulating **real-world IT/DevOps incident response triage** — where an AI agent acts as an on-call engineer handling production incidents.

[![OpenEnv](https://img.shields.io/badge/OpenEnv-compatible-blue)](https://github.com/meta-pytorch/OpenEnv)
[![HF Space](https://img.shields.io/badge/🤗-HuggingFace%20Space-yellow)](https://huggingface.co/spaces/rohanjain1648/incident-triage-env)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-green)](https://www.python.org)

---

## 📋 Environment Description

**Incident Response Triage** simulates the work that **on-call engineers at every tech company do daily**: monitoring production alerts, diagnosing root causes, prioritizing incidents by severity, and applying fixes before outages escalate.

The environment presents the agent with realistic production alerts, system metrics, application logs, and configuration data. The agent must navigate through investigation → diagnosis → prioritization → remediation → verification to resolve incidents.

### Why This Domain?

- **Genuine real-world task**: Millions of engineers perform incident response daily
- **Rich decision-making**: Multiple valid investigation paths, priority trade-offs, cascading failures
- **Partial-credit scenarios**: Correct diagnosis but wrong fix, correct priority but slow
- **Meaningful difficulty progression**: From single alert to cascading multi-service failures

---

## 🎯 Action Space

The agent has **6 action types** to interact with the environment:

| Action Type | Target | Parameters | Description |
|---|---|---|---|
| `investigate` | Service name | `{"aspect": "logs\|metrics\|connections\|config"}` | Examine a system for detailed information |
| `diagnose` | Incident ID | `{"root_cause": "<diagnosis>"}` | Declare the root cause of an incident |
| `prioritize` | Incident ID | `{"priority": "P1\|P2\|P3\|P4"}` | Assign severity level |
| `remediate` | Service name | `{"action": "<fix description>"}` | Apply a fix to a service |
| `escalate` | Incident ID | `{"team": "<team>", "reason": "<why>"}` | Escalate to specialist team |
| `verify` | Service name | `{}` | Verify that a fix was successful |

### Action JSON Format

```json
{
  "action_type": "investigate",
  "target": "database_primary",
  "parameters": {"aspect": "logs"}
}
```

---

## 👁️ Observation Space

After each action, the agent receives:

| Field | Type | Description |
|---|---|---|
| `alerts` | `list[dict]` | Active alerts with severity, service, title, message |
| `system_status` | `dict` | Service health metrics (CPU, memory, error rate, latency) |
| `investigation_results` | `str` | Detailed output from the last action |
| `time_elapsed` | `float` | Simulated minutes since incident start |
| `incidents_resolved` | `int` | Number of incidents fixed |
| `incidents_remaining` | `int` | Number still active |
| `last_action_error` | `str\|null` | Error feedback for invalid actions |
| `current_step` | `int` | Current step number |
| `max_steps` | `int` | Maximum steps for this task |

---

## 📊 Tasks & Difficulty Levels

### Task 1: `single_incident` (🟢 Easy)

**Resolve a single production incident.**

The agent receives ONE alert and must: investigate → diagnose → prioritize → remediate → verify.

| Component | Weight |
|---|---|
| Correct diagnosis | 30% |
| Correct priority | 15% |
| Correct remediation | 35% |
| Successful verification | 10% |
| Efficiency (fewer steps) | 10% |

**Max steps:** 10 | **Expected:** 5–6 steps

**Scenarios:** Database connection pool exhaustion, disk space critical, SSL certificate expired

---

### Task 2: `multi_incident` (🟡 Medium)

**Triage 2–3 simultaneous incidents with correlations.**

The agent must identify which alerts are independent vs. symptoms of a shared root cause, prioritize correctly, and fix efficiently.

| Component | Weight |
|---|---|
| Correct triage order | 20% |
| Correct diagnoses | 25% |
| Correct remediations | 30% |
| Correlation identification | 15% |
| Time efficiency | 10% |

**Max steps:** 20 | **Expected:** 12–14 steps

**Scenarios:** Memory leak causing cascading timeouts, DNS misconfiguration breaking deployments

---

### Task 3: `cascading_failure` (🔴 Hard)

**Resolve a cascading failure with 4+ alerts and red herrings.**

A database migration has locked a critical table, causing a full-stack cascade. The agent must identify the ROOT CAUSE (not just symptoms), ignore red herring alerts, and fix in the correct order.

| Component | Weight |
|---|---|
| Root cause identification | 30% |
| Red herrings ignored | 10% |
| Correct fix order | 20% |
| All incidents resolved | 25% |
| Efficiency | 15% |

**Max steps:** 30 | **Expected:** 18–22 steps

**Scenarios:** Full stack cascade from database migration (load balancer → app servers → database → cache → message queue, with cache eviction as red herring)

---

## 🏆 Reward Function

The environment provides **dense, per-step reward signals** (not just sparse end-of-episode):

### Positive Rewards
| Action | Reward |
|---|---|
| Useful investigation | +0.05 |
| Correct diagnosis | +0.15 |
| Root cause identified | +0.20 |
| Correct priority | +0.08 |
| Correct remediation | +0.20 |
| Successful verification | +0.10 |
| Red herring correctly ignored | +0.05 |
| Efficiency bonus (per step saved) | +0.02 |

### Penalties
| Behavior | Penalty |
|---|---|
| Wrong diagnosis | -0.10 |
| Wrong remediation (destructive) | -0.15 |
| Redundant investigation | -0.03 |
| Wrong triage order (P2 before P1) | -0.08 |
| Each step over expected | -0.01 |
| Invalid action | -0.05 |

---

## 🚀 Setup & Usage

### Prerequisites

- Python 3.10+
- Docker (for containerized deployment)

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/rohanjain1648/META-PYTORCH-HACKATHON.git
cd META-PYTORCH-HACKATHON

# 2. Install dependencies
pip install -e ./incident_triage_env

# 3. Start the environment server
cd incident_triage_env
uvicorn server.app:app --host 0.0.0.0 --port 8000

# 4. In another terminal, test it
curl -X POST http://localhost:8000/reset -H "Content-Type: application/json" -d '{"task_name": "single_incident"}'
curl -X POST http://localhost:8000/step -H "Content-Type: application/json" -d '{"action_type": "investigate", "target": "database_primary", "parameters": {"aspect": "logs"}}'
```

### Docker

```bash
# Build
docker build -t incident-triage-env .

# Run
docker run -p 8000:8000 incident-triage-env

# Test
curl http://localhost:8000/health
```

### Run Inference

```bash
# Set environment variables
export HF_TOKEN="your-hf-token"
export API_BASE_URL="https://router.huggingface.co/v1"
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"
export ENV_BASE_URL="http://localhost:8000"

# Run baseline inference on all 3 tasks
python inference.py
```

---

## 📈 Baseline Scores

Baseline performance using `Qwen/Qwen2.5-72B-Instruct`:

| Task | Difficulty | Score | Steps |
|---|---|---|---|
| `single_incident` | 🟢 Easy | ~0.75 | 6 |
| `multi_incident` | 🟡 Medium | ~0.50 | 15 |
| `cascading_failure` | 🔴 Hard | ~0.30 | 25 |

*Scores may vary based on model temperature and API latency.*

---

## 📁 Project Structure

```
META-PYTORCH-HACKATHON/
├── inference.py                          # Baseline inference script (root)
├── Dockerfile                            # Container definition (root)
└── incident_triage_env/
    ├── __init__.py                       # Package exports
    ├── models.py                         # Action, Observation, State models
    ├── client.py                         # HTTP client
    ├── scenarios.py                      # Incident scenario data
    ├── reward.py                         # Reward computation engine
    ├── tasks.py                          # Task definitions + graders
    ├── openenv.yaml                      # OpenEnv manifest
    ├── pyproject.toml                    # Dependencies
    └── server/
        ├── __init__.py
        ├── incident_environment.py       # Core environment logic
        ├── app.py                        # FastAPI application
        └── Dockerfile                    # Standalone container
```

---

## 🔧 API Reference

### `POST /reset`
Reset the environment for a new episode.
```json
{"task_name": "single_incident", "seed": 42}
```

### `POST /step`
Execute one action.
```json
{"action_type": "investigate", "target": "database_primary", "parameters": {"aspect": "logs"}}
```

### `GET /state`
Get current episode state.

### `GET /health`
Health check endpoint.

### `GET /tasks`
List available tasks.

### `GET /grade`
Get the final grade for the current episode.

---

## 🏗️ Architecture

```
┌──────────────────────────┐
│     Agent / LLM          │
│  (OpenAI API Client)     │
└──────────┬───────────────┘
           │ HTTP (POST /step, /reset)
           ▼
┌──────────────────────────┐
│   FastAPI Server         │
│   (app.py)               │
│   ├── /reset             │
│   ├── /step              │
│   ├── /state             │
│   └── /health            │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│  IncidentTriageEnv       │
│  (incident_environment)  │
│  ├── Scenarios           │
│  ├── Reward Engine       │
│  └── Task Graders        │
└──────────────────────────┘
```

---

## 📄 License

MIT License
