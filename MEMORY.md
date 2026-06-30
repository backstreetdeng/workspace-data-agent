# MEMORY.md - 数据智能体核心记忆

## 我的能力边界（架构 §3.3 + 6/25 老大硬约束）

✅ **做**（架构授权）：
- 结构化数据库查询（PostgreSQL）
- 向量知识库检索（pg-vector）
- 外部搜索（CnEVPost / 汽车之家 / EV100 / AutoThinker / Tavily）
- 交叉验证（多源对比）
- 置信度评估（4 因子模型，架构 §5.1）
- 数据缺口检测与标注（架构 §10 不得沉默）
- 冲突标记
- 阶段 callback（require_callback=true 时按 data_receive/data_sql_*/data_rag_*/data_web_*/data_done 节点）
- 事实层面 inferences（趋势/关联/对比，**不做战略判断**）

❌ **不做**（架构 §3.3 + §10 + 6/25 老大约束）：
- 战略分析（PEST / Porter / SWOT / 4P）→ analysis-agent
- 报告撰写（Markdown / 七步法）→ report-agent
- 决策判断（不替 strategy-orchestrator 决定下一步）
- 绕过 orchestrator 独立接任务（架构 §3.1）
- 让 Python 承载业务决策（架构 §4：SKILL.md = 脑子）
- **不下发给第四层**（6/25 老大硬约束：执行专家不能 sessions_send 给别人）
- **不整合证据账本**（架构 §3.3：编排专家是 evidence ledger owner）
- **战略层面的 inferences**（如"应进入 X 市场"）→ analysis-agent

## 权威文档（必读）

| 文档 | 路径 | 关键章节 |
|-----|------|---------|
| 架构设计基线 | `E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\汽车市场AI智能体架构设计-垂直领域方案-20260623.md` | §3.1/§3.3/§4/§5/§10 |
| data-agent 认知 | `E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\data-agent认知.md` | 5 张表 / Python 环境 / 外部数据源 |
| chat.html 接入 | `E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\chat.html接入OpenClaw网关-完整方案.md` | §3-4 |
| **6/25 重构日志** | `C:\Users\11489\.openclaw\workspace\memory\2026-06-25.md` | 14:30 Skill 归属 / 14:55 sessions_send 派发 / 16:53 E2E / 19:41 Fix1+Fix2 |
| **6/26 callback 协议** | `C:\Users\11489\.openclaw\workspace\memory\2026-06-26.md` | 10:40 callback_client / 14:02 树状事件协议 / 15:12 callback 字段注入 |
| **6/25 老大原稿** | `D:\2024年度工作日志和备忘录\数字化转型产品\4.0 同事组\5.0 邓\2026\7.0 智能体日志\0625\推荐架构-认知.txt` + `智能体化步骤.md` | 架构认知 / 智能体化 5 步路径 |
| **任务包/返回包协议** | `references/protocols/callback-protocol.md` | 8 必传 + 7 返回 + 节点命名 |

## 必传参数（任务包协议）

**8 字段硬约束**（架构硬约束 + 6/25 老大契约）：
- `task_id` - 任务唯一标识
- `original_question` - 原始问题（用户原话）
- `target_output` - 目标输出
- `time_range` - 时间范围
- `entities` - 对象（target_brand/target_model/price_range/market_scope）
- `constraints` - 约束
- `history_summary` - 历史摘要
- `callback_config` - 回调配置（callback_url/session_id/require_callback/parent_id）

**target_brand 或 target_industry**（必传其一，否则只返回 4 块通用市场数据）

## 5 大铁律

### 铁律 1：Python 运行时
必须用 `E:\AI\data\envs\car_agent_env\Scripts\python.exe`，默认 Python39 会失败（缺 `pydantic.json_schema`）。

### 铁律 2：品牌动态映射
短品牌名 ≠ DB 企业名称，必须先 `SELECT DISTINCT 企业名称` 后做动态映射。
- sales_import.企业名称 = **全名**（如"比亚迪汽车工业有限公司"）
- config_data.厂商 = **短名**（如"比亚迪"），需单独维护映射表

### 铁律 3：字段先 verify（2026-06-29 教训）
`sales_import` **没有** `产品名称` / `车型` / `月份` / `价格` 列！做车型特定查询前必须先 verify schema（`references/schemas/database-schema.md`）。
**CI 守门**：`tests/test_schema_docs.py` 已建（5 张表 127 字段 100% 对齐）

### 铁律 4：缺口显式标注（架构 §10）
找不到数据时返回 `data_gap`，不允许伪装 0。找到 1 条也要标注 `single_source=true`。

### 铁律 5：多源验证（架构 §5.1）
关键数据至少 1 主源 + 1 验证源，置信度才 ≥ 0.7。

## 数据库表行数（2026-06-29 验证）

| 表 | 行数 | 列数 |
|----|------|------|
| sales_import | 22,502 | 13 |
| tech_data | 2,455 | 53 |
| config_data | 3,463 | 39 |
| documents | 186 | 6 |
| chunks | 29,150 | 16 |

**销售日期范围**: 202501~202602（14 个月，整数 YYYYMM）
**sales_import 关键列**: 销售日期 / 产品型号 / 企业名称 / 产品商标 / 技术类型 / 乘用车细分 / 通用名称 / 整备质量 / 总质量 / 轴距 / 车型级别 / 销量
**config_data 厂商**：用的是**短名**（如 "比亚迪"），不是 sales_import.企业名称 的全名

## 关键词命中验证（2026-06-29 11:24）

| 关键词 | chunks 数 |
|-------|----------|
| 零跑 | 81 |
| 比亚迪 | 178 |
| 唐 | 45 |
| SUV | 436 |

## 验证过的品牌映射（短名 → DB 全名）

| 短名 | DB 企业名称 | 置信度 |
|-----|------------|--------|
| 比亚迪 | 比亚迪汽车工业有限公司 / 比亚迪汽车有限公司 | 0.95 |
| 理想 | 北京理想汽车有限公司 / 重庆理想汽车有限公司 | 0.90 |
| 赛力斯 / 问界 | 赛力斯汽车有限公司 / 赛力斯汽车（湖北）有限公司 | 0.85 |
| 零跑 | 浙江零跑科技股份有限公司 / 零跑汽车有限公司 | 待验证 |
| 特斯拉 | 特斯拉汽车（北京）有限公司 / 特斯拉（上海）有限公司 | 待验证 |

## 4 因子置信度模型（架构 §5.1）

```python
overall_confidence = (
    data_coverage      * 0.30 +   # 销量+配置+政策+舆情覆盖
    rag_coverage       * 0.25 +   # 向量检索覆盖
    source_credibility * 0.25 +   # 来源可信度
    conflict_level     * 0.20     # 冲突程度
)
# quality_passed = (overall_confidence >= 0.6)  # 架构 §5.2 硬阈值
```

## callback 节点命名规范（6/26 14:02）

```
data_receive → data_sql_{N} → data_rag_{N} → data_web_{N} → data_done
```

阶段 callback 必须按这 5 类节点推送（详见 `references/protocols/callback-protocol.md`）。

## Skill 归属（6/25 14:30 大管家分配）

| Skill | 路径 | 归属 |
|-------|------|------|
| `pg-vector-search` | skills/pg-vector-search/ | ✅ data-agent |
| `nl2sql-pg` | skills/nl2sql-pg/ | ✅ data-agent |
| `tavily-search` | skills/tavily-search/ | ✅ data-agent |
| `anysearch` | skills/anysearch/ | ✅ data-agent |
| `automotive-data-retriever` | skills/automotive-data-retriever/ | ✅ data-agent（Tier 1 主入口） |
| `automotive-structured-sql` | skills/automotive-structured-sql/ | ✅ data-agent（Tier 1） |
| `automotive-vector-rag` | skills/automotive-vector-rag/ | ✅ data-agent（Tier 1） |
| `automotive-external-search` | skills/automotive-external-search/ | ✅ data-agent（Tier 1） |
| `data-quality-validator` | skills/data-quality-validator/ | ✅ data-agent（Tier 1） |
| `self-improving-agent` | skills/self-improving-agent/ | ✅ data-agent（学习闭环） |
| `cn-web-search` | skills/cn-web-search/ | ⚠️ Node.js 实现（AutoThinker/汽车之家备选） |

**`automotive-strategy-analysis` 不属于 data-agent**（属于 analysis-agent），不要再误复制过来。

## 历史关键教训

### 2026-06-25：Python 环境错误导致首次 E2E 失败
- **现象**：`retrieval.vector_store` 导入失败，缺 `pydantic.json_schema`
- **根因**：默认 Python39
- **修复**：切换到 `E:\AI\data\envs\car_agent_env\Scripts\python.exe`
- **教训**：skills/ 下的所有脚本必须硬编码 E 盘 Python

### 2026-06-25：品牌硬匹配返回 0 条
- **现象**：`WHERE 企业名称='比亚迪'` 返回 0
- **根因**：DB 存的是全称（比亚迪汽车工业有限公司）
- **修复**：动态 `brand → enterprise` 映射
- **教训**：不要假设任何短品牌名直接匹配

### 2026-06-25：唐L 数据缺口
- **现象**：唐L 无销售记录
- **处理**：显式标注 `gap`，不假装 0
- **2026-06-29 更新**：唐L 实际已录入 1 条累计销量 38882 辆（纠正之前印象）
- **教训**：缺口是真实信号，不应沉默（架构 §10）

### 2026-06-25 14:30：Skill 归属大管家分配
- 把 nl2sql-pg/pg-vector-search/tavily-search/anysearch 从 workspace-market 复制到 workspace-data-agent
- data-agent 真正拥有 4 个底层 Skill + 5 个 Tier 1 SKILL.md
- report-generator 不再属于 data-agent

### 2026-06-25 14:55：Python wrapper 主脑降级
- `agent_tool_adapters.py` 改为只发 sessions_send 任务包
- `skill_strategy_adapter.py` 改为产生 controlled dispatch steps
- `targeted_sql_pack.py`（orchestrator 副本）改为 deprecated shim
- **Python 不能再承载业务决策**

### 2026-06-25 16:53：E2E 链路验证
- `strategy-orchestrator -> data-agent -> analysis-agent -> report-agent -> strategy-orchestrator -> market_strategy`
- 6/25 19:41 Fix1+Fix2 验证：brand dynamic mapping + final return to market_strategy

### 2026-06-26 10:40：callback_client.py 落地
- 给智能体一个 Python helper 发回调，避免 PowerShell curl 别名坑
- `/callback` 兼容标准格式 + 旧式扁平格式

### 2026-06-26 14:02：树状事件协议
- `substep_created` / `substep_updated` + `parent_id` 父子节点
- 节点 ID 规范：data_receive / data_sql_N / data_rag_N / data_web_N / data_done
- data-agent 接收 `require_callback=true` + callback_config 时必须主动 callback

### 2026-06-29：工作空间大清理
- 删 `agents/`（~310KB 错位内容）+ `python_wrapper/` + `skills/automotive-strategy-analysis/` + `tools/` 错位工具
- 112 → 57 文件，869KB → 295KB
- 教训：agent 仓库之间不能相互倾倒代码

### 2026-06-29：SQL 列名错位（阻塞 E2E）
- **现象**：`tools/targeted_sql_pack.py` 用 fab 英文列名（sales_month/company_name/model_name/sales）
- **真实列名**：销售日期/企业名称/通用名称/销量
- **修复**：老大提供 `targeted_sql_pack_new.py`（commit f1ac7b3）
- **教训**：任何 schema 假设必须先用 `information_schema.columns` 在线 verify

### 2026-06-29：ROOT 7 md 被污染（早期）
- **现象**：workspace-data-agent ROOT 7 md 全是"汽车市场战略分析师"内容
- **根因**：data-agent 创建仓库时直接复制了分析专家的 SOUL/AGENTS/MEMORY
- **教训**：创建仓库时要确认内容真实性

### 2026-06-29：TOOLS.md / schema.md / SKILL.md 漂移
- **现象**：TOOLS.md 函数名错位（search_chunks/search_web/nl2sql_pg.nl2sql/cn_search）；schema doc 列名错位（说"月份/车型/价格"）
- **修复**：v3.0 重写（commit 0845987）
- **教训**：文档必须与代码/DB 真实 schema 同步

### 2026-06-29：架构对齐 v3.0 升级
- 老大分享 3 份架构文档（架构设计 + chat.html 接入 + data-agent 认知）
- 5 个核心 SKILL.md 升级到 v2.1（对齐架构 §3.3/§4/§5.1/§5.2/§10）
- quality_passed 阈值 0.5 → 0.6 对齐架构 §5.2

### 2026-06-29 15:30：v3.1 自测闭环
- smoke 5/5 + schema 5/5 + e2e 14/14 = 24/24 PASS
- 建 CI 校验 `tests/test_schema_docs.py`（防 schema 漂移）
- 建 `references/sql-patterns/config-data-brand-mapping.md`（22 品牌映射）
- 修 `anysearch_cli.ps1` PowerShell 5.1 Join-Path 数组 bug
- 意外发现：唐L 实际有 1 条 38882 辆记录

### 2026-06-29 22:00：基于 6/25-6/26 memory 同步 v3.2
- 读 `workspace\memory\2026-06-25.md` 和 `2026-06-26.md`
- 补充 callback 协议（5 节点命名 + callback_config 必传字段）
- 补充任务包 8 字段硬约束 + data_package 7 字段返回（新增 inferences、errors、evidence_sources）
- 明确 Skill 归属（4 个底层 + 5 个 Tier 1 + 1 Node.js）
- 明确"两级深度"约束（data-agent 不下发到第四层）
- 明确 inferences 只做事实层推断，不做战略判断
- 新增 `references/protocols/callback-protocol.md`


### 2026-06-30 19:23：Git 主动提交硬约束（老大原话）

- **场景**：老大花了半天让全员把各自工作空间除 .gitignore 外的文件强制 commit + push 到远端
- **新规则（永久约束）**：
  - 后续各自改完代码，**主动**提交到本地仓库，**不要等**老大说"提交"
  - commit 格式必须含 3 要素：**提交者**（因为都是老大账号） / **文件清单** / **原因**
  - push 格式保持本地 commit 一致（同一 message，不另写）
- **落地**：已写入 AGENTS.md `## Git 提交规范 → ### 主动提交规则（2026-06-30 19:23 老大硬约束）`
- **当前远端状态**：`c447a79 P0: 2026-06-30 16:40 老大指令 - 全量同步工作空间 (data-agent 75 文件 / 12639 行)` + `05a2bc6 init: 清空远程仓库`

## 当前版本

- **v3.3**（2026-06-30 19:23 老大硬约束：Git 主动提交规范）
- 涵盖：6/25-6/29 三轮同步（协议对齐 + 自测闭环 + 主动提交硬约束）
- 状态：可承接编排专家真实任务（含 callback + 主动 git commit）

## 团队协作

| 角色 | 关系 | 通讯方式 |
|-----|------|---------|
| 上游（唯一任务来源） | strategy-orchestrator（架构 §3.1 sessions_send） | sessions_send 接 task_package（含 callback_config） |
| 下游（结果交付） | strategy-orchestrator（sessions_send 回 data_package） | sessions_send 回 7 字段 data_package |
| 平行（不直接对接） | analysis-agent / report-agent（架构 §3.3） | 通过 orchestrator 转发 |
| 顶层 | market_strategy（大管家重构后小市场是 router + 最终解释者） | 通过 orchestrator 转发 |

## 我的常用 Skill

- **automotive-data-retriever**（主入口，Tier 1）
- **automotive-structured-sql**（Tier 1，包装 targeted_sql_pack）
- **automotive-vector-rag**（Tier 1，包装 pg-vector-search）
- **automotive-external-search**（Tier 1，包装 tavily / anysearch）
- **data-quality-validator**（Tier 1，4 因子置信度）

## 与 data-agent 上次成功的 E2E 对比

- **task_id**: `e2e-fix2-market-return-20260625-1941`
- **场景**: BYD 唐L 20-30万 SUV 市场机会分析
- **8 块全部返回**: market_overview=1, monthly_trend=12, yoy_change=2, competitor_share=12, target_brand_performance=2, model_contribution=12, power_mix=2, price_and_config=12
- **置信度**: 0.65
- **缺口**: 唐L 无销售记录（显式标注）
- **结论**: BYD 在 20-30万 SUV 市场有结构性机会，但唐L 需要差异化定位

---

*版本：v3.2*
*更新时间：2026-06-29 22:00*
