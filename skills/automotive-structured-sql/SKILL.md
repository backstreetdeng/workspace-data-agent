# automotive-structured-sql（结构化数据查询）

## 身份与能力边界

- **定位**：封装 `tools/targeted_sql_pack.py`，负责 PostgreSQL 结构化数据查询（销量 / 份额 / 价格 / 配置）
- **触发条件**：`automotive-data-retriever` 判定需要 SQL 路径时调用
- **能力上限**：返回 8 块结构化数据 + 品牌映射后的精确查询
- **能力下限**：不做品牌映射（上层做）、不做质量评分（上层做）、不做战略分析

> **权威依据**：`E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\汽车市场AI智能体架构设计-垂直领域方案-20260623.md` §4.3 Skill 2

## 执行流程

### Step 1：接收参数
```python
{
    "target_brand": "比亚迪",        # 可选，但强烈建议
    "brand_aliases": ["比亚迪汽车有限公司", "比亚迪汽车工业有限公司"],  # 必填（由上层品牌映射提供）
    "target_model": "唐",            # 可选
    "price_range": "20-30万",        # 可选
    "time_range": "近12个月",        # 可选，默认近12个月
    "market_scope": "新能源 SUV",    # 可选
    "power_type": "新能源",          # 可选
}
```

### Step 2：调用 targeted_sql_pack（2026-06-29 修正签名）
```python
from tools.targeted_sql_pack import run_targeted_sql_pack

result = run_targeted_sql_pack(
    analysis_plan={
        "target_brand": target_brand,
        "brand_aliases": brand_aliases,  # 必填
        "time_range": time_range,
        "market_scope": market_scope,
        "power_type": power_type,
        "price_band": price_range,
    },
    session_id=session_id,  # 可选，用于阶段回调
)
```

> ⚠️ **2026-06-29 修正**：原 SKILL.md 写的 `run_targeted_sql_pack(target_brand=..., time_range=...)` 是错的。真实签名是 `run_targeted_sql_pack(analysis_plan=dict)`，所有参数必须包在 analysis_plan 里。

### Step 3：解析 8 块结果

| 块 | 内容 | 关键字段 |
|----|------|---------|
| market_overview | 整体市场 | total_sales, brand_count, model_count, period_start, period_end |
| monthly_trend | 月度趋势 | month[], sales[], mom_pct |
| yoy_change | 同比变化 | period, sales, yoy_pct |
| competitor_share | 竞品份额 | brand[], sales[], model_count, share_pct |
| target_brand_performance | 目标品牌表现 | brand, sales, model_count, period |
| model_contribution | 车型贡献 | model, brand, power_type, vehicle_level, segment, sales |
| power_mix | 动力类型构成 | power_type, sales, model_count |
| price_and_config | 价格带与配置 | model, maker, energy_type, level, guide_price, price_band, cltc_range, motor_power |

### Step 4：返回结果
返回原始 SQL 结果（含 `success`, `blocks[]`, `period_start`, `period_end`），让 `data-quality-validator` 处理。

## 决策规则

| 情况 | 决策 |
|------|------|
| `target_brand` 缺失 | 仅返回 4 块（market_overview, monthly_trend, yoy_change, competitor_share） |
| `brand_aliases` 为空 | SQL 返回 0 行，记录 `gap="brand_aliases_missing"` |
| 品牌映射失败 | 返回 `gaps=["brand_mapping_failed"]`，所有 brand-specific 块为空 |
| 表字段不存在 | 跳过该查询，返回 `gap="field_not_exists"` |
| SQL 执行超时（>30s） | 返回 `status=partial`, `error="sql_timeout"` |
| SQL 列名错误 | 返回 `status=failed`, `error="undefined_column"`（参考 2026-06-29 bug fix） |

## 输出格式

```json
{
  "skill": "automotive-structured-sql",
  "success": true,
  "blocks": [
    {"name": "market_overview", "purpose": "...", "rows": [...], "row_count": 1},
    {"name": "monthly_trend", "purpose": "...", "rows": [...], "row_count": 6},
    ...
  ],
  "period_start": 202509,
  "period_end": 202602,
  "previous_period_start": 202503,
  "previous_period_end": 202508,
  "results": [...],
  "brand_mapping": {
    "input": "比亚迪",
    "matched": ["比亚迪汽车工业有限公司", "比亚迪汽车有限公司"],
    "confidence": 0.95
  },
  "gaps": [],
  "errors": []
}
```

## 质量门

- ✅ 至少 1 个块有数据（row_count > 0）
- ✅ brand_mapping confidence >= 0.7
- ✅ SQL 执行无 `UndefinedColumn` 错误
- ❌ 不满足 → `status=partial`

## 与其他 Skill 的交接

- **上游**：`automotive-data-retriever`
- **下游**：返回给 `data-retriever`，再交给 `data-quality-validator`
- **底层工具**：`tools/targeted_sql_pack.py`（19.7KB，2026-06-29 已 fix 列名错位）

## v2.1 修正记录

- 2026-06-29 11:24：修正 `run_targeted_sql_pack()` 调用签名（analysis_plan dict 形式）+ 8 块字段名按真实 DB schema 对齐
- 2026-06-29 11:24：补充 `brand_aliases` 必填约束 + 价格带/配置用 config_data 而非 sales_import

---

*版本：v2.1*
*更新时间：2026-06-29 11:24*
