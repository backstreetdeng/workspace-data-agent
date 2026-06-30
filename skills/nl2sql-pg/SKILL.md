---
name: nl2sql-pg
description: "自然语言转SQL查询：将用户问题转换为SQL并执行，查询销量、市场份额等结构化数据"
metadata: {"clawdbot":{"emoji":"📊"}, "openclaw": {"tools": ["query"]}}
---

# 自然语言转SQL查询 Skill

## 功能说明

将自然语言问题转换为 SQL 查询并执行。从 PostgreSQL 数据库获取：
- 品牌销量数据
- 车型销量排名
- 市场趋势数据
- 细分市场分布

## 工具列表

| 工具 | 用途 | 参数 |
|------|------|------|
| `query` | NL转SQL并执行 | `question`: 用户问题, `execute`: 是否执行 |

## 输入参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| question | string | 必填 | 自然语言问题 |
| execute | bool | true | 是否执行查询 |

## 输出格式

```json
{
  "success": true,
  "sql": "SELECT ... FROM sales_import WHERE ...",
  "query_type": "sales_by_brand",
  "record_count": 15,
  "results": [
    {"brand": "比亚迪", "sales": 1500000, "model_count": 12}
  ]
}
```

## 数据库表结构

### sales_import (销量数据)
- 企业名称, 通用名称, 技术类型
- 销量, 销售日期, 乘用车细分
- 厂商指导价

### config_data (配置数据)
- 车型名称, 款型名称, 厂商
- 能源类型, 级别, 电动机总功率
- CLTC纯电续航里程, 百公里耗电量
- 厂商指导价

## 使用示例

```prose
session: analyst
  prompt: "使用 nl2sql-pg 查询比亚迪销量：query(question='比亚迪最近销量如何', execute=true)"
```

## 技术实现

- 主文件: `nl2sql.py`
- 函数: `query(question, execute)`
- 依赖: psycopg2, PostgreSQL
