# Orchestrator

**职责分离式 AI 质量保障系统。** 生产 Agent 执行 → 检查 Agent 盲审打分 → 代码判分。不让任何 AI 模型同时当运动员和裁判。

[English](README_EN.md)

---

## 架构

```
你（用户）──→ Orch（Claude）──→ loop.py（后台引擎）
                                      │
                         ┌────────────┼────────────┐
                         ▼            ▼            ▼
                   生产 Worker   检查 Worker    judge.py
                   (claude -p)   (claude -p)   (纯代码)
                         │            │            │
                    task.json  checklist.json criteria.json
                         │            │            │
                         └── 产出 ──→ 打分 ──→ PASS/FAIL
```

| 角色 | 是谁 | 做什么 | 知道什么 |
|------|------|--------|---------|
| Orch | 主对话 Claude | 理解、拆解、调度、汇报 | 全部 |
| loop.py | Python 脚本 | 启 Worker、跑循环、写审计 | 全部 artifact |
| 生产 Worker | `claude -p` 子进程 | 执行任务、产出结果 | 只拿到 task.json |
| 检查 Worker | `claude -p` 子进程 | 逐条审查、打分 | 只拿到 checklist.json + 产出 |
| judge.py | Python 脚本 | 比对验收标准 vs 打分结果 | criteria.json + 检查结果 |

## 核心约束

| # | 规则 |
|---|------|
| 0 | **放行判定只能由代码做** — judge.py 是唯一的守门人 |
| 1 | **生产/检查 Worker 上下文完全隔离** — 独立 claude -p 进程 |
| 2 | **生产 Worker 不拿验收标准** — 只拿到 task.json |
| 3 | **检查 Worker 不拿验收标准** — 只拿到 checklist.json |
| 4 | **验收标准只出现在 judge.py 输入** — 不经过任何模型 |
| 5 | **人工终审是强制闸门** — judge.py PASS ≠ 交付 |

## 快速开始

### 1. 拆需求

创建 config.json，包含三段：

```json
{
  "task": {
    "description": "做什么。不包含任何验收标准。",
    "output_format": { "schema": {} }
  },
  "checklist": {
    "items": [
      { "id": "correctness", "dimension": "正确性", "check": "验证逻辑是否正确", "scoring": {"type": "score", "max": 10} }
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

### 2. 启动

```bash
python3 scripts/loop.py --config examples/sample-config.json
```

loop.py 后台运行。Orch 保持交互——自由聊天，随时查进度。

### 3. 查看进度

```bash
python3 scripts/status.py                          # 阶段快照
tail -f run_output/<ts>/round_1/production_live.log  # 实时 Worker 输出
```

或者启动 Agent Monitor（默认行为）：

```
Agent 任务：每 20 秒读 progress.json + *_live.log，有变化就汇报。
```

### 4. 人工终审

`FINAL_PASS.json` 出现后，Orch 展示结果。用户确认 → 交付。

## 检查项设计原则

> 尽可能减少主观判断。每个评分维度都应该是可量化的。如果必须有主观判断，也要有清晰明确的描述。

| ❌ 差 | ✅ 好 |
|-------|------|
| "代码质量好" | "变量命名使用 snake_case，函数不超过 20 行，无魔法数字" |
| "设计好看" | "卡片圆角 12px，阴影 0 2px 8px rgba(0,0,0,0.08)，移动端断点 768px" |
| "文章读起来流畅" | "平均句长 < 30 字，段落之间有关联词，无连续 3 段以上并列句" |

## 文件结构

```
Orchestrator/
├── SKILL.md                        # Skill 定义 & Orch 操作手册
├── README.md                       # 中文说明
├── README_EN.md                    # English docs
├── scripts/
│   ├── judge.py                    # 代码判官（纯 Python）
│   ├── loop.py                     # 后台引擎
│   └── status.py                   # 进度查看器
├── references/
│   └── schema.md                   # Artifact JSON Schema
└── examples/
    └── sample-config.json          # 示例配置
```

## 配置选项

| 选项 | 默认值 | 说明 |
|------|--------|------|
| `production_model` | `haiku` | 生产 Worker 模型 |
| `check_model` | `sonnet` | 检查 Worker 模型 |
| `production_backend` | `claude` | 生产后端：claude 或 api |
| `check_backend` | `claude` | 检查后端：claude 或 api（多模态用 api） |
| `api_endpoint` | — | OpenAI 兼容 API 地址 |
| `api_key` | — | API 密钥 |
| `max_rounds` | 3 | 最大重试轮次 |
| `bare` | `true` | true=隔离模式无网络, false=可搜索 |
| `worker_timeout` | 600 | Worker 超时秒数 |

## 依赖

- Python 3.12+
- [Claude Code](https://claude.ai/code) CLI

## 为什么

当 AI 模型既当运动员又当裁判，它会下意识放水让自己通过。解决方案是软件工程最古老的一招：**职责分离 + 自动化验收测试。** 这个项目把这个模式应用到了 AI Agent 协作中。

## License

MIT
