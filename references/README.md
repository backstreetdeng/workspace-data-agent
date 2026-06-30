# references/ - 参考资料索引

## 目录结构

```
references/
├── schemas/
│   └── database-schema.md       # PostgreSQL vectordb 5 张表结构
├── data-sources/
│   └── external-sources.md      # 外部数据源清单（CnEVPost/汽车之家等）
└── sql-patterns/
    └── brand-mapping.md         # 品牌动态映射 SQL 模式
```

## 使用方式

data-agent 在执行任务前应先读这些文档：

1. **接到 SQL 任务前**: `schemas/database-schema.md`（避免假设字段）
2. **接到外部搜索任务前**: `data-sources/external-sources.md`（选最优站点）
3. **接到品牌特定查询前**: `sql-patterns/brand-mapping.md`（先做动态映射）

## 更新规则

- 数据库 schema 变化时 → 更新 `schemas/database-schema.md`
- 外部站点新增/废弃 → 更新 `data-sources/external-sources.md`
- 新发现 SQL 模式 → 添加到 `sql-patterns/`

---

*版本：v2.0*
*更新时间：2026-06-29*
