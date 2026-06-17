**English** | [中文](README.md)

# Orchestrator

A Claude Code skill that makes AI agents deliver high-quality results — by separating production, blind review, and automated judgment into independent workers. No AI model is both player and referee.

## What You Get

Describe what you want. Orchestrator breaks it down, lets a Production Agent build it, has a Check Agent review it blind, and a code judge (`judge.py`) decides pass or fail. If it fails, the feedback goes back to production for another round. You only get involved for final approval.

- **Production Agent** — executes the task, never sees acceptance criteria
- **Check Agent** — scores the output against a checklist, never knows the passing threshold
- **Judge (pure Python)** — compares checklist scores against hard criteria, decides pass/fail
- **Auto-retry loop** — failed rounds feed back to production, up to 3 rounds
- **Full audit trail** — every round's output, scores, and rulings saved to disk
- **Agent Monitor** — a subagent watches progress in real-time and reports changes
- **Multimodal support** — plug in external vision models (MiMo, GPT-4o, etc.) for checking images/UI/screenshots

## Quick Start

**1. Install**

Give your Claude Code the GitHub link and let it handle installation:

```
Install this skill for me: https://github.com/Gavin9902/orchestrator-ai
```

Claude Code will clone and link the skill into `~/.claude/skills/`.

**2. Summon**

```
/orchestrator
```

**3. Talk through your requirements**

Orch will guide you in clarifying what needs to be done and what "good" looks like — but won't set standards for you. You and Orch figure them out together.

**4. Wait for results**

Once requirements are confirmed, Orch launches loop.py + Agent Monitor in the background. Keep chatting or ask about progress anytime.

**5. Approve delivery**

Orch presents results when done. Nothing is delivered until you say yes. Change the standards and re-run if you want.

## See an Example

You say: "Build a personal timeline page for Zara Zhang, showing her published opinions and tools from 2023 to now. Reverse chronological, alternating left-right cards."

### Orch decomposes

Orch clarifies with you: data sources (GitHub, Xiaohongshu, X/Twitter), time range (2023-2026), style (vertical timeline, alternating cards, reverse order). Then produces three artifacts:

- **task.json** — what to do, no acceptance criteria inside
- **checklist.json** — 4 dimensions: HTML structure, timeline ordering, layout, content coverage
- **criteria.json** — hard thresholds: all structural checks must pass, content coverage ≥ 7/10

### Background execution

The Production Agent (Sonnet, with web search) searches GitHub, X/Twitter, podcasts, and Xiaohongshu on its own. It collects 22 timeline entries and generates the HTML. The Check Agent reviews every item — 18/18 score. judge.py: 3/3 passed. One round, done.

### Delivery

```
✅ Round 1 passed | 3/3 conditions met
   ✅ HTML structure valid
   ✅ Timeline reverse-chronological, 22 entries
   ✅ Left-right alternating layout, mobile responsive
   ✅ Content: 12 tools + 6 opinions + 4 milestones
   ✅ Design quality: 5/5
⏸  Awaiting human final approval...
```

Open the HTML in a browser — gradient title, card shadows, entrance animations, mobile responsive. From "I want this" to seeing the result took 12 minutes. You did exactly one thing: confirm the requirements.

## Changing Settings

Settings are configured through conversation with Orch. Just say:

- "Use Haiku for production, Opus for checking"
- "Switch to 5 retry rounds"
- "Update the multimodal API key to sk-xxx"
- "Show my current settings"

For direct config, edit the options in your task's config.json or `~/.orchestrator-config.json`.

## Checklist Design

The hardest part of quality assurance is defining what "good" means. The principle:

**Minimize subjective judgment. Every scoring dimension should be quantifiable.**

| ❌ Bad | ✅ Good |
|--------|------|
| "Good code quality" | "Variables use snake_case, functions ≤ 20 lines, no magic numbers" |
| "Looks nice" | "Card radius 12px, shadow 0 2px 8px rgba(0,0,0,0.08), mobile breakpoint 768px" |
| "Flows well" | "Average sentence < 30 chars, paragraphs linked with transitions" |

## Requirements

- Python 3.12+
- [Claude Code](https://claude.ai/code) CLI

## License

MIT
