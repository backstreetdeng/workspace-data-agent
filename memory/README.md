# memory/ - 工作日志索引

## 用途

data-agent 每天的工作日志。记录：
- 接收的任务（task_id, intent, brand, time_range）
- 数据结果（SQL 块数、向量 hits、外部结果数）
- 遇到的问题和解决
- 学到的教训

## 文件命名

`YYYY-MM-DD.md`（如 `2026-06-29.md`）

## 模板

```markdown
# YYYY-MM-DD.md - data-agent 工作日志

## 今日任务总览
- 总任务数: X
- 成功率: Y/Z

## 任务列表
| task_id | intent | brand | status | confidence | notes |
|---------|--------|-------|--------|------------|-------|

## 重要问题与解决

### 问题 1: ...
- 现象: ...
- 根因: ...
- 解决: ...

## 学到的教训

- ...
```

---

*版本：v2.0*
*更新时间：2026-06-29*
