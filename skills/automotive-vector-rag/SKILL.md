# automotive-vector-rag（向量知识库检索 - data-agent 语义层）

## 身份与能力边界

- **定位**：data-agent 视角的**语义包装层**，封装 `pg-vector-search`，产出 data-agent 标准 chunk 格式
- **触发条件**：`automotive-data-retriever` 判定需要向量路径时调用
- **能力上限**：返回 top_k 相关 chunks + 相似度分数 + 来源元数据
- **能力下限**：不做语义理解扩展（除非开启 LLM rephrase）；不替代 `pg-vector-search`

## 与 pg-vector-search 的关系

| 层级 | Skill | 提供 |
|------|-------|------|
| 真实实现 | `pg-vector-search` | `vector_search()` / `search_by_intent()` / `skill_main()` |
| 语义包装（data-agent 视角） | `automotive-vector-rag`（本 skill） | 调用 pg-vector-search，补齐 doc_type / year / chunk_id 等元数据 |

> **重要**：本 skill **没有独立 Python 实现**，只是 SKILL.md 协议层。所有调用最终走 `skills/pg-vector-search/vector_search.py`。

## 真实调用方式（2026-06-29 修正）

```python
import sys
sys.path.insert(0, "skills/pg-vector-search")
from vector_search import vector_search  # ✅ 真实函数名（不是 search_chunks）

def rag_search(query, top_k=10, hybrid=True, filter=None):
    """data-agent 视角的向量检索包装"""
    result = vector_search(
        query=query,
        top_k=top_k,
        search_mode="hybrid" if hybrid else "vector",
        brand=filter.get("brand") if filter else None,
        source=filter.get("source") if filter else None,
    )
    if not result.get("success"):
        return {"skill": "automotive-vector-rag", "chunks": [], "gaps": [result.get("error", "unknown")]}

    chunks = []
    for i, r in enumerate(result.get("results", []), 1):
        chunks.append({
            "chunk_id": f"C{i:03d}",
            "content": r.get("content", ""),
            "source_doc_id": None,  # pg-vector-search 当前未返回，需后续从 document_id 补
            "doc_title": r.get("file_name", ""),
            "doc_type": r.get("source", ""),
            "year": None,  # publish_date 为空时无法解析
            "similarity_score": r.get("score", 0.0),
            "brand": r.get("brand", ""),
            "keyword_hit": [query] if query else [],
        })
    return {
        "skill": "automotive-vector-rag",
        "chunks": chunks,
        "total_hits": result.get("count", 0),
        "search_mode": "hybrid" if hybrid else "vector",
        "query_used": query,
        "gaps": [],
    }
```

## 输入参数

```python
{
    "query": "比亚迪 唐 销量",
    "top_k": 10,                # 默认 10，建议 ≤ 50
    "hybrid": True,             # 关键词 + 向量混合（推荐）
    "filter": {                 # 可选
        "brand": "比亚迪",
        "source": "数据中心",
        "year": 2025
    }
}
```

## 输出格式

```json
{
  "skill": "automotive-vector-rag",
  "chunks": [
    {
      "chunk_id": "C001",
      "content": "...",
      "source_doc_id": "D123",
      "doc_title": "新能源分阶段车型及投放节奏对销量影响分析.md",
      "doc_type": "数据中心",
      "year": 2025,
      "similarity_score": 0.7251,
      "brand": "比亚迪, 特斯拉, 理想, 问界",
      "keyword_hit": ["比亚迪", "唐"]
    }
  ],
  "total_hits": 10,
  "search_mode": "hybrid",
  "query_used": "比亚迪 唐 销量",
  "gaps": []
}
```

## 决策规则

| 情况 | 决策 |
|------|------|
| 检索 0 条 | 降级到 Tavily 网页搜索（前提是 query 是新闻类） |
| top_k > 50 | 截断到 50（防止 context overflow） |
| query 太短（<2 字）| 强制开启 hybrid |
| query 太长（>200 字）| 截断到 200 字 |
| hybrid=True 但 keyword 命中 0 | 标记 `keyword_no_match=true` |
| publish_date 为空 | year 字段填 None，不假装 |

## 质量门

- 至少 1 条 chunk 相似度 ≥ 0.6 → confidence ≥ 0.7
- source_doc_id 都已 verify → confidence ≥ 0.8
- 不满足 → `confidence` 标注 low，`gaps=["low_confidence"]`

## 与其他 Skill 的交接

- **上游**：`automotive-data-retriever`
- **下游**：返回给 `data-retriever`，再交给 `data-quality-validator`
- **底层依赖**：`pg-vector-search`（真实向量检索实现）

## 已知数据统计（2026-06-29 11:24 验证）

| 关键词 | chunks 数 |
|-------|----------|
| 零跑 | 81 |
| 比亚迪 | 178 |
| 唐 | 45 |
| SUV | 436 |

## v2.1 修正记录

- 2026-06-29 11:24：原 SKILL.md 引用 `from skills.pg_vector_search.vector_search import search_chunks` 是错的（该函数不存在）。改为真实函数 `vector_search`，并明确本 skill 为语义包装层而非独立实现
- 2026-06-29 11:24：补充 `rag_search()` 函数原型作为标准包装模板
- 2026-06-29 11:24：`source_doc_id` / `year` 字段说明当前实现不一定能填齐，标注为"需后续从 document_id 补"

---

*版本：v2.1*
*更新时间：2026-06-29 11:24*
