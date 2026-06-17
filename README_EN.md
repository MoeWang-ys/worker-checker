# Orchestrator

**AI quality assurance through separation of duties.** Production Agent executes → Check Agent scores blind → Code judges. No AI model gets to be both player and referee.

[中文](README.md)

---

## Architecture

```
You (User) ──→ Orch (Claude) ──→ loop.py (background engine)
                                       │
                          ┌────────────┼────────────┐
                          ▼            ▼            ▼
                   Production Wkr  Check Wkr    judge.py
                   (claude -p)     (claude -p)   (pure code)
                          │            │            │
                     task.json   checklist.json  criteria.json
                          │            │            │
                          └──── output ──→ score ──→ PASS/FAIL
```

| Role | Who | What | Knows |
|------|-----|------|-------|
| Orch | Main Claude | Understands, decomposes, schedules, reports | Everything |
| loop.py | Python script | Starts Workers, runs loop, writes audit trail | All artifacts |
| Production Worker | `claude -p` subprocess | Executes task, produces output | Only task.json |
| Check Worker | `claude -p` subprocess | Reviews, scores each item | Only checklist.json + output |
| judge.py | Python script | Compares criteria vs scores | criteria.json + check result |

## Core Rules

| # | Rule |
|---|------|
| 0 | **Only code decides pass/fail** — judge.py is the sole gatekeeper |
| 1 | **Production & Check Workers fully isolated** — separate `claude -p` processes |
| 2 | **Production Worker never sees criteria** — only gets task.json |
| 3 | **Check Worker never sees criteria** — only gets checklist.json |
| 4 | **Criteria only appear in judge.py input** — never passes through a model |
| 5 | **Human final approval is mandatory** — judge.py PASS ≠ delivered |

## Quick Start

### 1. Decompose the requirement

Create a config.json with three sections:

```json
{
  "task": {
    "description": "What to do. No acceptance criteria here.",
    "output_format": { "schema": {} }
  },
  "checklist": {
    "items": [
      { "id": "correctness", "dimension": "Correctness", "check": "Verify logic", "scoring": {"type": "score", "max": 10} }
    ]
  },
  "criteria": {
    "pass_conditions": [
      { "id": "min_score", "type": "threshold", "source": "results[0].score", "operator": ">=", "value": 8 }
    ],
    "logic": "all",
    "max_rounds": 3
  }
}
```

### 2. Launch

```bash
python3 scripts/loop.py --config examples/sample-config.json
```

loop.py runs in background. Orch stays interactive — chat freely, check progress anytime.

### 3. Check progress

```bash
python3 scripts/status.py                          # Phase snapshot
tail -f run_output/<ts>/round_1/production_live.log  # Live Worker output
```

Or launch an Agent Monitor (enabled by default):

```
Agent: "Check progress.json + *_live.log every 20s. Report any changes."
```

### 4. Human final review

When `FINAL_PASS.json` appears, Orch presents results. User confirms → delivered.

## Checklist Design Principle

> Minimize subjective judgment. Every scoring dimension should be quantifiable. When subjective judgment is unavoidable, provide clear, specific descriptions.

| ❌ Bad | ✅ Good |
|--------|------|
| "Good code quality" | "Variables use snake_case, functions ≤ 20 lines, no magic numbers" |
| "Looks nice" | "Card radius 12px, shadow 0 2px 8px rgba(0,0,0,0.08), mobile breakpoint 768px" |
| "Flows well" | "Average sentence < 30 chars, paragraphs linked with transitions, no 3+ consecutive parallel sentences" |

## File Structure

```
Orchestrator/
├── SKILL.md                        # Skill definition & Orch manual
├── README.md                       # 中文说明
├── README_EN.md                    # English docs
├── scripts/
│   ├── judge.py                    # Code gatekeeper (pure Python)
│   ├── loop.py                     # Background engine
│   └── status.py                   # Progress viewer
├── references/
│   └── schema.md                   # Artifact JSON schemas
└── examples/
    └── sample-config.json          # Demo config
```

## Configuration Options

| Option | Default | Description |
|--------|---------|-------------|
| `production_model` | `haiku` | Model for production Worker |
| `check_model` | `sonnet` | Model for check Worker |
| `production_backend` | `claude` | Backend: `claude` or `api` |
| `check_backend` | `claude` | Backend: `claude` or `api` (use `api` for multimodal) |
| `api_endpoint` | — | OpenAI-compatible API endpoint |
| `api_key` | — | API key |
| `max_rounds` | 3 | Max retry rounds |
| `bare` | `true` | `true` = isolated (no network), `false` = full (WebSearch ok) |
| `worker_timeout` | 600 | Worker timeout in seconds |

## Requirements

- Python 3.12+
- [Claude Code](https://claude.ai/code) CLI

## Why

When an AI model both produces and judges its own output, it subconsciously lowers the bar. The solution is the oldest trick in software engineering: **separation of duties + automated acceptance testing.** This project applies that pattern to AI agent collaboration.

## License

MIT
