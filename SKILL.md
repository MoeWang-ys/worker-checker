---
name: orchestrator
description: 职责分离式 AI 质量保障系统。Orch 拆需求→生产Worker 执行→检查Worker 盲审→代码判分→人工终审。触发词：orchestrator、质量保障、生产检查循环、loop.py、AI质检。
---

# Orchestrator · 职责分离式质量保障

## 角色分工（先搞清楚谁是谁）

```
你（用户）
  │  提需求，做人工终审
  │
  ▼
我（Orch = 主对话 Claude）
  │  跟你聊天的人。理解需求、拆 artifact、启 loop.py、查进度、展示结果。
  │  一直在，不会消失。skill 加载后我就知道怎么干 Orchestrator 的活。
  │
  ├── 装备：scripts/judge.py    — 代码判官（纯 Python，零 LLM）
  ├── 装备：scripts/loop.py     — 后台引擎（调 claude -p 启 Worker，跑循环）
  ├── 装备：scripts/status.py   — 进度查看器（读 progress.json）
  └── 装备：references/schema.md — artifact 格式定义
        │
        ▼
     loop.py（启动后独立运行，Orch 不阻塞）
        │
        ├── claude -p --model haiku  = 生产 Worker（只执行，不评判）
        ├── claude -p --model sonnet = 检查 Worker（只打分，不定标准）
        └── python3 judge.py         = 代码判分（唯一放行判定）
```

| 角色 | 是谁 | 做什么 | 知道什么 |
|------|------|--------|---------|
| 你 | 用户 | 提需求、终审确认 | 全部 |
| 我（Orch） | 主对话 Claude | 沟通、拆解、调度、汇报 | 全部 |
| loop.py（后台引擎） | Python 脚本 | 启 Worker、跑循环、写审计 | 全部 artifact |
| 生产 Worker | `claude -p` 子进程 | 执行任务、产出结果 | 只拿到 task.json |
| 检查 Worker | `claude -p` 子进程 | 逐条审查、打分 | 只拿到 checklist.json + 生产输出 |
| judge.py（判官） | Python 脚本 | 比对验收标准 vs 打分结果 | criteria.json + check_result.json |

## 核心约束

| # | 规则 | 持有者 |
|---|------|--------|
| 0 | 放行判定只能由代码做 | **judge.py** |
| 1 | 生产/检查 Worker 上下文完全隔离 | **loop.py 通过独立 claude -p 保证** |
| 2 | 生产 Worker 不拿验收标准 | **Orch 不在 task.json 里放标准** |
| 3 | 检查 Worker 不拿验收标准 | **Orch 不在 checklist.json 里放标准** |
| 4 | 验收标准只出现在 judge.py 输入 | **criteria.json → judge.py，不经过模型** |
| 5 | 人工终审是强制闸门 | **你（用户）在 judge.py PASS 后必须确认** |

## 我的工作流程（Orch 操作手册）

### 第一步：拆需求

你提需求后，我产出 **一个 config.json**（内含 task + checklist + criteria 三段），格式见 `references/schema.md`。

关键原则：
- task 里**不准出现**"至少 80 分""必须通过"这类验收标准
- checklist 里**不准出现**"8/10 以上算过"这类及格线
- criteria 是纯机器规则，用 threshold/exact/regex/script/schema 表达

### 第二步：启动 loop.py

```bash
# 后台运行，我不阻塞
python3 scripts/loop.py --config <config.json>
# 最后一行输出: LOOP_RESULT: PASS | round=1 | passed=3/3 | output=run_output/20260617_xxx/
```

我用 Bash 工具的 `run_in_background` 参数启动，loop.py 在后台跑，我立刻回来继续跟你聊天。

### 第三步：陪你等结果

loop.py 跑着的时候，你可以：
- 问我进度 → 我跑 `python3 scripts/status.py` 回答
- 问我任何问题 → 正常对话，不耽误
- 让我改需求 → 我记下，如果 loop.py 还没跑完可以先 kill 重来，等跑完了就基于审计记录调整后重来

### 第四步：收到通知，展示结果

loop.py 跑完，Claude Code 自动通知我。我打开审计目录：
- 看 `FINAL_PASS.json`：哪轮过的、各项细节
- 看 `round_N/production_result.json`：生产 Worker 的产出
- 看 `round_N/check_result.json`：检查 Worker 打的分
- 展示给你，**等你确认**。你不确认，不算交付。

### 第五步：人工终审

你确认 → 交付。你有意见 → 我改 config 或加约束，重跑。

## 执行流程图

```
你提需求
  │
  ▼
我拆解 → 保存 config.json
  │
  ├─ 后台启动 loop.py
  ├─ "已启动，输出在 run_output/xxx/，随时问进度"
  │
  ▼  loop.py 在后台跑，我和你自由对话 ──────────────┐
  │                                                   │
你："到哪了？"                                         │
我：（跑 status.py）"第 2/3 轮，正在检查"               │
  │                                                   │
你："对了需求里再加个条件"                               │
我："记下了，跑完这轮我再追加"                           │
  │                                                   │
  │           loop.py 跑完 ──→ Claude Code 通知我 ────┘
  ▼
我看到 LOOP_RESULT: PASS
  │
  ├─ 打开 FINAL_PASS.json + 生产结果 + 检查报告
  ├─ 展示给你
  └─ "确认通过？"
        │
        ├─ 你确认 → 交付
        └─ 你有意见 → 我拆新 config，重跑 loop.py
```

## loop.py 做了什么（你不需要手动管的部分）

```
loop.py 启动
  │
  └─ for round in 1..3:
       │
       ├─ ① 生产 Worker
       │     claude -p --model haiku --bare --system-prompt "你是生产Worker"
       │     输入: task.json
       │     输出: production_result.json → 落盘
       │     写 progress.json: phase=production_worker
       │
       ├─ ② 检查 Worker
       │     claude -p --model sonnet --bare --system-prompt "你是检查Worker"
       │     输入: checklist.json + 生产输出
       │     输出: check_result.json → 落盘
       │     写 progress.json: phase=check_worker
       │
       ├─ ③ judge.py 比对
       │     python3 judge.py criteria.json check_result.json
       │     写 progress.json: phase=judging
       │
       ├─ PASS → 写 FINAL_PASS.json，stdout 输出 LOOP_RESULT: PASS，exit 0
       └─ FAIL → 反馈写入 task.feedback，下一轮生产 Worker 会收到
                 写 progress.json: phase=retrying

3 轮 FAIL → 写 FINAL_FAIL.json，stdout 输出 LOOP_RESULT: FAIL，exit 1
```

每轮全部中间产物落盘。任何时候都能审计。

## 查看进度

### 机械方式（status.py）

| 你想知道 | 命令 |
|---------|------|
| 整体到哪了 | `python3 scripts/status.py` |
| 某轮 Worker 实时输出 | `tail -f run_output/<ts>/round_N/production_live.log` |
| 某轮生产了什么 | `cat run_output/<ts>/round_N/production_result.json` |
| 某轮检查结果 | `cat run_output/<ts>/round_N/check_result.json` |
| judge 怎么判的 | `cat run_output/<ts>/round_N/judge_result.json` |
| 最终结果 | `cat run_output/<ts>/FINAL_PASS.json` |

### 智能方式（Agent Monitor，推荐）

loop.py 启动后，另起一个 Agent subagent 专职监控：

```
Agent 任务：每20秒读 progress.json + *_live.log，有变化就汇报。
```

Agent 能理解输出内容，汇报比 status.py 更丝滑，比如"生产Worker已搜到5条小红书观点"。

**不要**起 Agent 之后自己还去读 output_file（那是完整 JSONL 记录，会撑爆上下文）。等 Agent 完成通知即可。

## 配置选项

```json
{
  "options": {
    "production_model": "haiku",      // 生产 Worker 模型
    "check_model": "sonnet",           // 检查 Worker 模型
    "max_rounds": 3,                   // 最大重试轮次
    "output_dir": "run_output",        // 审计输出目录
    "bare": true,                      // true=隔离模式无网络, false=可搜索
    "worker_timeout": 600              // Worker 超时秒数（搜索任务设 900+）
  }
}
```

## 模型分工

| 角色 | 模型 | 理由 |
|------|------|------|
| 我（Orch） | Opus | 需求理解、拆解质量、跟你沟通 |
| 生产 Worker | Haiku | 执行力，快+便宜 |
| 检查 Worker | Sonnet | 判断力，严格审查 |
| judge.py | — | 不是模型，是代码 |

## 路由表

| 当需要... | 读 |
|-----------|-----|
| 了解 artifact 格式 | `references/schema.md` |
| 看 judge.py 支持哪些判定类型 | `scripts/judge.py` 头部注释 |
| 看完整示例 | `examples/sample-config.json` |
