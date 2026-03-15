"""趋势分析技能"""
from typing import Any
from .registry import BaseSkill, registry


class TrendSkill(BaseSkill):
    name = "trend"
    description = (
        "分析指标的时间趋势。"
        "适用于'月度保费趋势'、'理赔金额季度变化'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "description": "要分析的指标列名，如 premium, sum_insured, commission, claim_amount",
        },
        "date_column": {
            "type": "string",
            "description": "日期列名，默认 policy_date",
        },
        "granularity": {
            "type": "string",
            "enum": ["day", "week", "month", "quarter", "year"],
            "description": "时间粒度，默认 month",
        },
        "year": {
            "type": "integer",
            "description": "可选：限定年份，如 2024",
        },
        "dimensions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "可选：分组维度，如 ['product_type']",
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
        date_col = params.get("date_column", "policy_date")
        gran = params.get("granularity", "month")
        year = params.get("year")
        dims = params.get("dimensions", [])
        table = params.get("table", "policies")
        filters = params.get("filters", {})

        select_parts = [f"DATE_TRUNC('{gran}', CAST({date_col} AS DATE)) AS period"]
        group_parts = ["period"]

        for d in dims:
            select_parts.append(d)
            group_parts.append(d)

        select_parts.extend([
            f"SUM({metric}) AS total_{metric}",
            "COUNT(*) AS record_count",
            f"ROUND(AVG({metric}), 2) AS avg_{metric}",
        ])

        conditions = []
        if year:
            conditions.append(f"YEAR(CAST({date_col} AS DATE)) = {year}")
        for col, val in filters.items():
            conditions.append(f"{col} = '{val}'")

        where = ""
        if conditions:
            where = "\nWHERE " + " AND ".join(conditions)

        return f"""SELECT
    {', '.join(select_parts)}
FROM {table}{where}
GROUP BY {', '.join(group_parts)}
ORDER BY period"""


registry.register(TrendSkill())
