# data-agent 端到端自测报告

**生成时间**: 2026-06-29 15:30
**测试者**: data-agent
**被测**: workspace-data-agent v3.0 全部技能
**测试用例数**: 6（覆盖 5 路径 + 1 缺口场景）

---

## 一、能力与价值复盘

### 1.1 我的能力边界

✅ **能做**：
- PostgreSQL 结构化查询（5 张核心表 / 127 字段）
- 向量知识库检索（29,150 chunks，pg-vector + BAAI/bge-large-zh-v1.5）
- 外部实时搜索（Tavily / AnySearch / CnEVPost 等）
- 交叉验证（多源对比 + 冲突检测）
- 4 因子置信度评分（架构 §5.1 权重 30/25/25/20）
- 数据缺口显式标注（架构 §10）
- 跨表品牌映射（sales_import 全名 ↔ config_data 短名）

❌ **不能做**：
- 战略分析（PEST / Porter / SWOT / 4P）→ analysis-agent
- 报告撰写（Markdown 七步法）→ report-agent
- 决策判断（不替 orchestrator 决定下一步）
- 绕过 orchestrator 独立接任务（架构 §3.1）

### 1.2 我的价值主张

> **"我是质量的看门人。战略分析的数据基础必须可信、可追溯、有置信度。"**

| 价值 | 实现方式 |
|-----|---------|
| 数据准确 | 4 因子置信度 + 多源交叉验证 |
| 来源可追溯 | 每条事实附 source_id（架构 §5.3） |
| 缺口显式 | 不沉默、不伪装 0（架构 §10） |
| 防止漂移 | CI 校验脚本（test_schema_docs.py） |

---

## 二、测试用例设计

| 编号 | 名称 | 路径 | 验证目标 | 期望 | 实际 |
|-----|------|------|---------|------|------|
| 1 | SQL 路径 | targeted_sql_pack | 品牌映射 + 8 块返回 | 8 块全返回 | ✅ 8 块全返回 |
| 2 | 向量路径 | pg-vector-search | hybrid/vector/keyword 三模式 | 三种模式都通 | ✅ hybrid 1.5s / vector 0.6s / keyword 0.9s |
| 3 | Tavily 路径 | tavily_search.py | 实时外部搜索 | API 调用成功 | ✅ 1.2s 返回 3 条 |
| 4 | AnySearch 路径 | anysearch_cli.ps1 | 通用搜索 | 通用搜索可用 | ✅ 6.4s 返回 3 条（修复 Join-Path bug 后） |
| 5 | 三路融合 | SQL + 向量 + 置信度 | 理想汽车综合查询 | overall ≥ 0.6 | ✅ overall=0.805, quality_passed=True |
| 6 | 缺口场景 | DB 查询 | 唐L 显式标注 gap | 显式 0 或单源 | ⚠️ 唐L 实际有 1 条 38882 辆（纠正旧认知） |

---

## 三、测试结果汇总

```
[PASS] smoke_test.py: 5/5 (Python/DB/品牌/向量)
[PASS] test_schema_docs.py: 5/5 表 (127 字段对齐)
[PASS] test_e2e_self.py: 14/14 (6 路径全部调试通畅)
```

**总通过率**: 24/24 = 100%

---

## 四、反思：自测中发现的问题与修复

### 问题 1：anysearch_cli.ps1 在 PowerShell 5.1 下报错 ⚠️ → ✅ 已修复

**症状**：
```
Join-Path : 无法将"System.Object[]"转换为参数"ChildPath"所需的类型"System.String"
所在位置 ...anysearch_cli.ps1:14 字符: 41
+     $envPaths = @(Join-Path $SCRIPT_DIR ".env", Join-Path $SCRIPT_DIR ".." ".env")
```

**根因**：PowerShell 5.1 不支持 `Join-Path` 数组字符串参数（5.1 是按第一个字符串解析，其余被忽略为对象数组）

**修复**：拆成两步
```powershell
# 原代码（5.1 失败）
$envPaths = @(Join-Path $SCRIPT_DIR ".env", Join-Path $SCRIPT_DIR ".." ".env")
# 修复后（5.1/7 都兼容）
$envPath1 = Join-Path $SCRIPT_DIR ".env"
$envPath2 = Join-Path (Join-Path $SCRIPT_DIR "..") ".env"
$envPaths = @($envPath1, $envPath2)
```

**验证**：AnySearch 修复后调用 exit=0，6.4s 返回 3 条 BYD 海豹结果，无 stderr。

### 问题 2：schema doc 字段展示不全 ⚠️ → ✅ 已修复

**症状**：`tests/test_schema_docs.py` 首次运行 FAIL：
```
tech_data: doc 缺少字段 ['CLTC续驶里程', 'WLTC续驶里程', '乘用车级别', ...] (42 个)
config_data: doc 缺少字段 ['CLTC纯电续航里程', 'WLTC纯电续航里程', '价格带', ...] (27 个)
chunks: doc 缺少字段 ['industry_level', 'policy_type', 'region', 'section_title'] (4 个)
```

**根因**：v3.0 doc 只列出每张表的"核心字段"，没列全。CI 校验要求 100% 对齐。

**修复**：把 tech_data (53) / config_data (39) / chunks (16) 全部字段补齐到 doc。sales_import (13) / documents (6) 之前已完整。

**验证**：CI PASS（5 张表 127 字段 100% 对齐）。

### 问题 3：唐L 数据状态认知错误 ⚠️ → ✅ 已纠正

**症状**：MEMORY.md / SOUL.md 里反复提"2026-06-25 唐L 数据缺口" / "唐L 无销售记录"。

**根因**：6 月 25 日查的时候**确实**没有（DB 当时未录入），但**当前（2026-06-29）已有 1 条记录**：通用名称='比亚迪唐L'，销量=38882 辆（应是累计值）。

**修复**：
- 不修改 MEMORY.md 历史教训（保留"曾无数据"的真实记录，教训仍有价值）
- 增加新的发现："截至 2026-06-29，唐L 已录入 1 条累计销量 38882 辆"
- 缺口标注规则保留（架构 §10）：找到 1 条 → `confidence < 0.7, single_source=true`

### 问题 4：config_data 短名厂商映射缺失 ⚠️ → ✅ 已建表

**症状**：之前只有 sales_import 全名 ↔ 短品牌名映射，没有 config_data.厂商（短名）↔ sales_import.企业名称（全名）的映射表。

**根因**：config_data 厂商是"比亚迪"、"理想汽车"、"AITO 问界"等短名（117 个），sales_import 是"比亚迪汽车工业有限公司"等全名（306 个）。

**修复**：新建 `references/sql-patterns/config-data-brand-mapping.md`，覆盖老大常关注的 22 个品牌映射。

---

## 五、与架构文档对齐度验证

| 架构要求 | 当前实现 | 验证 |
|---------|---------|------|
| §3.1 仅经 orchestrator 接收任务 | sessions_send(agentId="data-agent") | ✅ AGENTS.md / SOUL.md 已加约束 |
| §3.3 数据获取边界 | 5 路径 + 不做分析决策 | ✅ SOUL.md "我不做什么" |
| §4 SKILL.md = 脑子 | 5 个核心 SKILL.md v2.1 | ✅ 决策逻辑全在 SKILL.md |
| §4.3 三路融合规则 | 决策表 + 优先级 | ✅ automotive-data-retriever SKILL.md Step 3 |
| §5.1 4 因子权重 30/25/25/20 | 计算正确 | ✅ Test 5.3 overall=0.805 |
| §5.2 quality_passed ≥ 0.6 | 阈值正确 | ✅ data-quality-validator SKILL.md |
| §5.3 Evidence Ledger 标准字段 | evidence_id / source_type / source_table / caliber / data_currency | ✅ data-quality-validator SKILL.md |
| §10 禁止 Python 承载决策 | 5 SKILL.md 是脑子 | ✅ Python 只做执行 |
| §10 缺口必须显式标注 | data_gap / single_source | ✅ Test 6 + 决策规则 |
| §10 长任务 > 5 分钟 callback | 已在 AGENTS.md / SOUL.md | ✅ 异常处理表 |

---

## 六、待办（已全部解决）

| 待办 | 状态 |
|------|------|
| `tests/test_schema_docs.py` CI 校验 | ✅ 已建，PASS |
| `references/sql-patterns/config-data-brand-mapping.md` | ✅ 已建，覆盖 22 个品牌 |
| anysearch_cli.ps1 PowerShell 5.1 兼容性 bug | ✅ 已修 |
| 端到端 E2E 测试用例 | ✅ 6 个用例 + 14 个断言 |

---

## 七、后续改进建议（非阻塞）

1. **CLI Python 包装**：把 anysearch_cli.ps1 调用包成 Python（避免 PowerShell 版本差异）
2. **品牌映射动态化**：config_data 厂商 → sales_import 全名 自动匹配（基于子串 + 阈值）
3. **置信度校准**：跑更多历史查询，看 4 因子预测的 confidence 与实际质量的偏差，调整权重
4. **Conflict 真实注入**：构造同一数据多源 5% 偏差，验证冲突检测逻辑

---

*报告版本：v1.0*
*生成者：data-agent*
*commit: 即将推送*
