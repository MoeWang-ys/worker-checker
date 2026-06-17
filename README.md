[English](README_EN.md) | **中文**

# Orchestrator

一个 Claude Code skill，让 AI agent 产出高质量结果——把生产、盲审、自动判分拆成三个独立 Worker。不让任何 AI 模型同时当运动员和裁判。

## 你会得到什么

描述你想要什么。Orchestrator 拆解需求，让生产 Agent 干活，检查 Agent 盲审打分，代码判官（`judge.py`）决定过不过。没过就带反馈回传给生产重来，直到通过或达到最大轮次。你只做最后的确认。

- **生产 Agent** — 执行任务，不知道验收标准
- **检查 Agent** — 对照检查项打分，不知道及格线
- **判官（纯 Python）** — 拿打分结果比对硬性标准，决定过不过
- **自动重试循环** — 失败轮次反馈回生产，最多 3 轮
- **完整审计追溯** — 每轮的产出、打分、判定全落盘
- **Agent Monitor** — 一个 subagent 实时监控进度，有变化就汇报
- **多模态支持** — 接入外部视觉模型（MiMo、GPT-4o 等）检查图片/UI/截图

## 快速开始

1. 在 Claude Code 里输入 `/orchestrator`
2. 描述你的需求
3. Orch（你的主对话 Claude）拆解需求，后台启动循环
4. 正常聊天，随时问进度
5. 跑完后 Orch 展示结果。你确认 → 交付

```bash
# 或者直接运行：
python3 scripts/loop.py --config examples/sample-config.json
```

首次使用时，如果任务需要多模态检查（图片、UI、截图），而当前模型不支持图片，Orch 会询问 API endpoint 和 key。配置存入 `~/.orchestrator-config.json`，下次自动用。

## 修改设置

通过对话修改配置。直接告诉 Orch：

- "生产用 Haiku，检查用 Opus"
- "重试改成 5 轮"
- "更新多模态 API key 为 sk-xxx"
- "显示当前配置"

也可以直接编辑 config.json 或 `~/.orchestrator-config.json`。

## 检查项设计

质量保障最难的部分是定义"好"的标准。核心原则：

**尽可能减少主观判断，每个评分维度都应该是可量化的。**

| ❌ 差 | ✅ 好 |
|-------|------|
| "代码质量好" | "变量用 snake_case，函数 ≤ 20 行，无魔法数字" |
| "设计好看" | "卡片圆角 12px，阴影 0 2px 8px rgba(0,0,0,0.08)，移动端断点 768px" |
| "读起来流畅" | "平均句长 < 30 字，段落之间有关联词" |

## 依赖

- Python 3.12+
- [Claude Code](https://claude.ai/code) CLI

## License

MIT
