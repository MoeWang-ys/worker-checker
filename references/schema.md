# Artifact JSON Schema 参考

三个 artifact 的完整字段定义和约束。

---

## task.json — 生产 Worker 输入

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Task",
  "type": "object",
  "required": ["description", "output_format"],
  "properties": {
    "description": {
      "type": "string",
      "description": "任务描述。只说做什么，不说怎么检查。不含任何验收标准。"
    },
    "output_format": {
      "type": "object",
      "required": ["description"],
      "properties": {
        "description": {
          "type": "string",
          "description": "产出物格式的文字描述"
        },
        "schema": {
          "type": "object",
          "description": "可选的 JSON Schema，约束输出结构"
        },
        "example": {
          "type": "object",
          "description": "可选的输出示例"
        }
      }
    },
    "context": {
      "type": "object",
      "properties": {
        "files": {
          "type": "array",
          "items": {"type": "string"},
          "description": "Worker 可访问的文件路径"
        },
        "constraints": {
          "type": "array",
          "items": {"type": "string"},
          "description": "技术/环境约束"
        },
        "reference_code": {
          "type": "string",
          "description": "参考代码片段（如有）"
        }
      }
    },
    "feedback": {
      "type": "object",
      "description": "上一轮检查的反馈（仅重试时由 loop.py 填入，首次为空）"
    }
  }
}
```

### 生产 Worker 的 system prompt 模板

```
你是生产 Worker。你的唯一职责是按任务描述产出结果。
规则：
1. 只做任务描述里要求的事，不做额外的事
2. 不自我评价，不自我审查
3. 按 output_format 要求的格式输出
4. 如果收到上一轮的反馈，按反馈修复问题
```

---

## checklist.json — 检查 Worker 输入

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "Checklist",
  "type": "object",
  "required": ["items"],
  "properties": {
    "items": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "dimension", "check"],
        "properties": {
          "id": {
            "type": "string",
            "description": "唯一标识，对应 criteria.json 中的 source 路径"
          },
          "dimension": {
            "type": "string",
            "description": "评分维度：正确性、安全性、性能、可读性、完整性..."
          },
          "check": {
            "type": "string",
            "description": "具体检查什么，用自然语言描述"
          },
          "scoring": {
            "type": "object",
            "properties": {
              "type": {
                "type": "string",
                "enum": ["score", "pass_fail", "level"],
                "description": "评分方式"
              },
              "max": {
                "type": "number",
                "description": "score 类型时的满分值"
              },
              "levels": {
                "type": "array",
                "items": {"type": "string"},
                "description": "level 类型时的等级列表"
              }
            }
          },
          "weight": {
            "type": "number",
            "description": "权重（用于综合计分，默认均等）"
          }
        }
      }
    }
  }
}
```

### 检查 Worker 的 system prompt 模板

```
你是检查 Worker。你的唯一职责是按检查项逐一审查产出结果，给出客观评分。
规则：
1. 逐条对照检查项，不遗漏
2. 评分客观，不手软也不刁难
3. 不知道"多少分算过"——你只管打分
4. 按要求的 JSON 格式输出评分结果
```

### 检查 Worker 的输出格式（必须严格遵守）

```json
{
  "results": [
    {
      "item_id": "check_001",
      "dimension": "正确性",
      "score": 8,
      "max_score": 10,
      "pass": true,
      "notes": "具体评分依据，哪里好哪里不好"
    }
  ],
  "overall": {
    "total_score": 42,
    "max_total": 50,
    "pass_rate": 0.84,
    "summary": "一句话总结"
  }
}
```

---

## criteria.json — judge.py 输入（不经过任何模型）

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "AcceptanceCriteria",
  "type": "object",
  "required": ["pass_conditions", "logic"],
  "properties": {
    "pass_conditions": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "type", "source", "operator", "value"],
        "properties": {
          "id": {
            "type": "string",
            "description": "条件唯一标识"
          },
          "type": {
            "type": "string",
            "enum": ["threshold", "exact", "regex", "script", "schema", "all_items_pass"],
            "description": "判定类型"
          },
          "source": {
            "type": "string",
            "description": "从 check_result.json 取值的 JSONPath 表达式。如 overall.pass_rate, results[0].score"
          },
          "operator": {
            "type": "string",
            "enum": [">=", ">", "==", "<=", "<", "matches", "contains", "!="],
            "description": "比较运算符"
          },
          "value": {
            "description": "阈值。类型取决于 type"
          },
          "description": {
            "type": "string",
            "description": "人类可读的通过条件说明"
          }
        }
      }
    },
    "logic": {
      "type": "string",
      "enum": ["all", "any", "majority"],
      "description": "all=所有条件通过才算通过, any=任一通过即可, majority=多数通过"
    },
    "majority_threshold": {
      "type": "number",
      "minimum": 0,
      "maximum": 1,
      "description": "majority 模式下的通过比例，默认 0.5"
    },
    "max_rounds": {
      "type": "integer",
      "minimum": 1,
      "maximum": 10,
      "default": 3,
      "description": "最大重试轮次"
    },
    "hard_blocks": {
      "type": "array",
      "items": {"type": "string"},
      "description": "一票否决的条件 ID 列表。这些条件任何一个失败，直接 FAIL，不管 logic 设置。"
    }
  }
}
```

### 判定类型详解

| type | 用途 | value 示例 | 行为 |
|------|------|-----------|------|
| `threshold` | 数值比较 | `0.8` | source 值 >= 0.8 |
| `exact` | 精确匹配 | `"production"` | source 值 == "production" |
| `regex` | 正则匹配 | `"error.*not found"` | source 值 matches regex |
| `script` | 自定义脚本 | `"python3 check.py output/"` | 脚本 exit code 0 = 通过 |
| `schema` | JSON Schema | `{"type": "object", ...}` | source JSON 符合 schema |
| `all_items_pass` | 所有检查项 pass | `true` | results 数组每个元素的 pass 都为 true |
