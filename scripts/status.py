#!/usr/bin/env python3
"""
status.py — 查看 loop.py 执行进度

用法:
    python3 status.py <output_dir>

输出当前执行状态、所处阶段、每轮结果摘要。

示例:
    python3 status.py run_output/20260617_212841
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m{s}s"


def get_status(output_dir: Path) -> dict:
    progress_file = output_dir / "progress.json"
    final_pass = output_dir / "FINAL_PASS.json"
    final_fail = output_dir / "FINAL_FAIL.json"

    # 检查是否已完成
    if final_pass.exists():
        data = json.loads(final_pass.read_text(encoding="utf-8"))
        return {
            "status": "passed",
            "round": data["round"],
            "message": f"第 {data['round']} 轮通过，等待人工终审",
            "detail": data,
        }
    if final_fail.exists():
        data = json.loads(final_fail.read_text(encoding="utf-8"))
        return {
            "status": "failed",
            "max_rounds": data["max_rounds"],
            "message": f"已达最大轮次，未通过",
            "detail": data,
        }

    # 读取实时进度
    if not progress_file.exists():
        # 尝试从已有的 round 目录推断
        if not output_dir.exists():
            return {"status": "unknown", "message": "输出目录不存在，可能尚未启动"}
        rounds = sorted(output_dir.glob("round_*"))
        if not rounds:
            return {"status": "starting", "message": "刚启动，尚未开始第1轮"}
        return {"status": "running", "message": f"正在运行，已完成 {len(rounds)} 个目录", "rounds_found": len(rounds)}

    progress = json.loads(progress_file.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    started = datetime.fromisoformat(progress["started_at"])
    elapsed = (now - started).total_seconds()

    status = {
        "status": progress["status"],
        "current_round": progress.get("current_round"),
        "max_rounds": progress.get("max_rounds"),
        "phase": progress.get("phase"),
        "started_at": progress["started_at"],
        "elapsed": format_duration(elapsed),
        "message": "",
        "rounds_summary": progress.get("rounds", []),
    }

    phase_labels = {
        "production_worker": "正在执行生产 Worker",
        "check_worker": "正在执行检查 Worker",
        "judging": "正在运行 judge.py 比对",
        "retrying": "准备重试，将反馈回传生产 Worker",
    }
    phase_label = phase_labels.get(progress.get("phase", ""), progress.get("phase", "?"))

    if progress["status"] == "running":
        status["message"] = (
            f"第 {progress['current_round']}/{progress['max_rounds']} 轮 · {phase_label} · 已运行 {format_duration(elapsed)}"
        )
    elif progress["status"] == "completed":
        status["message"] = f"循环完成 · 总耗时 {format_duration(elapsed)}"

    return status


def render(status: dict) -> str:
    lines = ["═══ Orchestrator Loop 状态 ═══", ""]
    lines.append(f"状态: {status['message']}")

    if status.get("rounds_summary"):
        lines.append("")
        lines.append("各轮摘要:")
        for r in status["rounds_summary"]:
            icon = "✅" if r.get("judge_pass") else "❌" if r.get("status") == "failed" else "🔄"
            phase = r.get("phase", r.get("status", "?"))
            lines.append(f"  {icon} 第{r['round']}轮: {phase}")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        # 尝试找到最新的 run_output 目录
        output_dirs = sorted(Path("run_output").glob("*"), reverse=True)
        if output_dirs:
            output_dir = output_dirs[0]
        else:
            print("用法: python3 status.py <output_dir>", file=sys.stderr)
            print("没有找到 run_output 目录", file=sys.stderr)
            sys.exit(1)
    else:
        output_dir = Path(sys.argv[1])

    status = get_status(output_dir)
    print(render(status))

    # 如果有详细错误，打印
    if status["status"] == "failed" and status.get("detail"):
        detail = status["detail"]
        if detail.get("last_feedback"):
            fb = detail["last_feedback"]
            print(f"\n最后一轮反馈: {fb.get('judge_summary', '')}")


if __name__ == "__main__":
    main()
