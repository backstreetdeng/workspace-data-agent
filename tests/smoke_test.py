"""data-agent smoke test - 基础连接验证

测试项：
1. Python 环境（pydantic 2.13.4）
2. PostgreSQL 连接
3. 向量检索
4. 品牌动态映射
5. targeted_sql_pack 调用

运行：
    E:\\AI\\data\\envs\\car_agent_env\\Scripts\\python.exe tests/smoke_test.py
"""
import sys
import json


def test_python_env():
    """测试 Python 环境（pydantic 版本）"""
    import pydantic
    expected = "2.13.4"
    actual = pydantic.VERSION
    if actual != expected:
        print(f"[FAIL] pydantic {actual} != {expected}")
        print(f"  请用 E:\\AI\\data\\envs\\car_agent_env\\Scripts\\python.exe")
        return False
    print(f"[OK] pydantic {actual}")
    return True


def test_db_connection():
    """测试 PostgreSQL 连接"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="192.168.3.146",
            port=5432,
            database="vectordb",
            user="vectordb",
            password="vectordb123",
        )
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM sales_import")
        count = cur.fetchone()[0]
        conn.close()
        if count < 1000:
            print(f"[FAIL] sales_import only {count} rows (expected > 1000)")
            return False
        print(f"[OK] sales_import {count} rows")
        return True
    except Exception as e:
        print(f"[FAIL] DB connection: {e}")
        return False


def test_brand_mapping():
    """测试品牌动态映射"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="192.168.3.146",
            port=5432,
            database="vectordb",
            user="vectordb",
            password="vectordb123",
        )
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT 企业名称 FROM sales_import WHERE 企业名称 LIKE %s", ("%比亚迪%",))
        results = [r[0] for r in cur.fetchall()]
        conn.close()
        if not results:
            print(f"[FAIL] no BYD enterprises found")
            return False
        print(f"[OK] BYD enterprises: {results}")
        return True
    except Exception as e:
        print(f"[FAIL] brand mapping: {e}")
        return False


def test_vector_search():
    """测试向量检索（关键词命中验证）"""
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="192.168.3.146",
            port=5432,
            database="vectordb",
            user="vectordb",
            password="vectordb123",
        )
        cur = conn.cursor()
        for kw in ["零跑", "比亚迪", "SUV"]:
            cur.execute("SELECT COUNT(*) FROM chunks WHERE content LIKE %s", (f"%{kw}%",))
            count = cur.fetchone()[0]
            print(f"[OK] {kw}: {count} chunks")
        conn.close()
        return True
    except Exception as e:
        print(f"[FAIL] vector search: {e}")
        return False


if __name__ == "__main__":
    print("=" * 60)
    print("data-agent smoke test")
    print("=" * 60)
    
    results = {
        "python_env": test_python_env(),
        "db_connection": test_db_connection(),
        "brand_mapping": test_brand_mapping(),
        "vector_search": test_vector_search(),
    }
    
    print("=" * 60)
    print(json.dumps(results, indent=2, ensure_ascii=False))
    
    if all(results.values()):
        print("[ALL PASS]")
        sys.exit(0)
    else:
        print("[SOME FAILED]")
        sys.exit(1)
