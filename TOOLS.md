# TOOLS.md - 数据智能体工具集

## ⚠️ 强制 Python 运行时（铁律）

```bash
# ✅ 必须用
E:\AI\data\envs\car_agent_env\Scripts\python.exe

# ❌ 禁止用
C:\Program Files\Python39\python.exe
```

**验证**：
```bash
E:\AI\data\envs\car_agent_env\Scripts\python.exe -c "import pydantic; print(pydantic.VERSION)"
# 期望: 2.13.4
```

**为什么**：默认 Python39 缺 `pydantic.json_schema`，会导致 `retrieval.vector_store` 导入失败。

## 数据库连接配置

```python
DB_CONFIG = {
    "host": "192.168.3.146",
    "port": 5432,
    "database": "vectordb",
    "user": "vectordb",
    "password": "vectordb123",
}
```

## 数据库表（2026-06-29 11:24 在线 verify）

| 表 | 行数 | 列数 | 关键字段 |
|----|------|------|----------|
| sales_import | 22,502 | 13 | 销售日期(YYYYMM), 企业名称, 产品商标, 通用名称, 技术类型, 乘用车细分, 销量 |
| tech_data | 2,455 | 53 | 产品商标, 产品型号, 通用名称, 价格, CLTC续驶里程, 电机峰值功率 |
| config_data | 3,463 | 39 | 车型名称, 厂商, 厂商指导价, 价格带(20), 能源类型, CLTC纯电续航里程 |
| documents | 186 | 6 | file_name, source, brand, category, upload_date |
| chunks | 29,150 | 16 | content, embedding(vector 1024), brand, car_model, publish_date, metadata |

**⚠️ 重要**：
- `sales_import` **没有** `产品名称` / `车型` / `月份` / `价格` 列！车型查询需用 `通用名称` 或 `产品型号`
- `config_data.厂商` 用的是**短名**，`sales_import.企业名称` 用的是**全名**，两者映射需单独维护短名↔全名对照表
- 详细 schema 见 `references/schemas/database-schema.md`

## 向量模型

- **模型**: BAAI/bge-large-zh-v1.5
- **维度**: 1024
- **距离**: cosine
- **关键词命中验证**（2026-06-29 11:24）：零跑=81, 比亚迪=178, 唐=45, SUV=436

## 核心工具调用

### 工具 1: targeted_sql_pack.py（结构化 8 块）

```python
import sys
sys.path.insert(0, "tools")
from targeted_sql_pack import run_targeted_sql_pack, build_targeted_sql_evidences, missing_required_blocks

# ✅ 正确调用：analysis_plan 是 dict-like
result = run_targeted_sql_pack(
    analysis_plan={
        "target_brand": "比亚迪",                  # 必传，否则只返回 4 块
        "brand_aliases": ["比亚迪汽车有限公司", "比亚迪汽车工业有限公司"],  # 品牌动态映射后填入
        "time_range": "2025-01~2025-12",          # 或 "近6个月" / "2025年" / "近12个月"
        "market_scope": "新能源 SUV",             # 可选
        "power_type": "新能源",                    # 可选
        "price_band": "20-30万",                   # 可选
    },
    # session_id / callback_url 可选（推送给编排专家）
)
```

**8 个输出块**：
- `market_overview` - 整体市场（total_sales / brand_count / model_count / period）
- `monthly_trend` - 月度趋势（month / sales / mom_pct）
- `yoy_change` - 同比变化（current vs previous_year，yoy_pct）
- `competitor_share` - 竞品份额（brand / sales / model_count / share_pct）
- `target_brand_performance` - 目标品牌表现（brand / sales / model_count）
- `model_contribution` - 车型贡献（model / brand / power_type / vehicle_level / segment / sales）
- `power_mix` - 动力类型构成（power_type / sales / model_count）
- `price_and_config` - 价格带与配置（model / maker / energy_type / level / guide_price / price_band / cltc_range / motor_power）

**辅助函数**：
```python
evidences = build_targeted_sql_evidences(result, analysis_plan)
missing = missing_required_blocks(result, target_brand="比亚迪")
```

### 工具 2: pg-vector-search（向量检索，主实现）

```python
import sys
sys.path.insert(0, "skills/pg-vector-search")
from vector_search import vector_search, search_by_intent, skill_main

# ✅ 主函数：混合检索（推荐）
result = vector_search(
    query="比亚迪 唐 销量",
    top_k=10,
    brand="比亚迪",       # 可选过滤
    source="数据中心",     # 可选过滤
    search_mode="hybrid", # hybrid / vector / keyword
)

# 按意图检索
result = search_by_intent(
    intent_result={"keywords": ["增程式", "销量"], "brands_mentioned": ["问界"]},
    top_k=10,
)

# OpenClaw skill 入口
result = skill_main(action="search", params={"query": "...", "top_k": 6})
```

**输出格式**：
```json
{
  "success": true,
  "query": "比亚迪 唐 销量",
  "search_mode": "hybrid",
  "count": 5,
  "results": [
    {
      "rank": 1,
      "content": "...",
      "score": 0.7251,
      "source": "数据中心",
      "brand": "比亚迪, 特斯拉, 理想, 问界",
      "file_name": "新能源分阶段车型及投放节奏对销量影响分析（中乘数据分析）.md",
      "publish_date": null
    }
  ]
}
```

### 工具 3: automotive-vector-rag（data-agent 包装）

```python
# 这个 skill 没有独立 Python 实现，是 data-agent 视角的"语义层"
# 实际调用 pg-vector-search 的 vector_search()，再包装成 data-agent 输出格式
# 详见 skills/automotive-vector-rag/SKILL.md
```

### 工具 4: tavily-search（外部实时）

```python
import sys
sys.path.insert(0, "skills/tavily-search/scripts")
from tavily_search import tavily_search, main

result = tavily_search(
    query="比亚迪 2026年5月 销量",
    max_results=5,
    source_filter=["cnevpost.com", "car.autohome.com.cn"],
)
```

### 工具 5: nl2sql-pg（自然语言转 SQL）

```python
import sys
sys.path.insert(0, "skills/nl2sql-pg")
from nl2sql import nl_to_sql, query, query_with_intent, execute_sql

# 自然语言 → SQL → 执行
result = nl_to_sql(
    question="比亚迪 2025年总销量",
    execute=True,
)
# 注意：车型特定查询（唐年度销量）建议用 targeted_sql_pack
```

### 工具 6: cn-web-search（中文网页搜索，Node.js 实现）

```
# 该 skill 只有 package.json + README.md + SKILL.md，没有 Python 入口
# 通过 SKILL.md 调用约定执行（外部触发或脚本）
# 详见 skills/cn-web-search/SKILL.md
```

## 外部数据源

| 站点 | URL 模式 | 用途 | 优先级 |
|-----|---------|------|--------|
| CnEVPost | cnevpost.com | 品牌月度交付、财务（英文） | ⭐⭐⭐ |
| 汽车之家 | car.autohome.com.cn | 配置/价格/口碑验证 | ⭐⭐⭐ |
| EV100 | ev100.com.cn | NEV 宏观、国际对标 | ⭐⭐ |
| AutoThinker | autothinker.com | 深度研究报告 | ⭐⭐ |
| 乘联会 | cpcadata.com | 政策发布 | 数据需内部渠道 |
| MIIT | miit.gov.cn | 政策发布 | 数据需内部渠道 |

## 品牌动态映射规则（必做）

**禁止**：`WHERE 企业名称='比亚迪'` （返回 0 条）

**必须**：
```sql
-- 第 1 步：先取所有企业名
SELECT DISTINCT 企业名称 FROM sales_import;  -- 307 个企业

-- 第 2 步：动态映射
比亚迪 → 比亚迪汽车工业有限公司 / 比亚迪汽车有限公司（置信 0.95）
理想 → 北京理想汽车有限公司 / 重庆理想汽车有限公司（置信 0.90）
赛力斯/问界 → 赛力斯汽车有限公司 / 赛力斯汽车（湖北）有限公司（置信 0.85）
零跑 → 浙江零跑科技股份有限公司 / 零跑汽车有限公司
特斯拉 → 特斯拉汽车（北京）有限公司 / 特斯拉（上海）有限公司
```

**额外注意**：config_data.厂商 用短名（如 "比亚迪"），与 sales_import.企业名称（"比亚迪汽车工业有限公司"）需要单独维护**短名映射表**。

## 性能基线

- 单次 SQL 查询: < 5s
- 单次向量检索: < 3s
- 单次 Tavily: < 10s
- 三路并行总时长: < 15s（理想）
- 单 data_package 总时长: < 30s

## 失败回退

| 错误 | 回退策略 |
|------|---------|
| DB 不可达 | `status=failed, error="db_unreachable"`, 不重试超过 2 次 |
| 向量检索 0 条 | 降级到 Tavily 网页搜索 |
| Tavily 超时 | 标注 `gap="external_search_timeout"`, 不影响主流程 |
| 品牌映射失败 | 返回 `gaps=["brand_mapping_failed"]`, 等待人工 |
| 调错函数名（如 search_chunks） | 参考"核心工具调用"部分使用正确的 import |

## 已验证的 Skill 列表

| Skill | 路径 | 状态 | 备注 |
|-------|------|------|------|
| pg-vector-search | skills/pg-vector-search/ | ✅ 实际可用 | 真实 vector_search.py，含 vector_search/search_by_intent/skill_main |
| automotive-vector-rag | skills/automotive-vector-rag/ | ✅ SKILL.md 已对齐 | data-agent 视角的语义层，包装 pg-vector-search |
| tavily-search | skills/tavily-search/ | ✅ | 真实 tavily_search() |
| cn-web-search | skills/cn-web-search/ | ⚠️ Node.js 实现 | 只有 package.json，无 Python 入口 |
| nl2sql-pg | skills/nl2sql-pg/ | ✅ | `from nl2sql import nl_to_sql`（不是 nl2sql_pg.nl2sql） |
| automotive-data-retriever | skills/automotive-data-retriever/ | ✅ SKILL.md | 主入口编排 |
| automotive-structured-sql | skills/automotive-structured-sql/ | ✅ SKILL.md | 包装 targeted_sql_pack |
| automotive-external-search | skills/automotive-external-search/ | ✅ SKILL.md | 包装 tavily/cn-web |
| data-quality-validator | skills/data-quality-validator/ | ✅ SKILL.md | 4 因子置信度 |
| anysearch | skills/anysearch/ | ✅ | 通用搜索 |
| self-improving-agent | skills/self-improving-agent/ | ✅ | 学习闭环 |
| skill-vetter | skills/skill-vetter/ | ⚠️ 已清理 | v2.0 重组时删除残留 |

---

*版本：v3.0*
*更新时间：2026-06-29 11:24*
