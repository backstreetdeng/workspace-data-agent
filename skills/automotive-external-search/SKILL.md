# automotive-external-search（外部数据搜索）

## 身份与能力边界

- **定位**：封装 Tavily / cn-web-search / CnEVPost / 汽车之家 / EV100 / AutoThinker 等外部数据源
- **触发条件**：`automotive-data-retriever` 判定需要网页路径时调用
- **能力上限**：返回 top_k 网页结果 + 来源标记 + 数据 currency
- **能力下限**：不做内容解析（除非开启 LLM extract）、不做战略分析

> **权威依据**：`E:\openclaw\knowledge\MyVault\文档\AI项目研究\AI智能体Skill改造\汽车市场AI智能体架构设计-垂直领域方案-20260623.md` §4.3 Skill 2（外部网页路径）+ §8.2（技术栈 Firecrawl + AnySearch + Tavily）

## 执行流程

### Step 1：接收参数
```python
{
    "query": "比亚迪唐L 2026 销量",
    "max_results": 5,                        # 默认 5，建议 ≤ 20
    "site_filter": ["cnevpost.com"],         # 可选，限定站点
    "language": "zh",                        # 默认 zh
    "freshness": "month",                    # day/week/month/year
    "task_id": "...",                        # 用于回调
    "session_id": "...",                     # 用于阶段回调
}
```

### Step 2：路由策略
| 场景 | 优先站点 | 调用函数 |
|------|---------|---------|
| 品牌月度交付（英文）| CnEVPost (cnevpost.com) | `tavily_search` + source_filter |
| 配置/价格/口碑验证 | 汽车之家 (car.autohome.com.cn) | `cn-web-search`（Node.js CLI） |
| NEV 宏观/国际对标 | EV100 (ev100.com.cn) | `tavily_search` |
| 深度研究报告 | AutoThinker (autothinker.com) | `tavily_search` |
| 中文实时信息 | 全网 | `cn-web-search` |
| 国际/英文信息 | 全网 | `tavily_search` |

### Step 3：调用多 Skill 并行（2026-06-29 修正函数名）
```python
import sys
sys.path.insert(0, "skills/tavily-search/scripts")
from tavily_search import tavily_search  # ✅ 真实函数名（不是 search_web）

# Tavily 主搜索（国际/英文 + 不限站点）
tavily_results = tavily_search(
    query=query,
    max_results=max_results,
    source_filter=site_filter,  # 可选
)

# CnEVPost 专项（如适用英文品牌数据）
if "delivery" in intent or brand_english:
    cnevpost_results = tavily_search(
        query=query,
        max_results=3,
        source_filter=["cnevpost.com"],
    )

# 汽车之家专项（如适用中文配置/口碑）
if "config" in intent or "price" in intent:
    # cn-web-search 是 Node.js 实现，需通过 shell 调用
    import subprocess
    autohome = subprocess.run(
        ["node", "skills/cn-web-search/scripts/run.js", "--query", query, "--sites", "car.autohome.com.cn"],
        capture_output=True, text=True, timeout=10,
    )
    autohome_results = parse_cn_web_output(autohome.stdout)
```

### Step 4：聚合与去重
按相关度排序 + URL 去重 + 来源标记。

### Step 5：返回结果

## 决策规则

| 情况 | 决策 |
|------|------|
| Tavily 超时 | 降级到 cn-web-search，标注 `gap="tavily_timeout"` |
| 所有外部源都失败 | 返回 `status=partial`, `gaps=["external_search_unavailable"]` |
| 站点返回 401/403 | 标记 `gap="site_blocked"`，跳过该站点 |
| 查询无结果 | 尝试放宽 query 关键词重试 1 次，仍 0 则标 `gap="no_results"` |
| 长任务 > 5 分钟 | 按架构设计 §10，必须 callback 阶段进度给 orchestrator |

## 输出格式

```json
{
  "skill": "automotive-external-search",
  "success": true,
  "results": [
    {
      "result_id": "R001",
      "title": "BYD February 2026 deliveries hit 320,000 units",
      "url": "https://cnevpost.com/2026/03/01/byd-deliveries/",
      "snippet": "BYD sold 320,363 vehicles in February...",
      "source_site": "cnevpost.com",
      "data_currency": "2026-02",
      "relevance_score": 0.85,
      "freshness": "month"
    }
  ],
  "sites_queried": ["cnevpost.com", "car.autohome.com.cn"],
  "gaps": [],
  "errors": []
}
```

## 质量门

- ✅ 至少 1 条结果来源是 ??? 站点（CnEVPost / 汽车之家 / EV100）
- ✅ 每条结果都有 `data_currency`
- ✅ 来源站点在白名单（不可信源自动降权或排除）
- ❌ 不满足 → `status=partial`, `confidence < 0.6`

## 与其他 Skill 的交接

- **上游**：`automotive-data-retriever`
- **下游**：返回给 `data-retriever`，再交给 `data-quality-validator`
- **底层工具**：`skills/tavily-search/scripts/tavily_search.py`（Tavily API）+ `skills/cn-web-search/`（Node.js CLI）

## 外部数据源优先级（与架构设计 §8.2 一致）

| 站点 | 用途 | 优先级 |
|-----|------|--------|
| CnEVPost | 品牌月度交付（英文）| ⭐⭐⭐ |
| 汽车之家 | 配置/价格/口碑验证 | ⭐⭐⭐ |
| EV100 | NEV 宏观、国际对标 | ⭐⭐ |
| AutoThinker | 深度研究报告 | ⭐⭐ |
| 乘联会 | 政策发布 | 数据需内部渠道 |
| MIIT | 政策发布 | 数据需内部渠道 |

## v2.1 修正记录

- 2026-06-29 11:24：修正函数名（`search_web` → `tavily_search`），明确 `cn-web-search` 是 Node.js 实现（无 Python 入口）
- 2026-06-29 11:24：补充 5 分钟 callback 规则（架构设计 §10）

---

*版本：v2.1*
*更新时间：2026-06-29 11:24*
