# automotive-data-retriever（数据检索主入口）

## 身份与能力边界

- **定位**：data-agent 的**主入口 Skill**，负责**三路融合**（SQL / 向量 / 网页）的编排决策
- **触发条件**：strategy-orchestrator 通过 `sessions_send` 派发任务包，且任务需要数据支撑
- **能力上限**：根据 `task_package` 自动决定走哪些路，返回结构化 `data_package`（7 字段），按需推送阶段 callback
- **能力下限**：
  - 不分析、不做报告、不做决策、不可独立接收任务（必须经 orchestrator）
  - **不下发给第四层**（6/25 老大硬约束）
  - **不做战略层面的 inferences**

> **权威依据**：
> - 架构设计：`E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\汽车市场AI智能体架构设计-垂直领域方案-20260623.md` §3.3/§4.3
> - 重构日志：`C:\Users\11489\.openclaw\workspace\memory\2026-06-25.md` §14:30-16:53
> - callback 协议：`C:\Users\11489\.openclaw\workspace\memory\2026-06-26.md` §14:02 + 本仓库 `references/protocols/callback-protocol.md`

## 执行流程（v3.2 增强：阶段 callback）

### Step 1：解析任务包（8 必传字段 + callback_config）

```python
from task_package import parse_task_package

task = parse_task_package(task_package_raw)
required_fields = ["task_id", "original_question", "target_output",
                   "time_range", "entities", "constraints",
                   "history_summary", "callback_config"]
missing = [f for f in required_fields if not task.get(f)]
if missing:
    return {"status": "partial", "errors": [{"code": "missing_field", "detail": m} for m in missing]}

# callback_config 子结构
cb = task["callback_config"]
require_cb = cb.get("require_callback", False)
callback_url = cb.get("callback_url")
session_id = cb.get("session_id")
parent_id = cb.get("parent_id")
```

### Step 2：阶段 callback — data_receive done（若 require_cb）

```python
from callback_client import send_callback

if require_cb and callback_url:
    send_callback(
        callback_url=callback_url,
        session_id=session_id,
        phase="Act",
        status="done",
        agent="data-agent",
        node_id="data_receive",
        parent_id=parent_id,
        summary=f"data-agent 接收任务 {task['task_id']}",
    )
```

### Step 3：品牌动态映射（如需要）

```sql
SELECT DISTINCT 企业名称 FROM sales_import WHERE 企业名称 LIKE '%<brand>%';
```

### Step 4：决策三路（对齐架构 §4.3）

| 场景 | SQL | 向量 | 网页 | callback 节点 |
|------|-----|------|------|--------------|
| 销量 / 份额 / 价格 | ✅ | - | - | data_sql_N |
| 政策 / 报告 / 分析 | - | ✅ | - | data_rag_N |
| 实时新闻 / 上市 / 舆情 | - | - | ✅ | data_web_N |
| 品牌整体画像 | ✅ | ✅ | - | data_sql_N + data_rag_N |
| 价格带 + 配置 + 口碑 | ✅ | - | ✅ | data_sql_N + data_web_N |
| **综合分析**（默认） | ✅ | ✅ | ✅ | 三路并行 callback |

### Step 5：调用子 Skill（并行 + 阶段 callback）

```python
import concurrent.futures

def sql_block_with_cb(block_idx, query_plan):
    if require_cb:
        send_callback(..., node_id=f"data_sql_{block_idx}", status="running", summary="...")
    result = run_structured_sql(query_plan)
    if require_cb:
        send_callback(..., node_id=f"data_sql_{block_idx}", status="done", summary=f"...")
    return result

def rag_block_with_cb(idx, query):
    if require_cb:
        send_callback(..., node_id=f"data_rag_{idx}", status="running", summary="...")
    result = run_vector_rag(query)
    if require_cb:
        send_callback(..., node_id=f"data_rag_{idx}", status="done", summary=f"...")
    return result

def web_block_with_cb(idx, query):
    if require_cb:
        send_callback(..., node_id=f"data_web_{idx}", status="running", summary="...")
    result = run_external_search(query)
    if require_cb:
        send_callback(..., node_id=f"data_web_{idx}", status="done", summary=f"...")
    return result

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
    sql_fut = ex.submit(sql_block_with_cb, 1, query_plan)
    rag_fut = ex.submit(rag_block_with_cb, 1, query)
    web_fut = ex.submit(web_block_with_cb, 1, query)
    sql_result = sql_fut.result()
    rag_result = rag_fut.result()
    web_result = web_fut.result()
```

### Step 6：交叉验证 + 推断（事实层）

```python
# 1. 交叉验证：多源对比同一数据
cross_validation(sql_result, rag_result, web_result)

# 2. 事实层 inferences（趋势/关联/对比，**不做战略判断**）
inferences = generate_fact_inferences(facts, allowed_types=["trend", "relation", "comparison"])
```

### Step 7：调用 data-quality-validator

- 计算 4 因子置信度（架构 §5.1 权重 30/25/25/20）
- 标注 gaps（架构 §10 禁止沉默）
- 标注 conflicts

### Step 8：构建 data_package（7 字段硬约束）

```python
data_package = {
    "task_id": task["task_id"],
    "agent": "data-agent",
    "status": "success" if quality_passed else "partial",
    "facts": facts,                            # 必填
    "inferences": inferences,                  # 必填（v3.2 新增）
    "evidence_sources": evidence_sources,      # 必填（v3.2 改名）
    "confidence": overall_confidence,
    "confidence_factors": factors,
    "weight_config": {"data_coverage": 0.30, ...},
    "gaps": gaps,
    "conflicts": conflicts,
    "errors": errors,                          # 必填（v3.2 新增）
    "summary": summary,
    "timestamp": now_iso(),
}
```

### Step 9：阶段 callback — data_done done（若 require_cb）

```python
if require_cb and callback_url:
    send_callback(
        callback_url=callback_url,
        session_id=session_id,
        phase="Complete",
        status="done",
        agent="data-agent",
        node_id="data_done",
        parent_id=parent_id,
        summary=f"data_package 构建完成: status={data_package['status']}, confidence={data_package['confidence']}",
    )
```

### Step 10：sessions_send 返回 strategy-orchestrator

```python
sessions_send(agentId="strategy-orchestrator", message=data_package)
```

## 决策规则（v3.2 增强）

| 情况 | 决策 |
|------|------|
| `target_brand` 缺失 | SQL 走 4 块通用模式，向量走宽查询 |
| `time_range` 缺失 | 默认 "近12个月" |
| `target_output` 缺失 | 自动推断（销量/份额/价格/配置） |
| `history_summary` 缺失 | 不阻塞但 `errors` 警告 |
| 必传字段缺失 | `errors: [missing_field: X]` + `status=partial` |
| SQL 返回 0 条 | 降级到向量路，发出警告（架构 §4.3 质量门） |
| 向量返回 0 条 | 降级到 Tavily 网页搜索 |
| **三路均 0 条** | 标记 `data_gap`，报告注明数据缺失（架构 §4.3 + §10） |
| 关键数据只有 1 个源 | `confidence < 0.7, single_source=true` |
| **长任务 > 5 分钟** | 按架构 §10，必须 callback 阶段进度给 orchestrator |
| **task > 10 分钟** | 必须主动 callback 汇报进度（AGENTS.md 异常处理） |
| **callback 通道失败** | `errors: ["callback_failed: <reason>"]`，但不影响 data_package 交付 |

## 输出格式

返回 `data_package`（7 字段硬约束，详见 AGENTS.md §输出协议）。

## 质量门（架构 §5.2 + v3.2 增强）

- ✅ 至少 1 个事实 + 至少 1 个来源
- ✅ `overall_confidence >= 0.6`（架构 §5.2 阈值）
- ✅ 必传字段已传（task_package 8 字段 / data_package 7 字段）
- ✅ gaps 和 conflicts 都已显式标注（架构 §10）
- ✅ **5 节点 callback 全部推送**（若 require_callback=true）
- ✅ **inferences 只做事实层**（trend/relation/comparison，不含战略判断）
- ❌ 不满足 → `status=partial`

## 与其他 Skill 的交接

- **上游**：`strategy-orchestrator`（架构 §3.1 系统分层图，sessions_send 派发）
- **下游调用**：`automotive-structured-sql` / `automotive-vector-rag` / `automotive-external-search` / `data-quality-validator`
- **callback**：`fastapi_18003_adapter.callback_client`（避免 PowerShell curl 别名坑，6/26 10:40）
- **返回**：`sessions_send(agentId="strategy-orchestrator", message=data_package)`（不直接对接小市场 / 大管家 / 其他 agent，AGENTS.md §与其他 Agent 的边界）

## v3.2 修正记录

- 2026-06-29 22:00：基于 6/25-6/26 大管家 memory 同步，添加 callback 协议 5 节点（data_receive/data_sql_N/data_rag_N/data_web_N/data_done）+ task_package 8 字段硬约束 + data_package 7 字段（新增 inferences、errors，sources→evidence_sources）
- 2026-06-29 11:24：v2.1 quality_passed 阈值 0.5→0.6 对齐架构 §5.2；三路融合规则细化
- 2026-06-29：v2.0 初始版本（Tier 1 主入口）

---

*版本：v3.2*
*更新时间：2026-06-29 22:00*
