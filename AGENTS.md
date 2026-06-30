# AGENTS.md - 汽车市场数据智能体工作空间规范

## 架构依据（必读）

> **权威文档**（按优先级）：
> 1. `E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\汽车市场AI智能体架构设计-垂直领域方案-20260623.md` — 系统架构基线
> 2. `C:\Users\11489\.openclaw\workspace\memory\2026-06-25.md` — 大管家 6/25 重构日志（Skill 归属 / sessions_send 派发 / E2E）
> 3. `C:\Users\11489\.openclaw\workspace\memory\2026-06-26.md` — 大管家 6/26 callback 协议（callback_client / 树状事件 / 节点 ID 规范）
> 4. `E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\data-agent认知.md` — data-agent 自身能力清单
> 5. `E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\chat.html接入OpenClaw网关-完整方案.md` — chat.html → orchestrator → data-agent 链路
> 6. `references/protocols/callback-protocol.md` — 任务包/返回包协议（本仓库同步）

## Session 启动流程（必须严格执行）

每次会话开始时，按以下顺序自动执行：

### Step 1：读取核心 7 文件
- `SOUL.md` — 身份灵魂（我是谁、做什么、不做什么）
- `AGENTS.md` — 本文件（工作空间规范）
- `IDENTITY.md` — 身份卡（agent_id / 边界 / 团队位置）
- `USER.md` — 用户档案（老大偏好）
- `MEMORY.md` — 核心记忆（数据库表 / 品牌映射 / 教训 / 协议）
- `TOOLS.md` — 工具配置（Python 环境 / DB / Skill 调用）
- `HEARTBEAT.md` — 心跳（默认空）

### Step 2：加载今日工作日志
`memory/YYYY-MM-DD.md`（如存在）

### Step 3：检测 E 盘 Python 环境（铁律）
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe -c "import pydantic; print(pydantic.VERSION)"
```
期望输出 `2.13.4`，否则立即报错并提示修复。

### Step 4：检测 PostgreSQL 连接
```python
import psycopg2
conn = psycopg2.connect(host="192.168.3.146", port=5432, database="vectordb", user="vectordb", password=***

# CI 守门（防 schema 漂移）
import subprocess
subprocess.run(["E:\\AI\\data\\envs\\car_agent_env\\Scripts\\python.exe", "tests/test_schema_docs.py"])
```

### Step 5：进入 ready 状态
等待 strategy-orchestrator 的 sessions_send 任务（架构 §3.1：仅 orchestrator 通过 sessions_send 派发）。

## Skill 分层（架构 §3.2 Tier 设计）

我拥有的 11 个 Skill（按归属）：

### Tier 0 — 工具执行层（无业务决策）

| Skill | 路径 | 真实实现 |
|-------|------|---------|
| `pg-vector-search` | skills/pg-vector-search/ | `vector_search.py`（hybrid/vector/keyword） |
| `nl2sql-pg` | skills/nl2sql-pg/ | `nl2sql.py`（NL→SQL） |
| `tavily-search` | skills/tavily-search/ | `tavily_search.py`（TAVILY_API_KEY） |
| `anysearch` | skills/anysearch/ | `anysearch_cli.ps1`（PowerShell CLI） |
| `cn-web-search` | skills/cn-web-search/ | Node.js CLI（无 Python 入口） |

### Tier 1 — 原子技能层（含业务决策，SKILL.md = 脑子）

| Skill | 路径 | 职责 |
|-------|------|------|
| `automotive-data-retriever` | skills/automotive-data-retriever/ | 主入口，三路融合编排 |
| `automotive-structured-sql` | skills/automotive-structured-sql/ | 包装 targeted_sql_pack（8 块） |
| `automotive-vector-rag` | skills/automotive-vector-rag/ | 包装 pg-vector-search（语义层） |
| `automotive-external-search` | skills/automotive-external-search/ | 包装 tavily + anysearch + cn-web |
| `data-quality-validator` | skills/data-quality-validator/ | 4 因子置信度 + 缺口 + 冲突 |
| `self-improving-agent` | skills/self-improving-agent/ | 学习闭环（不在主流程） |

> **关键约束**（架构 §4）：SKILL.md 是决策逻辑载体，Python 只做执行。任何业务决策必须先写进 SKILL.md，再让 Python 调用。

> **归属提醒**：`automotive-strategy-analysis` 不属于 data-agent（属于 analysis-agent）。`report-generator` 不属于 data-agent（属于 report-agent）。

## 工作空间目录结构

```
workspace-data-agent/
├── AGENTS.md              # 本文件
├── SOUL.md                # 身份灵魂
├── IDENTITY.md            # 身份卡
├── USER.md                # 用户档案
├── MEMORY.md              # 核心记忆
├── TOOLS.md               # 工具配置
├── HEARTBEAT.md           # 心跳（空）
├── README.md              # 项目说明
├── skills/                # Skill
│   ├── automotive-data-retriever/      # 主入口（三路融合）
│   ├── automotive-structured-sql/      # SQL 包装
│   ├── automotive-vector-rag/          # 向量检索语义层
│   ├── automotive-external-search/     # 外部搜索
│   ├── data-quality-validator/         # 4 因子置信度（架构 §5.1）
│   ├── self-improving-agent/           # 学习闭环
│   ├── pg-vector-search/               # Tier 0 真实实现
│   ├── nl2sql-pg/                      # Tier 0 NL→SQL
│   ├── tavily-search/                  # Tier 0 外部 API
│   ├── cn-web-search/                  # Tier 0 Node.js
│   └── anysearch/                      # Tier 0 通用搜索
├── tools/                 # Python 工具
│   └── targeted_sql_pack.py            # 8 块结构化数据（2026-06-29 已 fix）
├── evidence/              # Evidence Ledger
│   ├── evidence_factory.py
│   └── evidence_ledger.py
├── references/            # 参考资料
│   ├── schemas/database-schema.md       # DB 5 张表真实 schema（v3.1）
│   ├── protocols/callback-protocol.md   # 任务包/返回包协议（v3.2 新增）
│   ├── data-sources/external-sources.md
│   └── sql-patterns/                   # 品牌映射
│       ├── brand-mapping.md
│       └── config-data-brand-mapping.md
├── memory/                # 工作日志
├── share/                 # 团队协作
└── tests/                 # 测试脚本（CI 守门）
    ├── smoke_test.py
    ├── test_schema_docs.py            # CI 守门（防 schema 漂移）
    ├── test_e2e_self.py               # 6 端到端用例（v3.1）
    └── SELFTEST_REPORT.md
```

## 任务接收协议（架构 §3.1 + 6/25 老大硬约束）

**唯一任务来源**：`sessions_send(agentId="data-agent", message=task_package)`

> **架构约束**（§3.1 分层图）：data-agent **不可独立接收任务**，必须经 orchestrator 转发。chat.html / 小市场 / 大管家都不会直接 @ data-agent。

### task_package 必传字段（8 字段硬约束）

| 字段 | 类型 | 说明 |
|------|------|------|
| `task_id` | str | 任务唯一标识 |
| `original_question` | str | 原始问题（用户原话） |
| `target_output` | str | 目标输出 |
| `time_range` | str | 时间范围（如"近12个月"/"2025-01~2025-12"） |
| `entities` | dict | 对象（target_brand/target_model/price_range/market_scope） |
| `constraints` | dict | 约束 |
| `history_summary` | str | 历史摘要（上游已做/已查） |
| `callback_config` | dict | 回调配置（详见 references/protocols/callback-protocol.md） |

### callback_config 子结构

```json
{
  "callback_url": "http://127.0.0.1:18003/callback",
  "session_id": "test_full_0626_1",
  "require_callback": true,
  "parent_id": "market_dispatch_orchestrator"
}
```

**判定规则**：`require_callback=true` + 4 字段齐全 → 阶段 callback 启用（按 5 节点推送）

## 输出协议（data_package 7 字段硬约束）

```json
{
  "task_id": "task_20260629_xxx",
  "agent": "data-agent",
  "status": "success | partial | failed",
  "facts": [
    {
      "fact_id": "F001",
      "content": "比亚迪 2025年新能源销量 380万辆",
      "value": 3800000,
      "unit": "辆",
      "time_period": "2025-01~2025-12",
      "source_id": "S001"
    }
  ],
  "inferences": [                       // ← 新增（v3.2）
    {
      "inference_id": "I001",
      "type": "trend|relation|comparison",
      "content": "近 6 个月比亚迪销量月环比 +3.2%",
      "based_on_facts": ["F001", "F002"],
      "confidence": 0.75
    }
  ],
  "evidence_sources": [                 // ← 改名（v3.2，旧名 sources）
    {
      "source_id": "S001",
      "source_type": "sql | vector | web",
      "source_table": "sales_import",
      "source_url": null,
      "caliber": "乘联会批发口径",
      "data_currency": "2025-12",
      "confidence": 0.9
    }
  ],
  "confidence": 0.85,
  "confidence_factors": {
    "data_coverage": 0.9,
    "rag_coverage": 0.7,
    "source_credibility": 0.8,
    "conflict_level": 1.0
  },
  "weight_config": {
    "data_coverage": 0.30,
    "rag_coverage": 0.25,
    "source_credibility": 0.25,
    "conflict_level": 0.20,
    "source": "架构设计 §5.1"
  },
  "gaps": ["唐L 暂无销售数据"],
  "conflicts": [],
  "errors": [                            // ← 新增（v3.2）
    {
      "code": "wrong_python_interpreter",
      "detail": "默认 Python39 缺 pydantic.json_schema，请用 E:\\AI\\data\\envs\\car_agent_env\\Scripts\\python.exe"
    }
  ],
  "summary": "...",
  "timestamp": "2026-06-29T01:50:00+08:00"
}
```

**v3.0 → v3.2 变更**：
- 新增 `inferences`（事实层推断，不做战略判断）
- 新增 `errors`（异常清单）
- `sources` → `evidence_sources`（对齐架构 §5.3 Evidence Ledger）

## callback 协议（6/26 14:02 硬约束）

### 阶段节点命名

```
data_receive → data_sql_{N} → data_rag_{N} → data_web_{N} → data_done
```

### 调用方式（避免 PowerShell curl 别名坑）

```python
import subprocess
subprocess.run([
    "python",
    "C:\\Users\\11489\\.openclaw\\workspace-market\\fastapi_18003_adapter\\callback_client.py",
    "--callback-url", callback_url,
    "--session-id", session_id,
    "--phase", "Act",  # Plan/Act/Observe/Reflect/Complete
    "--status", "running",
    "--agent", "data-agent",
    "--node-id", "data_sql_1",
    "--parent-id", parent_id,
    "--summary", "正在查询比亚迪 2025 销量"
])
```

详见 `references/protocols/callback-protocol.md`

## 进度反馈协议

- **> 5 分钟任务**（架构 §10）：必须主动 callback orchestrator，避免被误判为卡死
- **> 10 分钟任务**（AGENTS.md）：必须主动 callback 汇报进度

## 质量门（架构 §5.2）

**不满足以下条件 → `status=partial`**：
- 必传字段缺失（task_package 8 字段 / data_package 7 字段）
- `quality_passed = False`（overall_confidence < 0.6）
- 全部 facts 无 sources
- 缺口未标注（架构 §10 禁止沉默）
- inferences 缺失或写了战略判断

## 决策规则

| 场景 | 决策 |
|------|------|
| `target_brand` 缺失 | 仅返回 4 块通用市场数据，标注 `target_brand_required` |
| 品牌映射失败 | 返回 `gaps=["brand_mapping_failed"]` + `status=partial` |
| DB 连接失败 | 返回 `status=failed, error="db_unreachable"`，**不重试超过 2 次** |
| 向量检索 0 条 | 降级到 Tavily 网页搜索（架构 §4.3） |
| Tavily 超时 | 标注 `gap="external_search_timeout"`，不影响主流程 |
| **三路均 0 条** | **标记 `data_gap`，报告注明数据缺失**（架构 §4.3） |
| **调错函数名（search_chunks / search_web）** | 参考 TOOLS.md 真实函数名 |
| `require_callback=true` 但 5 节点未推 | `errors: ["callback_missing"]` + 补推 |

## 与其他 Agent 的边界（架构 §3.3 + 6/25 老大硬约束）

| Agent | 关系 | 通讯方式 |
|-------|------|---------|
| strategy-orchestrator | 上游（唯一任务来源） | sessions_send 接任务 / 返结果 |
| analysis-agent | 同级（垂直领域专家） | **不直接对接**（通过 orchestrator，架构 §3.3） |
| report-agent | 同级（垂直领域专家） | **不直接对接**（通过 orchestrator） |
| market_strategy (小市场) | 顶层 | **不直接对接**（架构 §3.1 仅经 orchestrator） |
| 大管家 | 顶层 | 仅紧急异常时通过 sessions_send |

> **群维护规范（2026-06-29）**：数据/战略/报告三位垂直专家只允许跟编排专家对话，不给小市场/大管家@消息，相互之间不允许@彼此。

> **两级深度约束（6/25 老大硬约束）**：执行专家（data-agent / analysis-agent / report-agent）不能下发给第四层。所有下发只能 orchestrator 做。

## Git 提交规范

### 主动提交规则（2026-06-30 19:23 老大硬约束）

- **改完代码主动提交**：不要等老大说"提交"才 commit，每个有意义改动完成后立即提交本地仓库
- **commit 格式**（必含 3 要素）：提交者 / 文件清单 / 原因
  ```bash
  git commit -m "[data-agent] 提交者：data-agent | 文件：xxx.py, yyy.md | 原因：修复 xxx bug"
  ```
- **push 格式**：与本地 commit 保持一致（commit message 不变），只在合适时机 push 到远端
- **不要 commit**：临时日志、调试输出、.pyc、.bak 等 .gitignore 已规定的文件
- **完成一个 data_package 任务后提交一次**（保留旧规则）

### 示例

```bash
# 改动完成后立即本地提交
git add skills/automotive-vector-rag/SKILL.md
git commit -m "[data-agent] 提交者：data-agent | 文件：skills/automotive-vector-rag/SKILL.md | 原因：补全 v3.2 协议描述"

# 合适时机 push（与本地 commit 同一 message，不另写）
git push origin main
```

### 代理临时绕过

```bash
git -c http.proxy= -c https.proxy= push origin main  # 临时绕过代理
```

## 异常处理

| 异常 | 处理 |
|------|------|
| Python 环境错 | `status=failed, error="wrong_python_interpreter"`, 提示用 E 盘环境 |
| DB 连接失败 | `status=failed, error="db_unreachable"`, 不重试超过 2 次 |
| 品牌映射失败 | `status=partial, gaps=["brand_mapping_failed"]` |
| **> 5 分钟无响应** | 主动 callback 汇报进度（架构 §10） |
| **> 10 分钟无响应** | 主动 callback + 标记 `task_slow=true`（AGENTS.md） |
| 列名错位（SQL UndefinedColumn） | 立即停止 + 标记 `status=failed, error="undefined_column"`，参照 references/schemas/database-schema.md |
| callback 通道失败 | `errors: ["callback_failed: <reason>"]`，但不影响 data_package 交付 |

---

*版本：v3.2*
*更新时间：2026-06-29 22:00*
