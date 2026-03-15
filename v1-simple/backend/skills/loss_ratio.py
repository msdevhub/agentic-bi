"""赔付率分析技能 — 跨表 JOIN policies + claims（避免重复计算）"""
from typing import Any
from .registry import BaseSkill, registry


class LossRatioSkill(BaseSkill):
    name = "loss_ratio"
    description = (
        "计算赔付率（已赔付金额 / 保费收入）。"
        "适用于'各险种赔付率'、'各地区赔付率排名'、'赔付率趋势'等问题。"
        "支持按地区、险种、渠道等维度分组分析。"
    )
    parameters_schema = {
        "dimensions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "分组维度，如 ['product_type'], ['region'], ['product_type', 'region']。注意：维度列必须在两张表中都存在（region, product_type）",
        },
        "time_granularity": {
            "type": "string",
            "enum": ["month", "quarter", "year", "none"],
            "description": "时间粒度，'none' 表示不按时间分组，默认 none",
        },
        "filters": {
            "type": "object",
            "description": "过滤条件，如 {\"region\": \"华东\", \"product_type\": \"健康险\"}",
        },
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        dims = params.get("dimensions", ["product_type"])
        time_gran = params.get("time_granularity", "none")
        filters = params.get("filters", {})

        # 构建各子查询的选择列和分组列
        p_select = []
        p_group = []
        c_select = []
        c_group = []
        join_conds = []

        if time_gran != "none":
            p_select.append(f"DATE_TRUNC('{time_gran}', policy_date) AS period")
            p_group.append("period")
            c_select.append(f"DATE_TRUNC('{time_gran}', claim_date) AS period")
            c_group.append("period")
            join_conds.append("p.period = c.period")

        for d in dims:
            p_select.append(d)
            p_group.append(d)
            c_select.append(d)
            c_group.append(d)
            join_conds.append(f"p.{d} = c.{d}")

        p_conds = [f"{col} = '{val}'" for col, val in filters.items()]
        c_conds = [f"{col} = '{val}'" for col, val in filters.items()]
        p_where = ("\nWHERE " + " AND ".join(p_conds)) if p_conds else ""
        c_where = ("\nWHERE " + " AND ".join(c_conds)) if c_conds else ""

        p_select_str = ", ".join(p_select)
        p_group_str = ", ".join(p_group)
        c_select_str = ", ".join(c_select)
        c_group_str = ", ".join(c_group)
        join_str = " AND ".join(join_conds)

        # 外层选择
        outer_cols = [f"p.{g}" for g in p_group]
        outer_cols.extend([
            "p.total_premium",
            "COALESCE(c.total_paid, 0) AS total_paid",
            "p.policy_count",
            "COALESCE(c.claim_count, 0) AS claim_count",
            "ROUND(COALESCE(c.total_paid, 0) / NULLIF(p.total_premium, 0) * 100, 2) AS loss_ratio_pct",
        ])

        order = "p.period" if time_gran != "none" else "loss_ratio_pct DESC"

        return f"""WITH p AS (
    SELECT {p_select_str},
        SUM(premium) AS total_premium,
        COUNT(*) AS policy_count
    FROM policies{p_where}
    GROUP BY {p_group_str}
),
c AS (
    SELECT {c_select_str},
        SUM(paid_amount) AS total_paid,
        COUNT(*) AS claim_count
    FROM claims{c_where}
    GROUP BY {c_group_str}
)
SELECT {', '.join(outer_cols)}
FROM p
LEFT JOIN c ON {join_str}
ORDER BY {order}"""


registry.register(LossRatioSkill())
