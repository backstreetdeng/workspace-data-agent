# data-quality-validator（数据质量验证）

## 身份与能力边界

- **定位**：对三路检索结果做**质量评分 + 缺口检测 + 冲突标记**
- **触发条件**：`automotive-data-retriever` 拿到三路结果后调用
- **能力上限**：计算 4 因子置信度，输出 evidence 清单
- **能力下限**：不做事实核查（除非开启 LLM verify）、不做最终报告、不做战略分析

> **权威依据**：`E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\汽车市场AI智能体架构设计-垂直领域方案-20260623.md` §5（P3 质量体系）

## 执行流程

### Step 1：接收三路结果
```python
{
    "sql_results": {...},       # 来自 automotive-structured-sql
    "vector_results": {...},    # 来自 automotive-vector-rag
    "external_results": {...},  # 来自 automotive-external-search
    "brand_mapping": {...},     # 品牌映射结果
    "task_id": "...",
}
```

### Step 2：4 因子置信度计算（权重对齐架构设计 §5.1）

#### 因子 1：数据覆盖 data_coverage（权重 30%）
| 条件 | 分数 |
|------|------|
| 销量+配置+政策+舆情 都有（4 路） | 1.0 |
| 销量+配置+政策（3 路） | 0.85 |
| 仅销量数据 | 0.6 |
| 仅政策/报告（向量） | 0.5 |
| 无结构化数据 | 0.3 |
| 全部无数据 | 0.0 |

#### 因子 2：RAG 覆盖 rag_coverage（权重 25%）
| 条件 | 分数 |
|------|------|
| > 10 条相关 chunk | 1.0 |
| 5-10 条 | 0.7 |
| < 5 条 | 0.4 |
| 0 条 | 0.0 |

#### 因子 3：来源可信度 source_credibility（权重 25%）
| 来源 | 分数 |
|------|------|
| 政府/监管文件（MIIT / 国务院） | 1.0 |
| 乘联会 / 中汽协 | 0.95 |
| CnEVPost / EV100 | 0.85 |
| 汽车之家 / 太平洋汽车 | 0.80 |
| AutoThinker | 0.75 |
| 社交媒体/论坛 | 0.50 |
| 未知来源 | 0.30 |

#### 因子 4：冲突程度 conflict_level（权重 20%）
| 条件 | 分数 |
|------|------|
| 无冲突 | 1.0 |
| 2 个来源冲突 | 0.6 |
| > 2 个来源冲突 | 0.3（需人工判断） |

### Step 3：综合置信度
```python
overall_confidence = (
    data_coverage * 0.30 +
    rag_coverage * 0.25 +
    source_credibility * 0.25 +
    conflict_level * 0.20
)
# 取值范围 [0.0, 1.0]，保留 3 位小数
```

### Step 4：质量门判定（对齐架构设计 §5.2）

```python
quality_passed = (
    overall_confidence >= 0.6      # 架构 §5.2 硬阈值
    and evidence_ledger_complete   # 每条结论有来源
    and no_unresolved_conflicts    # 无未解决冲突
)
```

### Step 5：缺口检测（架构 §10 禁止"沉默等待"原则 → 必须显式标注）
对每个事实检查：
- 时间口径是否明确？（年/月/累计）
- 单位是否统一？（辆/万辆/百分比）
- 来源是否标记？（source_id / url）
- 是否所有必填字段都有？

无则加入 `gaps[]`（不沉默，不假装 0）。

### Step 6：冲突标记
对比多源对同一事实的描述：
- 完全一致 → 不标记
- 偏差 < 5% → `minor_conflict`（不阻塞交付）
- 偏差 5-15% → `conflict`, 标注 `source_a=..., source_b=...`
- 偏差 > 15% → `major_conflict`, `need_human_review=true`

### Step 7：返回 quality_report

## 决策规则（与架构 §5.2 quality_passed 对齐）

| overall_confidence | quality_passed | 状态 |
|--------------------|----------------|------|
| ≥ 0.6 | True | `status=success` |
| 0.5 - 0.6 | False | `status=partial`，可交付但需风险提示 |
| < 0.5 | False | `status=failed`，不交付，建议重试或人工 |

## 输出格式

```json
{
  "skill": "data-quality-validator",
  "quality_passed": true,
  "overall_confidence": 0.75,
  "confidence_factors": {
    "data_coverage": 0.9,
    "rag_coverage": 0.7,
    "source_credibility": 0.8,
    "conflict_level": 0.6
  },
  "weight_config": {
    "data_coverage": 0.30,
    "rag_coverage": 0.25,
    "source_credibility": 0.25,
    "conflict_level": 0.20,
    "source": "汽车市场AI智能体架构设计-垂直领域方案-20260623 §5.1"
  },
  "gaps": ["唐L 暂无销售数据"],
  "conflicts": [
    {
      "topic": "比亚迪 2025年总销量",
      "source_a": {"source_id": "S001", "value": 3800000},
      "source_b": {"source_id": "S003", "value": 3650000},
      "deviation_pct": 4.1,
      "severity": "minor_conflict"
    }
  ],
  "evidence": [
    {
      "evidence_id": "E001",
      "content": "比亚迪 2025年新能源销量 380万辆",
      "source_id": "S001",
      "source_type": "sql",
      "source_table": "sales_import",
      "caliber": "乘联会批发口径",
      "data_currency": "2025-12",
      "confidence": 0.9,
      "tags": ["销量", "比亚迪", "新能源"]
    }
  ],
  "recommendation": "deliverable"
}
```

## 质量门

- ✅ 4 因子都已计算（不漏算）
- ✅ 所有 facts 都有 evidence_id（架构 §5.3 Evidence Ledger 标准字段）
- ✅ gaps 和 conflicts 都已显式标注（架构 §10 禁止沉默）
- ✅ evidence 字段对齐架构 §5.3 标准（evidence_id / content / source_type / source_table / source_url / confidence / data_currency / caliber / tags）
- ❌ 不满足 → 不进入 data_package 输出

## 与其他 Skill 的交接

- **上游**：`automotive-data-retriever`（拿到三路结果后调用）
- **下游**：返回给 `data-retriever`，用于构建最终 `data_package`

## v2.1 修正记录

- 2026-06-29 11:24：quality_passed 阈值从 0.7 改为 0.6（对齐架构设计 §5.2 硬阈值）
- 2026-06-29 11:24：补充 `weight_config` 字段，标注权重来源是架构设计文档 §5.1
- 2026-06-29 11:24：evidence 字段对齐架构 §5.3 标准（增加 source_type / source_table / caliber / tags）

---

*版本：v2.1*
*更新时间：2026-06-29 11:24*
