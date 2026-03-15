"""同比分析技能"""
from typing import Any
from .registry import BaseSkill, registry


class YearOverYearSkill(BaseSkill):
    name = "year_over_year"
    description = (
        "计算指标的同比变化（与去年同期对比）。"
        "适用于'保费同比增长'、'理赔同比变化'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "description": "要分析的指标列名，如 premium, claim_amount, commission",
        },
        "date_column": {
            "type": "string",
            "description": "日期列名，默认 policy_date",
        },
        "dimensions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "分组维度，如 ['region'] 或 ['product_type']",
        },
        "period": {
            "type": "string",
            "enum": ["month", "quarter", "year"],
            "description": "对比周期粒度，默认 month",
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
        dims = params.get("dimensions", [])
        period = params.get("period", "month")
        table = params.get("table", "policies")
        filters = params.get("filters", {})

        dim_select = ", ".join(dims)
        dim_join = " AND ".join([f"curr.{d} = prev.{d}" for d in dims])

        curr_select = [f"DATE_TRUNC('{period}', CAST({date_col} AS DATE)) AS period"]
        if dims:
            curr_select.append(dim_select)
        curr_select.append(f"SUM({metric}) AS current_value")

        group_cols = ["period"]
        if dims:
            group_cols.extend(dims)

        conditions = [f"{col} = '{val}'" for col, val in filters.items()]
        where = ""
        if conditions:
            where = "\nWHERE " + " AND ".join(conditions)

        subq = f"""SELECT {', '.join(curr_select)}
FROM {table}{where}
GROUP BY {', '.join(group_cols)}"""

        join_cond = "curr.period = prev.period + INTERVAL 1 YEAR"
        if dim_join:
            join_cond += f" AND {dim_join}"

        select_outer = ["curr.period"]
        if dims:
            select_outer.extend([f"curr.{d}" for d in dims])
        select_outer.extend([
            "curr.current_value",
            "prev.current_value AS previous_value",
            "ROUND((curr.current_value - prev.current_value) / NULLIF(prev.current_value, 0) * 100, 2) AS yoy_change_pct",
        ])

        return f"""WITH base AS (
    {subq}
)
SELECT {', '.join(select_outer)}
FROM base curr
LEFT JOIN base prev ON {join_cond}
WHERE prev.current_value IS NOT NULL
ORDER BY curr.period DESC"""


registry.register(YearOverYearSkill())
