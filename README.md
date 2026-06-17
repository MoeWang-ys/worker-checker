# Orchestrator

**AI quality assurance through separation of duties.** Production Agent executes → Check Agent scores blind → Code judges. No AI model gets to be both player and referee.

**职责分离式 AI 质量保障系统。** 生产 Agent 执行 → 检查 Agent 盲审打分 → 代码判分。不让任何 AI 模型同时当运动员和裁判。

---

## Architecture / 架构

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

## Core Rules / 核心约束

| # | Rule / 规则 |
|---|------------|
| 0 | **Only code decides pass/fail** — judge.py is the sole gatekeeper |
| 1 | **Production & Check Workers fully isolated** — separate `claude -p` processes |
| 2 | **Production Worker never sees criteria** — only gets task.json |
| 3 | **Check Worker never sees criteria** — only gets checklist.json |
| 4 | **Criteria only appear in judge.py input** — never passes through a model |
| 5 | **Human final approval is mandatory** — judge.py PASS ≠ delivered |

## Quick Start / 快速开始

### 1. Orch decomposes the requirement / 拆需求

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

### 2. Launch loop.py / 启动

```bash
python3 scripts/loop.py --config examples/sample-config.json
```

loop.py runs in background. Orch stays interactive — chat freely, check progress anytime.

### 3. Check progress / 查看进度

```bash
python3 scripts/status.py                    # Phase snapshot
tail -f run_output/<ts>/round_1/production_live.log  # Live Worker output
```

Or launch an Agent Monitor:

```
Agent task: "Check progress.json + *_live.log every 20s, report changes."
```

### 4. Human final review / 人工终审

When `FINAL_PASS.json` appears, Orch presents results. User confirms → delivered.

## Checklist Design Principle / 检查项设计原则

> Minimize subjective judgment. Every scoring dimension should be quantifiable. When subjective judgment is unavoidable, provide clear, specific descriptions.

> 尽可能减少主观判断。每个评分维度都应该是可量化的。如果必须有主观判断，也要有清晰明确的描述。

| ❌ Bad / 差 | ✅ Good / 好 |
|-------------|-------------|
| "代码质量好" | "变量命名使用 snake_case，函数不超过 20 行，无魔法数字" |
| "设计好看" | "卡片圆角 12px，阴影 0 2px 8px rgba(0,0,0,0.08)，移动端断点 768px" |
| "文章读起来流畅" | "平均句长 < 30 字，段落之间有关联词，无连续 3 段以上并列句" |

## File Structure / 文件结构

```
Orchestrator/
├── SKILL.md                        # Skill definition & Orch manual
├── README.md
├── scripts/
│   ├── judge.py                    # Code gatekeeper (pure Python)
│   ├── loop.py                     # Background engine
│   └── status.py                   # Progress viewer
├── references/
│   └── schema.md                   # Artifact JSON schemas
└── examples/
    └── sample-config.json          # Demo config (math_utils.py)
```

## Configuration Options / 配置选项

| Option | Default | Description |
|--------|---------|-------------|
| `production_model` | `haiku` | Model for production Worker |
| `check_model` | `sonnet` | Model for check Worker |
| `max_rounds` | 3 | Max retry rounds |
| `bare` | `true` | `true` = isolated (no network), `false` = full (WebSearch ok) |
| `worker_timeout` | 600 | Worker timeout in seconds |

## Requirements / 依赖

- Python 3.12+
- [Claude Code](https://claude.ai/code) CLI (for Worker subprocesses)

## Why / 为什么

When an AI model both produces and judges its own output, it subconsciously lowers the bar. The solution is the oldest trick in software engineering: **separation of duties + automated acceptance testing.** This project applies that pattern to AI agent collaboration.

当 AI 模型既当运动员又当裁判，它会下意识放水让自己通过。解决方案是软件工程最古老的一招：**职责分离 + 自动化验收测试。** 这个项目把这个模式应用到了 AI Agent 协作中。

## License

MIT
