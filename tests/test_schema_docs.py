"""
test_schema_docs.py — schema doc 与真实 DB 漂移校验（CI 用）

目的：防止 references/schemas/database-schema.md 与真实 DB schema 再次出现"说一套写一套"的漂移
（2026-06-29 教训：原 doc 写"产品名称/车型/月份/价格"等不存在的字段，导致 SQL UndefinedColumn）

用法：
    E:\AI\data\envs\car_agent_env\Scripts\python.exe tests/test_schema_docs.py
"""
import sys
import re
import json
from pathlib import Path

try:
    import psycopg2
except ImportError:
    print("[FAIL] psycopg2 未安装", file=sys.stderr)
    sys.exit(2)


DB_CONFIG = {
    "host": "192.168.3.146",
    "port": 5432,
    "database": "vectordb",
    "user": "vectordb",
    "password": "vectordb123",
}

# 5 张核心表
TABLES = ["sales_import", "tech_data", "config_data", "documents", "chunks"]

# schema doc 路径
SCHEMA_DOC = Path("references/schemas/database-schema.md")


def get_real_schema():
    """从 information_schema.columns 拉真实列名"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    schema = {}
    for table in TABLES:
        cur.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """, (table,))
        cols = [{"name": r[0], "type": r[1], "nullable": r[2]} for r in cur.fetchall()]
        cur.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cur.fetchone()[0]
        schema[table] = {"columns": cols, "row_count": row_count}
    conn.close()
    return schema


def parse_schema_doc():
    """
    从 schema doc 解析出声明的表与列。
    
    支持两种 doc 格式：
    1. `### sales_import（销量数据，13 列）` + markdown 表格
    2. `=== sales_import (13 cols) ===` + 字段列表
    """
    if not SCHEMA_DOC.exists():
        return None
    text = SCHEMA_DOC.read_text(encoding="utf-8")
    declared = {}
    for table in TABLES:
        # 格式 1: ### table_name（...，N 列）
        m = re.search(rf"^###\s*{table}[^\n]*?(\d+)\s*列", text, re.MULTILINE)
        # 格式 2: === table_name (N cols) ===
        if not m:
            m = re.search(rf"^===\s*{table}\s*\((\d+)\s*cols?\)", text, re.MULTILINE)
        if not m:
            declared[table] = None
            continue
        declared_cols_count = int(m.group(1))
        # 找该小节的 markdown 表格
        section_pattern = rf"^###\s*{table}.*?(?=^###\s|^##\s|\Z)"
        m2 = re.search(section_pattern, text, re.MULTILINE | re.DOTALL)
        columns = []
        if m2:
            section_text = m2.group(0)
            # 表格行: | 字段 | 类型 | NULL | 说明 |
            row_pattern = r"^\|\s*(\w+)\s*\|\s*\w+"
            for line in section_text.split("\n"):
                cm = re.match(row_pattern, line)
                if cm and cm.group(1) not in ("字段", "列", "Column", "column", "---", ""):
                    columns.append(cm.group(1))
        declared[table] = {"columns_count": declared_cols_count, "columns": columns}
    return declared


def main():
    print("=" * 60)
    print("schema doc vs real DB 漂移校验")
    print("=" * 60)

    print("\n[Step 1] 拉取真实 DB schema...")
    real = get_real_schema()
    for t in TABLES:
        print(f"  real.{t}: {len(real[t]['columns'])} cols, {real[t]['row_count']} rows")

    print("\n[Step 2] 解析 schema doc 声明...")
    doc = parse_schema_doc()
    if doc is None:
        print(f"[FAIL] schema doc 不存在: {SCHEMA_DOC}", file=sys.stderr)
        sys.exit(2)
    for t in TABLES:
        d = doc.get(t)
        if d:
            print(f"  doc.{t}: {d['columns_count']} cols declared, parsed {len(d['columns'])} col names")

    print("\n[Step 3] 比对...")
    errors = []
    for table in TABLES:
        real_count = len(real[table]["columns"])
        real_row = real[table]["row_count"]
        real_cols = set(c["name"] for c in real[table]["columns"])
        declared = doc.get(table)
        if declared is None:
            errors.append(f"{table}: doc 缺小节（找不到 `### {table}...`）")
            continue
        doc_count = declared["columns_count"]
        doc_cols = set(declared["columns"])

        if real_count != doc_count:
            errors.append(f"{table}: 列数不一致 doc={doc_count} real={real_count}")
        else:
            print(f"  [OK] {table}: 列数 {real_count} 一致")
        print(f"        行数 real={real_row}")

        missing_in_doc = real_cols - doc_cols
        extra_in_doc = doc_cols - real_cols
        if missing_in_doc:
            errors.append(f"{table}: doc 缺少字段 {sorted(missing_in_doc)}")
        if extra_in_doc:
            errors.append(f"{table}: doc 多出字段 {sorted(extra_in_doc)}")

    print("\n" + "=" * 60)
    if errors:
        print(f"[FAIL] 发现 {len(errors)} 个漂移:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        total = sum(len(real[t]["columns"]) for t in TABLES)
        print(f"[PASS] schema doc 与真实 DB 完全对齐（5 张表 / {total} 个字段）")
        sys.exit(0)


if __name__ == "__main__":
    main()
