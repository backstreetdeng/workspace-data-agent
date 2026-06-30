---
name: pg-vector-search
description: "PostgreSQL 向量数据库检索：根据语义相似度从 29,150 个行业报告/政策/分析 chunks 中检索相关文档，支持 vector/keyword/hybrid 三种模式"
metadata: {"clawdbot":{"emoji": "馃攳"}, "openclaw": {"tools": ["search"]}}
---

# PostgreSQL 向量检索 Skill

## 功能说明

基于语义相似度从 PostgreSQL + pgvector 中检索文档切片。适用于：
- 市场数据检索
- 行业报告检索
- 政策文件检索
- 知识库问答

## 真实工具列表（2026-06-29 验证）

| 函数 | 用途 | 参数 |
|------|------|------|
| `vector_search(query, top_k, brand, source, search_mode)` | 主检索入口 | query 必填，search_mode ∈ {hybrid, vector, keyword} |
| `search_by_intent(intent_result, top_k)` | 意图识别后调用 | intent_result = {keywords, brands_mentioned, question} |
| `skill_main(action, params)` | OpenClaw skill 适配入口 | action ∈ {search, by_intent} |

## 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| query | string | 必填 | 检索查询文本 |
| top_k | int | 6 | 返回结果数量（建议 ≤ 50） |
| brand | string | None | 品牌过滤（如 "比亚迪"） |
| source | string | None | 来源过滤（如 "数据中心"） |
| search_mode | string | "hybrid" | hybrid/vector/keyword |

## 输出格式（已 verify）

```json
{
  "success": true,
  "query": "比亚迪 唐 销量",
  "search_mode": "hybrid",
  "count": 5,
  "results": [
    {
      "rank": 1,
      "content": "文档内容...",
      "score": 0.7251,
      "source": "数据中心",
      "brand": "比亚迪, 特斯拉, 理想, 问界",
      "file_name": "新能源分阶段车型及投放节奏对销量影响分析.md",
      "publish_date": null
    }
  ]
}
```

## 使用示例

```prose
session: data-agent
  prompt: "向量检索比亚迪唐销量：vector_search(query='比亚迪 唐 销量', top_k=10, search_mode='hybrid')"
```

```python
import sys
sys.path.insert(0, "skills/pg-vector-search")
from vector_search import vector_search
result = vector_search(query="增程式 销量", top_k=5, search_mode="hybrid")
print(result["count"], "chunks found")
```

## 技术实现

- **主文件**: `vector_search.py`（19.7KB，2026-06-29 已 fix）
- **真实函数**: `vector_search(query, top_k, brand, source, search_mode)` / `search_by_intent(intent_result, top_k)` / `skill_main(action, params)`
- **底层 RAG 引擎**: `E:\AI\data\envs\car_agent_env\ai-decision\rag-engine\retrieval.vector_store`
- **依赖**: psycopg2, PostgreSQL + pgvector 扩展, BAAI/bge-large-zh-v1.5 embedding
- **DB 表**: `chunks` (29,150 行, embedding vector(1024), 16 列)

## 已知数据统计（2026-06-29 11:24 验证）

| 关键词 | chunks 数 |
|-------|----------|
| 零跑 | 81 |
| 比亚迪 | 178 |
| 唐 | 45 |
| SUV | 436 |

## 决策规则

| 情况 | 决策 |
|------|------|
| 检索 0 条 | 返回 success=True + 空 results，由调用方决定降级 |
| top_k > 50 | 建议截断到 50（防止 context overflow） |
| query 太短（<2 字）| 强制开启 hybrid |
| hybrid 模式 keyword 命中 0 | 标记 `keyword_no_match=true`（当前实现未标记，由调用方补充） |

## 与 data-agent 包装层关系

- 本 skill 是**底层真实实现**
- `skills/automotive-vector-rag/SKILL.md` 是**data-agent 视角的语义包装层**，调用本 skill 后产出 chunk_id / doc_type / year 等额外元数据

## 版本

- **v2.1**（2026-06-29 11:24 修正 SKILL.md 函数名与真实代码对齐）
- 修复点：原 SKILL.md 写的函数名 `search_chunks` 与真实代码不符，改为 `vector_search`
