# SQL 模式：品牌动态映射

## 模式 1：取所有企业名称

```sql
SELECT DISTINCT 企业名称 FROM sales_import ORDER BY 企业名称;
-- 返回 307 个企业
```

## 模式 2：短品牌名 → 企业全称 映射

### 比亚迪
```sql
SELECT 企业名称 FROM sales_import
WHERE 企业名称 LIKE '%比亚迪%'
GROUP BY 企业名称;
-- 预期结果：
-- 比亚迪汽车工业有限公司
-- 比亚迪汽车有限公司
```

### 理想
```sql
SELECT 企业名称 FROM sales_import
WHERE 企业名称 LIKE '%理想%'
GROUP BY 企业名称;
-- 预期结果：
-- 北京理想汽车有限公司
-- 重庆理想汽车有限公司
```

### 赛力斯 / 问界
```sql
SELECT 企业名称 FROM sales_import
WHERE 企业名称 LIKE '%赛力斯%'
GROUP BY 企业名称;
-- 预期结果：
-- 赛力斯汽车有限公司
-- 赛力斯汽车（湖北）有限公司
```

### 特斯拉
```sql
SELECT 企业名称 FROM sales_import
WHERE 企业名称 LIKE '%特斯拉%'
GROUP BY 企业名称;
-- 预期结果：
-- 特斯拉汽车（北京）有限公司
-- 特斯拉（上海）有限公司
```

## 模式 3：验证表字段是否存在

```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'sales_import';
-- 检查 产品名称 字段是否真的存在（不存在！）
```

## 模式 4：动态映射后查询

```python
# 假设已映射出企业名称列表
matched_enterprises = ['比亚迪汽车工业有限公司', '比亚迪汽车有限公司']

# SQL 查询
sql = f"""
SELECT 月份, SUM(销量) AS total
FROM sales_import
WHERE 企业名称 IN ({','.join(['%s'] * len(matched_enterprises))})
GROUP BY 月份
ORDER BY 月份 DESC
LIMIT 12;
"""
```

---

*版本：v2.0*
*更新时间：2026-06-29*
