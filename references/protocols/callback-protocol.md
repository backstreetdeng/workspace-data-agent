# data-agent 任务包与返回包协议（基于 6/25 架构规范）

> **来源**：`workspace\memory\2026-06-25.md`（大管家 14:30-16:53）"防上下文丢失"的契约

## 一、task_package 任务包（编排专家 → data-agent）

### 必传字段（8 项硬约束）

| 字段 | 类型 | 说明 | data-agent 如何使用 |
|------|------|------|------------------|
| `task_id` | str | 任务唯一标识 | 写入 data_package + callback 节点 |
| `original_question` | str | 原始问题（用户原话） | 保留到 inferences |
| `target_output` | str | 目标输出（如"20-30万SUV市场机会分析"） | 用于 NL2SQL 引导 + 验证覆盖 |
| `time_range` | str | 时间范围（如"近12个月"/"2025-01~2025-12"） | 直接传给 SQL / RAG |
| `entities` | dict | 对象（target_brand/target_model/price_range/market_scope） | 触发品牌动态映射 |
| `constraints` | dict | 约束（如"不能下到第四层"/"需多源验证"） | 决策规则 |
| `history_summary` | str | 历史摘要（上游已做/已查） | 避免重复工作 |
| `callback_config` | dict | 回调配置（见下文） | 触发阶段 callback |

### callback_config 子结构（可选，但推荐）

```json
{
  "callback_config": {
    "callback_url": "http://127.0.0.1:18003/callback",
    "session_id": "test_full_0626_1",
    "require_callback": true,
    "parent_id": "market_dispatch_orchestrator"
  }
}
```

**判定规则**：
- `require_callback=true` + 4 字段齐全 → 阶段 callback 启用
- `require_callback=false` 或缺失 → 跳过 callback 但 `errors` 中说明

---

## 二、data_package 返回包（data-agent → 编排专家）

### 必传字段（7 项，**对比之前 v3.0 多了 inferences 和 errors**）

| 字段 | 类型 | 来源 | 说明 |
|------|------|------|------|
| `task_id` | str | 输入 | 透传 |
| `agent` | str | 固定 | `"data-agent"` |
| `status` | enum | 计算 | `success | partial | failed` |
| `facts` | list[dict] | SQL/向量/网页 | 每条 {fact_id, content, value, unit, time_period, source_id} |
| `inferences` | list[dict] | data-agent LLM 推断 | 基于 facts 的关联/趋势/对比推断（**注意：不做战略判断**） |
| `evidence_sources` | list[dict] | SQL/向量/网页 | 每条 {source_id, source_type, source_table/url, caliber, data_currency, confidence} |
| `confidence` | float | 4 因子 | 0-1 |
| `gaps` | list[str] | 缺口检测 | 架构 §10 不得沉默 |
| `conflicts` | list[dict] | 多源对比 | 偏差 > 5% 的来源对比 |
| `errors` | list[dict] | 异常 | 字段名错位 / Python 环境错 / DB 不可达等 |
| `summary` | str | 综合 | 1-2 句核心结论（不带战略判断） |
| `timestamp` | str | 生成时间 | ISO 8601 |

**对比 v3.0 旧版**：v3.0 用 `sources` 字段命名，新协议改为 `evidence_sources`（对齐架构 §5.3 Evidence Ledger）。

### inferences 字段说明（新增）

data-agent **只做事实层面推断**，不做战略判断：

| 类型 | 示例 | 可做？ |
|------|------|--------|
| 趋势识别 | "近 6 个月比亚迪销量月环比 +3.2%" | ✅ |
| 关联推断 | "比亚迪在 20-30 万 SUV 份额从 8% 升至 12%" | ✅ |
| 对比标注 | "比亚迪 vs 理想：均价差 3 万" | ✅ |
| 战略机会判断 | "比亚迪应进入 X 市场" | ❌ → analysis-agent |
| PEST/Porter/SWOT | — | ❌ → analysis-agent |

---

## 三、callback 协议（data-agent → FastAPI adapter）

### 阶段节点命名（6/26 14:02 规范）

```
data_receive      → data_sql_*    → data_rag_*    → data_web_*    → data_done
                       ↓                ↓                ↓
                 sql_query_started sql_query_done  rag_query_done web_query_done
```

### 节点 ID 规范

| 节点 | ID 模式 | 状态 |
|------|---------|------|
| 任务接收 | `data_receive` | done |
| SQL 查询 | `data_sql_{N}` (N=1..8) | running → done |
| 向量查询 | `data_rag_{N}` (N=1..3) | running → done |
| 网页查询 | `data_web_{N}` (N=1..3) | running → done |
| 任务完成 | `data_done` | done |

### callback_client.py 调用规范

```python
# 推荐方式：调用 helper 避免 PowerShell curl 别名坑
import subprocess
subprocess.run([
    "python",
    "C:\\Users\\11489\\.openclaw\\workspace-market\\fastapi_18003_adapter\\callback_client.py",
    "--callback-url", callback_url,
    "--session-id", session_id,
    "--phase", "Act",  # Phase: Plan/Act/Observe/Reflect/Complete
    "--status", "running",  # running/done/error
    "--agent", "data-agent",
    "--node-id", "data_sql_1",
    "--parent-id", parent_id,
    "--summary", "正在查询比亚迪 2025 销量"
])
```

### 事件 schema（与编排专家对齐）

```json
{
  "session_id": "test_full_0626_1",
  "event": {
    "phase": "Act",
    "stage": "data_sql_1",
    "status": "done",
    "summary": "比亚迪 2025 年销量 3800000 辆（乘联会批发口径）",
    "agent": "data-agent",
    "parent_id": "market_dispatch_orchestrator",
    "timestamp": "2026-06-29T22:00:00+08:00"
  }
}
```

---

## 四、防上下文丢失的契约（架构硬约束）

### data-agent 必须遵守

1. ✅ **必传 8 字段**：接收任务包时，缺失任一字段 → `errors: ["missing_field: original_question"]` + `status=partial`
2. ✅ **返回 7 字段**：返回 data_package 时，facts/inferences/evidence_sources/confidence/gaps/conflicts/errors 必须齐全
3. ✅ **阶段 callback**：`require_callback=true` 时 5 个节点（data_receive/data_sql_*/data_rag_*/data_web_*/data_done）必须 callback
4. ✅ **两级深度**：data-agent **不能** sessions_send 给别的 agent（架构 §3.3）
5. ✅ **缺口显式**：找不到数据时 `gaps: ["数据库无 X 记录"]`，不假装 0（架构 §10）
6. ✅ **证据账本归属**：data-agent 只输出 evidence_sources，证据账本整合由编排专家负责（架构 §3.3）

---

## 五、与编排专家的握手

```
编排专家 → sessions_send(agentId="data-agent", message=task_package_with_callback)
   ↓
data-agent 接收：
   1. 校验必传 8 字段
   2. callback: data_receive done
   3. 决策三路（SQL/向量/网页）
   4. 并行执行 + callback 各节点
   5. 4 因子置信度计算
   6. 构建 data_package（7 字段齐全）
   7. callback: data_done done
   8. sessions_send(agentId="strategy-orchestrator", message=data_package)
```

**超时约定**：
- 单次 SQL ≤ 30s
- 单次向量 ≤ 10s
- 单次 Tavily ≤ 10s
- 总任务 ≤ 60s（超出 → callback 进度 + 编排专家决定是否 abort）

---

*协议版本：v1.0*
*来源：6/25-6/26 memory 大管家留痕 + 编排专家 14:02 协议*
*更新时间：2026-06-29 22:00*
