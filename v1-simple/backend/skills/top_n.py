"""TopN 排名分析技能"""
from typing import Any
from .registry import BaseSkill, registry


class TopNSkill(BaseSkill):
    name = "top_n"
    description = (
        "对指定维度按指标进行排名，返回 TopN 或 BottomN。"
        "适用于'保费最高的地区'、'排名前5的险种'、'理赔率最高的险种'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "description": "排名依据的指标列名，如 premium, sum_insured, commission, claim_amount, paid_amount",
        },
        "dimension": {
            "type": "string",
            "description": "排名维度，如 region, channel, product_type, product_name, claim_type",
        },
        "n": {
            "type": "integer",
            "description": "返回前N条记录，默认 10",
        },
        "order": {
            "type": "string",
            "enum": ["desc", "asc"],
            "description": "排序方向: desc(从高到低) 或 asc(从低到高)",
        },
        "table": {
            "type": "string",
            "enum": ["policies", "claims"],
            "description": "查询的表，默认 policies",
        },
        "filters": {
            "type": "object",
            "description": "可选：过滤条件，键为列名，值为过滤值。如 {\"region\": \"华东\", \"product_type\": \"寿险\"}",
        },
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        metric = params.get("metric", "premium")
        dimension = params.get("dimension", "region")
        n = params.get("n", 10)
        order = params.get("order", "desc").upper()
        table = params.get("table", "policies")
        filters = params.get("filters", {})

        conditions = [f"{col} = '{val}'" for col, val in filters.items()]
        where = ""
        if conditions:
            where = "\nWHERE " + " AND ".join(conditions)

        return f"""SELECT
    {dimension},
    SUM({metric}) AS total_{metric},
    COUNT(*) AS record_count,
    ROUND(AVG({metric}), 2) AS avg_{metric}
FROM {table}{where}
GROUP BY {dimension}
ORDER BY total_{metric} {order}
LIMIT {n}"""


registry.register(TopNSkill())
