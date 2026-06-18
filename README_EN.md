**English** | [中文](README.md)

# Orchestrator

A Claude Code skill for reliable AI output. Separates production, blind review, and automated judgment into independent workers. No AI model is both player and referee.

> "They just don't work. It's slop." — **Andrej Karpathy**, OpenAI co-founder. Inventor of vibe coding.
>
> "AI gets you 70% of the way. The last 30% is just as hard. Trust is declining." — **Addy Osmani**, Google Chrome Engineering Director.
>
> "Spending more time debugging AI output than if they coded it themselves." — Stack Overflow 2025 Survey. Trust dropped from 40% → **29%**.

**The problem isn't model capability. It's that nobody checks the output.**

## What You Get

Describe what you want. Orch decomposes, Production Agent builds, Check Agent scores blind, and the code judge (`judge.py`) decides pass or fail. Failed rounds feed back for retry. You only confirm at the end.

- **Production Agent** — executes tasks, never sees acceptance criteria
- **Check Agent** — scores against a checklist, doesn't know the passing threshold
- **Judge (pure Python)** — compares scores against hard criteria. The only thing that can say "pass"
- **Auto-retry** — failed feedback goes back to production, up to 3 rounds
- **Agent Monitor** — enabled by default, real-time progress reporting
- **Full audit trail** — every round's output, scores, and rulings saved to disk
- **Multimodal** — plug in external vision models (MiMo, GPT-4o)

## You do one thing: confirm.

**1. Install**

Give Claude Code the link:

```
Install this skill for me: https://github.com/Gavin9902/orchestrator-ai
```

**2. Summon**

```
/orchestrator
```

**3. Talk through requirements**

Orch guides you in clarifying what needs to be done and what "good" means.

**4. Wait**

Orch launches loop.py + Agent Monitor in background. Chat freely, check progress anytime.

**5. Approve**

Orch presents results. Nothing is delivered until you say yes.

## See an Example

Same DeepSeek V4 Flash model. Same task: generate a 7-day meal plan with 21 meals. Daily calories 1800-2200 kcal. Protein:Carbs:Fat = 30:40:30.

### Direct generation (no QA)

DeepSeek outputs directly. **1 out of 7 days passes** macro ratio checks. Protein drifts to 33%, carbs and fat ratios all over the place. Looks reasonable. Math doesn't check out.

### /orchestrator (with blind review)

Production Worker generates → Check Worker verifies every calorie and macro ratio → Round 1 format error **caught and rejected** → feedback → Production fixes → Round 2: **7/7 all pass**. All 21 meals verified.

```
              Direct         /orchestrator
Pass rate      1/7 (14%)      7/7 (100%)
Macro errors   6 days          0 days
Calorie math   unchecked      21/21 verified
Self-awareness none           Check Worker scored 18/18
```

**Same model. 14% → 100%. The difference isn't the model. It's the blind review.**

## Changing Settings

Tell Orch in plain language:

- "Use Haiku for production, Opus for checking"
- "Retry up to 5 rounds"
- "Update the multimodal API key"
- "Show current settings"

## Checklist Design

Define what "good" means. **Quantify everything. Minimize subjective judgment.**

| ❌ Bad | ✅ Good |
|--------|------|
| "Good code quality" | "Variables use snake_case, functions ≤ 20 lines, no magic numbers" |
| "Looks nice" | "Card radius 12px, shadow 0 2px 8px rgba(0,0,0,0.08), breakpoint 768px" |
| "Flows well" | "Average sentence < 30 chars, transitions between paragraphs" |

## Requirements

Python 3.12+ · [Claude Code](https://claude.ai/code) CLI

## License

MIT
