"""
nl2sql_pg skill
自然语言转SQL查询技能 - 基于PostgreSQL市场数据

功能：
- 将自然语言问题转换为SQL查询
- 执行结构化数据查询
- 支持销量、品牌、车型、趋势等查询
"""

import sys
import os
import json
import re
from typing import Dict, Any, List, Optional, Tuple

# 添加RAG引擎路径
RAG_ENGINE_PATH = r"E:\AI\data\envs\car_agent_env\ai-decision\rag-engine"
if RAG_ENGINE_PATH not in sys.path:
    sys.path.insert(0, RAG_ENGINE_PATH)


def load_dotenv():
    """加载环境变量"""
    env_path = os.path.join(os.path.dirname(RAG_ENGINE_PATH), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key.strip()] = value.strip()


load_dotenv()


# ==================== SQL模板定义 ====================

SQL_TEMPLATES = {
    # 销量查询
    "market_overview": """
        SELECT
            SUM("销量") as total_sales,
            COUNT(DISTINCT "企业名称") as brand_count,
            COUNT(DISTINCT "通用名称") as model_count
        FROM sales_import
        WHERE 1=1 {conditions}
    """,

    "sales_by_brand": """
        SELECT
            "企业名称" as brand,
            SUM("销量") as sales,
            COUNT(DISTINCT "通用名称") as model_count
        FROM sales_import
        WHERE 1=1 {conditions}
        GROUP BY "企业名称"
        ORDER BY sales DESC
        LIMIT {limit}
    """,

    "sales_by_model": """
        SELECT
            "通用名称" as model,
            "企业名称" as brand,
            "技术类型" as tech_type,
            SUM("销量") as sales
        FROM sales_import
        WHERE 1=1 {conditions}
        GROUP BY "通用名称", "企业名称", "技术类型"
        ORDER BY sales DESC
        LIMIT {limit}
    """,

    "sales_trend": """
        SELECT
            "销售日期" as month,
            SUM("销量") as sales
        FROM sales_import
        WHERE 1=1 {conditions}
        GROUP BY "销售日期"
        ORDER BY "销售日期"
    """,

    "segment_distribution": """
        SELECT
            "乘用车细分" as segment,
            SUM("销量") as sales
        FROM sales_import
        WHERE 1=1 {conditions}
        GROUP BY "乘用车细分"
        ORDER BY sales DESC
    """,

    # 价格区间+销量查询（直接聚合销量表获取准确数据）
    # 注意：价格过滤在报告生成层通过 config_data 匹配实现
    "sales_with_price": """
        SELECT
            "企业名称" as brand,
            "通用名称" as model,
            "技术类型" as tech_type,
            "乘用车细分" as segment,
            SUM("销量") as sales
        FROM sales_import
        WHERE 1=1 {conditions}
        GROUP BY "企业名称", "通用名称", "技术类型", "乘用车细分"
        ORDER BY sales DESC
        LIMIT {limit}
    """,

    # 配置查询
    "competitor_configs": """
        SELECT
            "车型名称",
            "款型名称",
            "厂商",
            "能源类型",
            "级别",
            "电动机总功率",
            "CLTC纯电续航里程",
            "百公里耗电量",
            "厂商指导价"
        FROM config_data
        WHERE 1=1 {conditions}
        LIMIT {limit}
    """,

    # 品牌对比
    "brand_comparison": """
        SELECT
            "企业名称" as brand,
            SUM("销量") as sales,
            COUNT(DISTINCT "通用名称") as model_count
        FROM sales_import
        WHERE 1=1 {conditions}
        GROUP BY "企业名称"
        ORDER BY sales DESC
    """
}

# 关键词映射
KEYWORD_MAPPINGS = {
    # 品牌
    "比亚迪": "比亚迪",
    "特斯拉": "特斯拉",
    "蔚来": "蔚来",
    "小鹏": "小鹏",
    "理想": "理想汽车",
    "问界": "问界",
    "小米": "小米汽车",
    "极氪": "极氪",
    "零跑": "零跑",

    # 技术类型
    "纯电": "纯电动",
    "电动车": "纯电动",
    "EV": "纯电动",
    "插混": "插电式混合动力",
    "PHEV": "插电式混合动力",
    "增程": "增程式",
    "混动": "混合动力",
    "HEV": "混合动力",
    "燃油": "汽油",

    # 细分市场
    "SUV": "SUV",
    "轿车": "轿车",
    "MPV": "MPV",
    "紧凑": "紧凑型车",
    "中型": "中型车",
    "中大型": "中大型车",

    # 价格区间
    "10万以下": (0, 100000),
    "10-15万": (100000, 150000),
    "15-20万": (150000, 200000),
    "20-30万": (200000, 300000),
    "30-50万": (300000, 500000),
    "50万以上": (500000, 9999999)
}

# 查询类型识别
QUERY_TYPE_PATTERNS = {
    "market_overview": ["市场规模", "市场概况", "总销量", "总体市场"],
    "sales_by_brand": ["品牌销量", "品牌排名", "哪个品牌卖得好", "品牌份额"],
    "sales_by_model": ["车型销量", "车型排名", "什么车卖得好", "竞品"],
    "sales_trend": ["趋势", "走势", "增长", "销量变化", "同比", "环比"],
    "segment_distribution": ["细分市场", "市场分布", "份额分布"],
    "competitor_configs": ["配置", "参数", "续航", "功率", "价格"],
    "brand_comparison": ["对比", "比较", "哪个好"]
}


def parse_query(question: str) -> Tuple[str, Dict[str, Any]]:
    """
    解析用户问题，识别查询类型和参数

    Args:
        question: 用户问题

    Returns:
        (query_type, params)
    """
    params = {
        "conditions": [],
        "limit": 20
    }

    # 价格区间映射（支持更多区间）
    price_keywords = [
        "10万以下", "10万以内",
        "10-15万", "10-18万", "10-20万",
        "15-20万", "15-25万",
        "20-30万", "20-35万",
        "30-50万", "30万以上",
        "50万以上"
    ]
    price_mapping = {
        "10万以下": (0, 100000),
        "10万以内": (0, 100000),
        "10-15万": (100000, 150000),
        "10-18万": (100000, 180000),
        "10-20万": (100000, 200000),
        "15-20万": (150000, 200000),
        "15-25万": (150000, 250000),
        "20-30万": (200000, 300000),
        "20-35万": (200000, 350000),
        "30-50万": (300000, 500000),
        "30万以上": (300000, 9999999),
        "50万以上": (500000, 9999999)
    }

    # 检测是否包含价格区间（需要使用 sales_with_price 模板）
    has_price_range = False
    detected_price_range = None
    for keyword in price_keywords:
        if keyword in question:
            has_price_range = True
            detected_price_range = keyword
            break

    # 识别查询类型（价格区间优先）
    if has_price_range:
        query_type = "sales_with_price"
    else:
        query_type = "market_overview"  # 默认
        max_score = 0

        for qtype, patterns in QUERY_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if pattern in question:
                    score += 1
            if score > max_score:
                max_score = score
                query_type = qtype

    # 提取品牌
    # 注意：竞品分析时不应限制品牌（用户想知道整个市场的竞品）
    # 只有在明确询问某品牌时才加品牌过滤
    brands = []
    for brand in ["比亚迪", "特斯拉", "蔚来", "小鹏", "理想", "问界", "极氪", "零跑", "小米"]:
        if brand in question:
            brands.append(brand)

    # 检查是否是竞品分析（"X的竞品分析"中X是被分析对象，不是过滤条件）
    is_competitive_analysis = "竞品" in question or query_type in ["sales_by_model", "brand_comparison", "competitor_configs"]

    # 竞品分析时不加品牌过滤
    skip_brand_filter = is_competitive_analysis

    if brands and not skip_brand_filter:
        # sales_import 表用 "企业名称"，config_data 表用 "厂商"
        if query_type == "sales_with_price":
            params["conditions"].append(f'(s."企业名称" LIKE \'%{brands[0]}%\' OR c."厂商" LIKE \'%{brands[0]}%\')')
        else:
            params["conditions"].append(f'"企业名称" LIKE \'%{brands[0]}%\'')
        params["brand"] = brands[0]
    elif brands:
        # 竞品分析时，记录品牌信息但不作为过滤条件
        params["brand"] = brands[0]

    # 提取技术类型（只匹配技术相关关键词）
    tech_keywords = ["纯电", "电动车", "EV", "插混", "PHEV", "增程", "混动", "HEV", "燃油", "汽油"]
    tech_mapping = {
        "纯电": "纯电动", "电动车": "纯电动", "EV": "纯电动",
        "插混": "插电式混合动力", "PHEV": "插电式混合动力",
        "增程": "增程式", "混动": "混合动力", "HEV": "混合动力", "燃油": "汽油"
    }
    for keyword in tech_keywords:
        if keyword in question:
            params["conditions"].append(f'"技术类型" = \'{tech_mapping[keyword]}\'')
            params["tech_type"] = tech_mapping[keyword]
            break

    # 提取价格区间（使用 config_data 的 厂商指导价，格式为 "10.99万" 需 *10000）
    # 注意：价格条件通过 sales_import 表的乘用车细分来间接过滤，不做精确价格匹配
    for keyword in price_keywords:
        if keyword in question:
            # 价格区间信息存储在 params 中，由调用方处理
            min_price, max_price = price_mapping[keyword]
            params["price_range"] = keyword
            params["min_price"] = min_price
            params["max_price"] = max_price
            break

    # 提取细分市场
    segment_keywords = ["SUV", "轿车", "MPV", "紧凑型", "中型"]
    segment_mapping = {
        "SUV": "SUV",
        "轿车": "轿车",
        "MPV": "MPV",
        "紧凑型": "紧凑型车",
        "中型": "中型车"
    }
    for keyword in segment_keywords:
        if keyword in question:
            # 细分市场直接过滤 sales_import 表
            params["conditions"].append(f'"乘用车细分" = \'{segment_mapping[keyword]}\'')
            params["segment"] = keyword
            break

    # 提取数量限制
    limit_match = re.search(r"前?(\d+)", question)
    if limit_match:
        params["limit"] = int(limit_match.group(1))

    return query_type, params


def nl_to_sql(question: str) -> Dict[str, Any]:
    """
    自然语言转SQL

    Args:
        question: 用户问题

    Returns:
        {
            "success": bool,
            "sql": str,
            "query_type": str,
            "params": dict
        }
    """
    try:
        query_type, params = parse_query(question)

        # 获取SQL模板
        template = SQL_TEMPLATES.get(query_type, SQL_TEMPLATES["market_overview"])

        # 构建WHERE条件
        conditions_list = params["conditions"]
        if conditions_list:
            # 条件前面加 AND
            conditions_str = " AND " + " AND ".join(conditions_list)
        else:
            conditions_str = ""

        # 填充模板
        sql = template.format(
            conditions=conditions_str,
            limit=params["limit"]
        )

        # 清理格式
        sql = re.sub(r'\s+', ' ', sql).strip()

        return {
            "success": True,
            "sql": sql,
            "query_type": query_type,
            "params": {
                "conditions": params["conditions"],
                "limit": params["limit"]
            },
            "raw_question": question
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "sql": None,
            "query_type": None
        }


def execute_sql(sql: str) -> Dict[str, Any]:
    """
    执行SQL查询

    Args:
        sql: SQL语句

    Returns:
        查询结果
    """
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor

        DB_CONFIG = {
            "host": os.environ.get("DB_HOST", "192.168.3.146"),
            "port": int(os.environ.get("DB_PORT", 5432)),
            "database": os.environ.get("DB_NAME", "vectordb"),
            "user": os.environ.get("DB_USER", "vectordb"),
            "password": os.environ.get("DB_PASSWORD", "vectordb123")
        }

        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        cur = conn.cursor()

        cur.execute(sql)
        rows = cur.fetchall()

        # 转换为列表
        results = [dict(row) for row in rows]

        cur.close()
        conn.close()

        return {
            "success": True,
            "record_count": len(results),
            "results": results,
            "sql": sql
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "record_count": 0,
            "results": [],
            "sql": sql
        }


def query(question: str, execute: bool = False) -> Dict[str, Any]:
    """
    自然语言查询主函数

    Args:
        question: 用户问题
        execute: 是否执行查询

    Returns:
        查询结果
    """
    # 转换为SQL
    sql_result = nl_to_sql(question)

    if not sql_result["success"]:
        return sql_result

    # 执行查询
    if execute:
        exec_result = execute_sql(sql_result["sql"])
        sql_result.update(exec_result)

    return sql_result


def query_with_intent(intent_result: Dict[str, Any], execute: bool = True) -> Dict[str, Any]:
    """
    根据意图识别结果进行查询

    Args:
        intent_result: intent_classifier 的输出
        execute: 是否执行

    Returns:
        查询结果
    """
    # 构建查询问题
    keywords = intent_result.get("keywords", [])
    brands = intent_result.get("brands_mentioned", [])
    price_range = intent_result.get("price_range", "")
    vehicle_type = intent_result.get("vehicle_type", "")
    intent_type = intent_result.get("intent_type", "")

    # 组合查询
    parts = []
    if brands:
        parts.append(brands[0])
    if price_range:
        parts.append(price_range)
    if vehicle_type:
        parts.append(vehicle_type)

    question = " ".join(parts) if parts else intent_result.get("question", "")

    # 根据意图类型选择查询重点
    if intent_type == "趋势分析":
        question += " 趋势"
    elif intent_type == "竞品分析":
        question += " 对比"
    elif intent_type == "画像分析":
        question += " 用户"

    return query(question, execute)


# OpenClaw skill 接口
def skill_main(action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    OpenClaw skill 主入口

    Args:
        action: 操作类型 (nl2sql/query/execute)
        params: 参数字典

    Returns:
        标准化结果
    """
    if params is None:
        params = {}

    if action == "nl2sql":
        return nl_to_sql(params.get("question", ""))
    elif action == "query":
        return query(
            params.get("question", ""),
            params.get("execute", True)
        )
    elif action == "execute":
        return execute_sql(params.get("sql", ""))
    elif action == "by_intent":
        return query_with_intent(
            params.get("intent_result", {}),
            params.get("execute", True)
        )
    else:
        return {"success": False, "error": f"未知操作: {action}"}


if __name__ == "__main__":
    # 命令行测试
    import argparse

    parser = argparse.ArgumentParser(description="自然语言转SQL查询")
    parser.add_argument("--question", default="比亚迪最近销量如何")
    parser.add_argument("--execute", action="store_true")

    args = parser.parse_args()

    result = query(args.question, args.execute)
    print(json.dumps(result, ensure_ascii=False, indent=2))
