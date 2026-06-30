# tests/ - 测试脚本

## 用途

data-agent 的 smoke test / 回归测试 / E2E 验证

## 当前文件

- `README.md` - 本文件
- `smoke_test.py` - 基础连接测试（DB + 向量）

## 测试覆盖

| 测试项 | 命令 |
|--------|------|
| Python 环境 | `python -c "import pydantic; print(pydantic.VERSION)"` |
| PostgreSQL 连接 | `python tests/test_db_connection.py` |
| 向量检索 | `python tests/test_vector_search.py` |
| 品牌映射 | `python tests/test_brand_mapping.py` |
| 三路融合 | `python tests/smoke_test.py` |

## 测试原则

- 测试必须有可验证的输出（不要 print "ok"）
- 测试必须独立（不依赖其他测试）
- 测试必须快速（每个 < 30s）
- 测试失败立即修复，不要绕过

---

*版本：v2.0*
*更新时间：2026-06-29*
