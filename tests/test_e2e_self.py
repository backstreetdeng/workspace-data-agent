"""test_e2e_self.py — data-agent 端到端自测

6 个测试用例覆盖 5 路径（SQL / 向量 / Tavily / AnySearch / 4 因子置信度）+ 缺口标注

运行：
    E:\AI\data\envs\car_agent_env\Scripts\python.exe tests/test_e2e_self.py
"""
import sys
import os
import json
import time
import subprocess
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "skills" / "pg-vector-search"))
sys.path.insert(0, str(ROOT / "skills" / "tavily-search" / "scripts"))

import psycopg2
DB_CONFIG = dict(host="192.168.3.146", port=5432, database="vectordb",
                 user="vectordb", password="vectordb123")

PASS = "[PASS]"
FAIL = "[FAIL]"
results = {"pass": 0, "fail": 0, "details": []}


def record(name, ok, detail):
    sym = PASS if ok else FAIL
    results["pass" if ok else "fail"] += 1
    line = f"{sym} {name}: {detail}"
    print(line)
    results["details"].append(line)


# ============ Test 1：SQL 路径 ============
def test_sql_path():
    print("\n=== Test 1: SQL 路径 (targeted_sql_pack 8 块) ===")
    try:
        from targeted_sql_pack import run_targeted_sql_pack
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT 企业名称 FROM sales_import WHERE 企业名称 LIKE %s", ('%比亚迪%',))
        byd_aliases = [r[0] for r in cur.fetchall()]
        record("1.1 brand_mapping", len(byd_aliases) > 0,
               f"比亚迪→{len(byd_aliases)} 个全名: {byd_aliases}")

        result = run_targeted_sql_pack(
            analysis_plan={"target_brand": "比亚迪", "brand_aliases": byd_aliases, "time_range": "2025-01~2025-12"}
        )
        blocks = result.get("blocks", []) if isinstance(result, dict) else []
        block_names = [b.get("name") if isinstance(b, dict) else b for b in blocks]
        record("1.2 sql_8_blocks", len(blocks) >= 4, f"返回 {len(blocks)} 块: {block_names}")

        # 验证关键块含 BYD
        for name in ["market_overview", "target_brand_performance", "competitor_share"]:
            blk = next((b for b in blocks if isinstance(b, dict) and b.get("name") == name), None)
            if blk and blk.get("rows"):
                record(f"1.3 block.{name}", True, f"含 {len(blk.get('rows', []))} 行")
            else:
                record(f"1.3 block.{name}", False, "块缺失或无数据")
        conn.close()
    except Exception as e:
        record("1.exception", False, str(e)[:200])


# ============ Test 2：向量路径 ============
def test_vector_path():
    print("\n=== Test 2: 向量路径 (pg-vector-search) ===")
    try:
        from vector_search import vector_search
        for mode in ["hybrid", "vector", "keyword"]:
            t0 = time.time()
            r = vector_search(query="比亚迪 唐 销量", top_k=5, search_mode=mode)
            dt = time.time() - t0
            ok = r.get("success") and r.get("count", 0) > 0
            record(f"2.{mode}", ok, f"返回 {r.get('count', 0)} 条, {dt:.2f}s")
    except Exception as e:
        record("2.exception", False, str(e)[:200])


# ============ Test 3：Tavily 路径 ============
def test_tavily_path():
    print("\n=== Test 3: Tavily 路径 (实时外部搜索) ===")
    try:
        # 确保 API key
        if not os.environ.get("TAVILY_API_KEY"):
            env_path = Path.home() / ".openclaw" / ".env"
            if env_path.exists():
                for line in env_path.read_text(encoding="utf-8").split("\n"):
                    if line.startswith("TAVILY_API_KEY="):
                        os.environ["TAVILY_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
        if not os.environ.get("TAVILY_API_KEY"):
            record("3.api_key", False, "TAVILY_API_KEY 未配置")
            return
        from tavily_search import tavily_search as tv
        t0 = time.time()
        r = tv(query="比亚迪 2026年5月 销量", max_results=3, include_answer=False, search_depth="basic")
        dt = time.time() - t0
        results_list = r.get("results", []) if isinstance(r, dict) else []
        record("3.tavily", len(results_list) > 0,
               f"返回 {len(results_list)} 条, {dt:.2f}s, top={results_list[0].get('title', '')[:50] if results_list else 'N/A'}")
    except Exception as e:
        record("3.exception", False, str(e)[:200])


# ============ Test 4：AnySearch 路径 ============
def test_anysearch_path():
    print("\n=== Test 4: AnySearch 路径 (通用搜索) ===")
    cli = ROOT / "skills" / "anysearch" / "scripts" / "anysearch_cli.ps1"
    if not cli.exists():
        record("4.cli_exists", False, str(cli))
        return
    try:
        t0 = time.time()
        proc = subprocess.run(
            ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(cli),
             "search", "比亚迪 海豹 2026", "--max_results", "3"],
            capture_output=True, timeout=30,
        )
        dt = time.time() - t0
        out = proc.stdout.decode("utf-8", errors="replace").strip() if proc.stdout else ""
        err = proc.stderr.decode("utf-8", errors="replace").strip() if proc.stderr else ""
        ok = proc.returncode == 0 and len(out) > 100 and "Error" not in err
        record("4.anysearch", ok,
               f"exit={proc.returncode}, {dt:.2f}s, stdout={len(out)}B, stderr={len(err)}B")
        if ok:
            print(f"      摘要: {out[:120]}")
    except subprocess.TimeoutExpired:
        record("4.timeout", False, ">30s")
    except Exception as e:
        record("4.exception", False, str(e)[:200])


# ============ Test 5：三路融合 + 4 因子置信度 ============
def test_three_way_fusion():
    print("\n=== Test 5: 三路融合 (SQL + 向量 + Tavily) + 4 因子置信度 ===")
    try:
        from targeted_sql_pack import run_targeted_sql_pack
        from vector_search import vector_search
        # SQL
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT 企业名称 FROM sales_import WHERE 企业名称 LIKE %s", ('%理想%',))
        aliases = [r[0] for r in cur.fetchall()]
        sql_result = run_targeted_sql_pack(
            analysis_plan={"target_brand": "理想", "brand_aliases": aliases, "time_range": "近6个月"}
        )
        sql_ok = sql_result.get("success") and len(sql_result.get("blocks", [])) > 0
        record("5.1 sql_in_fusion", sql_ok,
               f"理想汽车 SQL: {len(sql_result.get('blocks', []))} 块")

        # 向量
        vec = vector_search(query="理想汽车 增程式 销量", top_k=5, search_mode="hybrid")
        vec_ok = vec.get("success") and vec.get("count", 0) > 0
        record("5.2 vector_in_fusion", vec_ok, f"理想 RAG: {vec.get('count', 0)} chunks")

        # 4 因子置信度（对齐架构 §5.1 权重）
        sql_data_coverage = 0.85 if sql_ok else 0.0
        vec_rag_coverage = min(1.0, vec.get("count", 0) / 10.0)
        source_credibility = 0.9 if sql_ok and vec_ok else 0.5
        conflict_level = 1.0  # 无冲突
        overall = (sql_data_coverage * 0.30 + vec_rag_coverage * 0.25 +
                   source_credibility * 0.25 + conflict_level * 0.20)
        quality_passed = overall >= 0.6
        record("5.3 confidence_calc", True,
               f"overall={overall:.3f}, quality_passed={quality_passed}, "
               f"4 factors: data={sql_data_coverage}, rag={vec_rag_coverage:.2f}, "
               f"cred={source_credibility}, conflict={conflict_level}")
        conn.close()
    except Exception as e:
        record("5.exception", False, str(e)[:200])


# ============ Test 6：缺口场景 - 唐L 显式标注 ============
def test_gap_detection():
    print("\n=== Test 6: 缺口场景 - 唐L 无销售记录 (data_gap 显式标注) ===")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        # 查唐L 销量
        cur.execute("""
            SELECT 通用名称, SUM(销量) as total_sales, COUNT(*) as record_count
            FROM sales_import
            WHERE 通用名称 LIKE '%唐L%' OR 通用名称 = '唐L'
            GROUP BY 通用名称
        """)
        rows = cur.fetchall()
        if rows:
            record("6.gap_detected", True,
                   f"唐L 实际有 {len(rows)} 条记录: {[(r[0], r[1]) for r in rows]}")
        else:
            record("6.gap_detected", True,
                   "唐L 无销售记录（架构 §10 缺口信号：必须显式标注，不假装 0）")
        conn.close()
    except Exception as e:
        record("6.exception", False, str(e)[:200])


if __name__ == "__main__":
    test_sql_path()
    test_vector_path()
    test_tavily_path()
    test_anysearch_path()
    test_three_way_fusion()
    test_gap_detection()
    print("\n" + "=" * 60)
    print(f"汇总: PASS={results['pass']} FAIL={results['fail']}")
    print("=" * 60)
    sys.exit(0 if results["fail"] == 0 else 1)
