# share/ - 团队协作索引

## 用途

data-agent 与其他 Agent 的协作记录 / 接口定义 / 架构决策

## 当前文件

- `README.md` - 本文件

## 与其他 Agent 的接口

### 接收（来自 strategy-orchestrator）
```python
sessions_send(
    agentId="data-agent",
    message={
        "task_id": "...",
        "intent_type": "...",
        "target_brand": "...",
        "time_range": "...",
        ...
    }
)
```

### 返回（给 strategy-orchestrator）
```python
sessions_send(
    agentId="strategy-orchestrator",
    message={
        "task_id": "...",
        "status": "success | partial | failed",
        "facts": [...],
        "sources": [...],
        "confidence": 0.85,
        "confidence_factors": {...},
        "gaps": [...],
        "conflicts": [...],
        "summary": "..."
    }
)
```

## 团队位置

```
market_strategy
    ↓
strategy-orchestrator
    ↓
data-agent ← 我
    ↓
strategy-orchestrator
    ↓
analysis-agent / report-agent
    ↓
strategy-orchestrator → market_strategy
```

## 更新规则

- 接口变化 → 更新本文件
- 架构决策 → 新增 ARCHITECTURE_*.md
- 故障复盘 → 新增 POSTMORTEM_*.md

---

*版本：v2.0*
*更新时间：2026-06-29*
