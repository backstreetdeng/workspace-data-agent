# 数据库 Schema（PostgreSQL vectordb）

**最后验证**: 2026-06-29 11:55
**数据库**: 192.168.3.146:5432 / vectordb
**用户**: vectordb
**校验脚本**: `tests/test_schema_docs.py`（CI 必跑）

> **CI 守门**：`E:\AI\data\envs\car_agent_env\Scripts\python.exe tests/test_schema_docs.py`
> - 任意表列数漂移 → FAIL
> - 任意字段名漂移 → FAIL
> - 所有表通过 → PASS

---

## 5 张核心表

### sales_import（销量数据，13 列）

| 字段 | 类型 | NULL | 说明 |
|------|------|------|------|
| id | integer | NO | 主键 |
| 销售日期 | integer | YES | YYYYMM 整数（如 202602），范围 202501~202602（14 个月） |
| 产品型号 | text | YES | 工信部公告产品型号（如 AHC6460BEVP0E） |
| 企业名称 | text | YES | **完整企业名**（如 "比亚迪汽车工业有限公司"） |
| 产品商标 | text | YES | 整车厂商品牌（如 "比亚迪牌"/"方程豹牌"） |
| 技术类型 | text | YES | 纯电动/插电式混合动力/增程式 |
| 乘用车细分 | text | YES | 轿车/SUV/MPV 等 |
| 通用名称 | text | YES | 车型可读名（如 "比亚迪海鸥"） |
| 整备质量 | text | YES | kg |
| 总质量 | text | YES | kg |
| 轴距 | text | YES | mm |
| 车型级别 | text | YES | A0/A/B/C 级等 |
| 销量 | integer | YES | 当月销量（辆） |

**行数**: 22,502
**重要**：此表**没有** `产品名称` / `车型` / `月份` / `价格` 列，错误假设会导致 SQL 失败。

### tech_data（技术参数，53 列）

| 字段 | 类型 | NULL |
|------|------|------|
| id | integer | NO |
| 驱动类别 | text | YES |
| 大分类 | text | YES |
| 批次 | integer | YES |
| 款型ID | double precision | YES |
| 产品商标 | text | YES |
| 产品型号 | text | YES |
| 产品名称 | text | YES |
| 企业名称 | text | YES |
| 其他 | text | YES |
| 说明 | text | YES |
| 发动机型号 | text | YES |
| 发动机企业 | text | YES |
| 排量 | text | YES |
| 功率 | text | YES |
| 企业名称乘修正 | text | YES |
| 排量_修正 | text | YES |
| 功率_修正 | text | YES |
| 外形尺寸MM长 | text | YES |
| 外形尺寸MM宽 | text | YES |
| 外形尺寸MM高 | text | YES |
| 车型细分类 | text | YES |
| 轴距 | text | YES |
| 总质量 | text | YES |
| 整备质量 | text | YES |
| 电池类型 | text | YES |
| 电池企业 | text | YES |
| 电池单体_电芯企业 | text | YES |
| 单体企业简称 | text | YES |
| 电池总成_PACK企业 | text | YES |
| 驱动电机企业 | text | YES |
| 驱动电机型号 | text | YES |
| 驱动电机类型 | text | YES |
| 电机额定功率 | text | YES |
| 电机峰值功率 | text | YES |
| 乘用车级别 | text | YES |
| 乘用车细分 | text | YES |
| 通用名称 | text | YES |
| 链接 | text | YES |
| 免税目录 | text | YES |
| 纯电动续驶里程 | text | YES |
| CLTC续驶里程 | text | YES |
| WLTC续驶里程 | text | YES |
| 动力蓄电池组总质量 | text | YES |
| 动力蓄电池组总能量 | text | YES |
| 系统能量密度 | text | YES |
| 储能装置种类 | text | YES |
| 综合工况电能消耗量 | text | YES |
| 外接充电 | text | YES |
| 年度 | text | YES |
| 驱动形式 | text | YES |
| 价格 | text | YES |
| 车型级别 | text | YES |

**行数**: 2,455

### config_data（配置数据，39 列）

| 字段 | 类型 | NULL |
|------|------|------|
| id | integer | NO |
| 车型名称 | text | YES |
| 款型id | text | YES |
| 款型名称 | text | YES |
| 能源类型 | text | YES |
| 上市时间 | text | YES |
| 电池能量 | text | YES |
| 驱动方式 | text | YES |
| 厂商 | text | YES | **短名**（如 "比亚迪"），与 sales_import.企业名称 全名映射见 `references/sql-patterns/config-data-brand-mapping.md` |
| 级别 | text | YES |
| 整备质量 | text | YES |
| 总质量 | text | YES |
| 长度 | text | YES |
| 宽度 | text | YES |
| 高度 | text | YES |
| 轴距 | text | YES |
| 前电动机型号 | text | YES |
| 后电动机型号 | text | YES |
| 电机类型 | text | YES |
| 电动机总功率 | text | YES |
| 电动机总扭矩 | text | YES |
| 前电动机最大功率 | text | YES |
| 前电动机最大扭矩 | text | YES |
| 后电动机最大功率 | text | YES |
| 后电动机最大扭矩 | text | YES |
| CLTC纯电续航里程 | text | YES |
| WLTC纯电续航里程 | text | YES |
| 百公里耗电量 | text | YES |
| 前电动机品牌 | text | YES |
| 后电动机品牌 | text | YES |
| 驱动电机数 | text | YES |
| 电机布局 | text | YES |
| 电池快充时间 | text | YES |
| 电池快充电量范围 | text | YES |
| 电池类型 | text | YES |
| 电芯品牌 | text | YES |
| 厂商指导价 | text | YES |
| WLTC燃料消耗量 | text | YES |
| 价格带 | text | YES |

**行数**: 3,463

### documents（文档元数据，6 列）

| 字段 | 类型 | NULL | 说明 |
|------|------|------|------|
| id | integer | NO | 主键 |
| file_name | text | YES | 文档原始文件名 |
| source | text | YES | 来源（数据中心/政策/分析报告等） |
| brand | text | YES | 关联品牌 |
| category | text | YES | 分类 |
| upload_date | timestamp | YES | 上传时间 |

**行数**: 186

### chunks（文本块+embedding，16 列）

| 字段 | 类型 | NULL | 说明 |
|------|------|------|------|
| id | integer | NO | 主键 |
| document_id | integer | YES | 关联 documents.id |
| content | text | YES | 文本块内容 |
| embedding | vector | YES | 1024 维向量（BAAI/bge-large-zh-v1.5） |
| chunk_index | integer | YES | 文档内顺序 |
| source | text | YES | 同 documents.source |
| brand | text | YES | 关联品牌 |
| car_model | text | YES | 关联车型 |
| publish_date | text | YES | 发布日期 |
| metadata | text | YES | JSON 元数据 |
| page_number | integer | YES | 页码 |
| policy_type | text | YES | 政策类型 |
| industry_level | text | YES | 行业层级 |
| parent_chunk_id | integer | YES | 父块 ID |
| section_title | text | YES | 章节标题 |
| region | text | YES | 地区 |

**行数**: 29,150

---

## 跨表查询注意事项

### 1. 品牌映射（最易出错）
- `sales_import.企业名称` = **全名**（如 "比亚迪汽车工业有限公司"）
- `config_data.厂商` = **短名**（如 "比亚迪"）
- `tech_data.企业名称` = **全名**（同 sales_import）
- 查询前必须先做品牌映射，参考 `references/sql-patterns/brand-mapping.md` 和 `references/sql-patterns/config-data-brand-mapping.md`

### 2. 时间字段统一
- `sales_import.销售日期` = 整数 YYYYMM（如 202602）
- `chunks.publish_date` = 字符串（格式不一，可能为空）
- `documents.upload_date` = timestamp

### 3. 车型名查询
- `sales_import.通用名称` = 可读车型名（如 "比亚迪海鸥"）
- `tech_data.通用名称` = 可读车型名
- `config_data.车型名称` = 可读车型名
- `chunks.car_model` = 文本块提到的车型（不一定是完整车型）

### 4. 向量查询
- `chunks.embedding` 维度 1024
- 模型 BAAI/bge-large-zh-v1.5
- 距离度量 cosine
- 检索函数 `vector_search()` 见 `skills/pg-vector-search/vector_search.py`

---

## v3.1 修正记录

- 2026-06-29 11:55：tech_data / config_data / chunks 字段从 53/39/16 个补齐（CI 校验要求完整）
- 2026-06-29 11:55：添加 CI 守门脚本 `tests/test_schema_docs.py` 引用
- 2026-06-29 11:24：v3.0 重写，5 张表 100% 按真实列名
- 2026-06-29：v2.x 教训：原 doc 写 "产品名称/车型/月份/价格" 等不存在字段，导致 SQL UndefinedColumn

---

*版本：v3.1*
*更新时间：2026-06-29 11:55*
