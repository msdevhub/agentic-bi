"""客户画像分析技能"""
from typing import Any
from .registry import BaseSkill, registry


class CustomerProfileSkill(BaseSkill):
    name = "customer_profile"
    description = (
        "分析客户画像：年龄段分布、性别分布、客户×险种交叉分析。"
        "适用于'客户年龄分布'、'男女保费占比'、'各年龄段险种偏好'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "enum": ["age_distribution", "gender_analysis", "cross_analysis"],
            "description": "分析类型: age_distribution(年龄段), gender_analysis(性别), cross_analysis(交叉分析)",
        },
        "measure": {
            "type": "string",
            "description": "度量指标: premium(保费), policy_count(保单数), sum_insured(保额). 默认 premium",
        },
        "cross_dimension": {
            "type": "string",
            "description": "交叉分析维度(仅 cross_analysis): product_type, channel, region",
        },
        "filters": {
            "type": "object",
            "description": "过滤条件",
        },
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        metric = params.get("metric", "age_distribution")
        measure = params.get("measure", "premium")
        cross_dim = params.get("cross_dimension", "product_type")
        filters = params.get("filters", {})

        conditions = [f"{col} = '{val}'" for col, val in filters.items()]
        where = ""
        if conditions:
            where = "\nWHERE " + " AND ".join(conditions)

        agg = f"SUM({measure})" if measure != "policy_count" else "COUNT(*)"
        agg_alias = f"total_{measure}" if measure != "policy_count" else "policy_count"

        if metric == "age_distribution":
            return f"""SELECT
    CASE
        WHEN customer_age < 25 THEN '18-24岁'
        WHEN customer_age < 35 THEN '25-34岁'
        WHEN customer_age < 45 THEN '35-44岁'
        WHEN customer_age < 55 THEN '45-54岁'
        ELSE '55岁以上'
    END AS age_group,
    {agg} AS {agg_alias},
    COUNT(*) AS policy_count,
    ROUND(AVG(premium), 2) AS avg_premium
FROM policies{where}
GROUP BY age_group
ORDER BY age_group"""

        elif metric == "gender_analysis":
            return f"""SELECT
    customer_gender,
    {agg} AS {agg_alias},
    COUNT(*) AS policy_count,
    ROUND(AVG(premium), 2) AS avg_premium,
    ROUND(AVG(customer_age), 1) AS avg_age
FROM policies{where}
GROUP BY customer_gender
ORDER BY {agg_alias} DESC"""

        else:  # cross_analysis
            return f"""SELECT
    CASE
        WHEN customer_age < 30 THEN '30岁以下'
        WHEN customer_age < 40 THEN '30-39岁'
        WHEN customer_age < 50 THEN '40-49岁'
        ELSE '50岁以上'
    END AS age_group,
    {cross_dim},
    {agg} AS {agg_alias},
    COUNT(*) AS policy_count
FROM policies{where}
GROUP BY age_group, {cross_dim}
ORDER BY age_group, {agg_alias} DESC"""


registry.register(CustomerProfileSkill())
