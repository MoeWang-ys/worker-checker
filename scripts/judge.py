#!/usr/bin/env python3
"""
judge.py — 唯一放行判定者（纯代码，零 LLM 调用）

这是整个 Orchestrator 架构的"局长"。所有通过/不通过的决定都在这里由代码做出，
不经过任何模型的判断。

用法:
    python3 judge.py <criteria.json> <check_result.json>

输入:
    criteria.json       — Orchestrator 生成的验收标准
    check_result.json   — 检查 Worker 的评分输出

输出 (stdout):
    JSON: {"pass": true/false, "details": [...], "summary": "..."}
    exit code 0 = 通过, 1 = 不通过, 2 = 执行错误

判定类型:
    threshold    — 数值比较 (>=, >, ==, <=, <, !=)
    exact        — 精确匹配
    regex        — 正则匹配
    schema       — JSON Schema 校验
    script       — 运行外部脚本，exit code 0 = 通过
    all_items_pass — 所有检查项的 pass 字段都为 true

组合逻辑:
    all      — 所有条件通过才算通过
    any      — 任一条件通过即可
    majority — 超过阈值比例通过即可
    hard_blocks — 一票否决条件列表
"""

import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any


def resolve_path(data: dict, path: str) -> Any:
    """简易 JSONPath 取值。支持 dot notation 和数组索引。

    resolve_path(data, "overall.pass_rate") -> data["overall"]["pass_rate"]
    resolve_path(data, "results[0].score") -> data["results"][0]["score"]
    """
    parts = re.split(r"\.|\[|\]", path)
    parts = [p for p in parts if p and not p.isdigit() is False]
    # 处理 results[0] -> ["results", "0"]
    tokens = re.findall(r"(\w+)(?:\[(\d+)\])?", path)
    result = data
    for key, idx in tokens:
        result = result[key]
        if idx:
            result = result[int(idx)]
    return result


def check_threshold(source_val: Any, operator: str, target: Any) -> tuple[bool, str]:
    ops = {
        ">=": lambda a, b: a >= b,
        ">": lambda a, b: a > b,
        "==": lambda a, b: a == b,
        "<=": lambda a, b: a <= b,
        "<": lambda a, b: a < b,
        "!=": lambda a, b: a != b,
    }
    fn = ops.get(operator)
    if fn is None:
        return False, f"未知运算符: {operator}"
    passed = fn(source_val, target)
    return passed, f"{source_val} {operator} {target} => {'PASS' if passed else 'FAIL'}"


def check_exact(source_val: Any, operator: str, target: Any) -> tuple[bool, str]:
    if operator == "==":
        passed = source_val == target
    elif operator == "!=":
        passed = source_val != target
    else:
        return False, f"exact 类型不支持运算符: {operator}"
    return passed, f"'{source_val}' {operator} '{target}' => {'PASS' if passed else 'FAIL'}"


def check_regex(source_val: Any, operator: str, pattern: str) -> tuple[bool, str]:
    if operator == "matches":
        passed = bool(re.search(pattern, str(source_val)))
    elif operator == "contains":
        passed = pattern in str(source_val)
    else:
        return False, f"regex 类型不支持运算符: {operator}"
    return passed, f"'{source_val}' {operator} '{pattern}' => {'PASS' if passed else 'FAIL'}"


def check_schema(source_val: Any, schema: dict) -> tuple[bool, str]:
    """简易 JSON Schema 校验（不依赖 jsonschema 库）。"""
    errors = []

    def _validate(instance: Any, s: dict, path: str = "$"):
        if "type" in s:
            expected = s["type"]
            actual = type(instance).__name__
            type_map = {
                "string": str, "number": (int, float), "integer": int,
                "boolean": bool, "array": list, "object": dict, "null": type(None),
            }
            expected_types = type_map.get(expected)
            if expected_types is None:
                return
            if isinstance(expected_types, tuple):
                if not isinstance(instance, expected_types):
                    errors.append(f"{path}: 期望类型 {expected}, 实际 {actual}")
            else:
                if not isinstance(instance, expected_types):
                    errors.append(f"{path}: 期望类型 {expected}, 实际 {actual}")

        if s.get("type") == "object" and "properties" in s and isinstance(instance, dict):
            for key, prop_schema in s["properties"].items():
                if key in instance:
                    _validate(instance[key], prop_schema, f"{path}.{key}")
                elif key in s.get("required", []):
                    errors.append(f"{path}.{key}: 缺少必需字段")

        if s.get("type") == "array" and "items" in s and isinstance(instance, list):
            for i, item in enumerate(instance):
                _validate(item, s["items"], f"{path}[{i}]")

        if "enum" in s and instance not in s["enum"]:
            errors.append(f"{path}: '{instance}' 不在允许值 {s['enum']} 中")

    _validate(source_val, schema)
    passed = len(errors) == 0
    detail = "schema 校验通过" if passed else "; ".join(errors)
    return passed, detail


def check_script(source_val: Any, script: str) -> tuple[bool, str]:
    """运行外部脚本，exit code 0 = 通过。"""
    try:
        result = subprocess.run(
            script, shell=True, capture_output=True, text=True, timeout=60
        )
        passed = result.returncode == 0
        detail = f"脚本 exit_code={result.returncode}"
        if result.stdout:
            detail += f", stdout={result.stdout.strip()[:200]}"
        if result.stderr:
            detail += f", stderr={result.stderr.strip()[:200]}"
        return passed, detail
    except subprocess.TimeoutExpired:
        return False, "脚本执行超时 (60s)"
    except Exception as e:
        return False, f"脚本执行异常: {e}"


def check_all_items_pass(source_val: Any) -> tuple[bool, str]:
    """检查所有检查项的 pass 字段是否都为 true。"""
    if not isinstance(source_val, list):
        return False, f"all_items_pass 期望数组，实际 {type(source_val).__name__}"
    failed = [r.get("item_id", "?") for r in source_val if not r.get("pass", False)]
    passed = len(failed) == 0
    detail = "所有检查项通过" if passed else f"未通过项: {failed}"
    return passed, detail


def evaluate_condition(condition: dict, check_result: dict) -> dict:
    """评估单条通过条件。"""
    cond_type = condition["type"]
    result = {
        "id": condition["id"],
        "description": condition.get("description", ""),
        "type": cond_type,
        "passed": False,
        "detail": "",
    }

    try:
        if cond_type == "script":
            source_val = check_result  # script 不依赖 source 字段
        elif cond_type == "schema":
            source_path = condition.get("source", "$")
            source_val = resolve_path(check_result, source_path) if source_path != "$" else check_result
        elif cond_type == "all_items_pass":
            source_path = condition.get("source", "results")
            source_val = resolve_path(check_result, source_path)
        else:
            source_val = resolve_path(check_result, condition["source"])

        if cond_type == "threshold":
            passed, detail = check_threshold(source_val, condition["operator"], condition["value"])
        elif cond_type == "exact":
            passed, detail = check_exact(source_val, condition["operator"], condition["value"])
        elif cond_type == "regex":
            passed, detail = check_regex(source_val, condition["operator"], condition["value"])
        elif cond_type == "schema":
            passed, detail = check_schema(source_val, condition["value"])
        elif cond_type == "script":
            passed, detail = check_script(source_val, condition["value"])
        elif cond_type == "all_items_pass":
            passed, detail = check_all_items_pass(source_val)
        else:
            passed, detail = False, f"未知判定类型: {cond_type}"

        result["passed"] = passed
        result["detail"] = detail
    except (KeyError, IndexError, TypeError) as e:
        result["passed"] = False
        result["detail"] = f"取值失败: {e}"
    except Exception as e:
        result["passed"] = False
        result["detail"] = f"判定异常: {e}"

    return result


def judge(criteria_path: str, check_result_path: str) -> dict:
    """执行完整判定流程。"""
    criteria = json.loads(Path(criteria_path).read_text(encoding="utf-8"))
    check_result = json.loads(Path(check_result_path).read_text(encoding="utf-8"))

    conditions = criteria["pass_conditions"]
    logic = criteria.get("logic", "all")
    hard_blocks = set(criteria.get("hard_blocks", []))
    majority_threshold = criteria.get("majority_threshold", 0.5)

    details = []
    for cond in conditions:
        detail = evaluate_condition(cond, check_result)
        details.append(detail)

    # 检查一票否决
    for detail in details:
        if detail["id"] in hard_blocks and not detail["passed"]:
            return {
                "pass": False,
                "logic": logic,
                "details": details,
                "summary": f"一票否决: {detail['id']} 未通过 — {detail['detail']}",
            }

    # 按逻辑组合判定
    passed_count = sum(1 for d in details if d["passed"])
    total = len(details)

    if logic == "all":
        final_pass = all(d["passed"] for d in details)
        summary = f"ALL: {passed_count}/{total} 通过"
    elif logic == "any":
        final_pass = any(d["passed"] for d in details)
        summary = f"ANY: {passed_count}/{total} 通过"
    elif logic == "majority":
        final_pass = (passed_count / total) >= majority_threshold
        summary = f"MAJORITY({majority_threshold:.0%}): {passed_count}/{total} 通过"
    else:
        final_pass = False
        summary = f"未知组合逻辑: {logic}"

    if not final_pass:
        summary += " => FAIL"
    else:
        summary += " => PASS"

    return {
        "pass": final_pass,
        "logic": logic,
        "details": details,
        "passed_count": passed_count,
        "total": total,
        "summary": summary,
    }


def main():
    if len(sys.argv) < 3:
        print("用法: python3 judge.py <criteria.json> <check_result.json>", file=sys.stderr)
        sys.exit(2)

    criteria_path = sys.argv[1]
    check_result_path = sys.argv[2]

    try:
        result = judge(criteria_path, check_result_path)
    except FileNotFoundError as e:
        print(json.dumps({"pass": False, "error": f"文件不存在: {e}"}, ensure_ascii=False))
        sys.exit(2)
    except json.JSONDecodeError as e:
        print(json.dumps({"pass": False, "error": f"JSON 解析失败: {e}"}, ensure_ascii=False))
        sys.exit(2)
    except Exception as e:
        print(json.dumps({"pass": False, "error": f"未知错误: {e}"}, ensure_ascii=False))
        sys.exit(2)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result["pass"] else 1)


if __name__ == "__main__":
    main()
