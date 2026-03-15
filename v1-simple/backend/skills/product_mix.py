"""产品结构分析技能"""
from typing import Any
from .registry import BaseSkill, registry


class ProductMixSkill(BaseSkill):
    name = "product_mix"
    description = (
        "分析产品结构：险种占比、新单vs续期、产品名排名。"
        "适用于'各险种保费占比'、'新单率'、'热门产品排名'、'续保率'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "enum": ["product_share", "new_business_ratio", "product_ranking", "renewal_rate"],
            "description": "product_share(占比), new_business_ratio(新单率), product_ranking(产品排名), renewal_rate(续保率)",
        },
        "dimension": {
            "type": "string",
            "description": "分组维度: product_type, product_name, region, channel. 默认 product_type",
        },
        "filters": {
            "type": "object",
            "description": "过滤条件",
        },
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        metric = params.get("metric", "product_share")
        dimension = params.get("dimension", "product_type")
        filters = params.get("filters", {})

        conditions = [f"{col} = '{val}'" for col, val in filters.items()]
        where = ""
        if conditions:
            where = "\nWHERE " + " AND ".join(conditions)

        if metric == "product_share":
            return f"""SELECT
    {dimension},
    SUM(premium) AS total_premium,
    COUNT(*) AS policy_count,
    ROUND(SUM(premium) * 100.0 / SUM(SUM(premium)) OVER (), 2) AS premium_share_pct,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 2) AS count_share_pct
FROM policies{where}
GROUP BY {dimension}
ORDER BY total_premium DESC"""

        elif metric == "new_business_ratio":
            return f"""SELECT
    {dimension},
    COUNT(*) AS total_policies,
    SUM(CASE WHEN is_new_business THEN 1 ELSE 0 END) AS new_business_count,
    ROUND(SUM(CASE WHEN is_new_business THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS new_business_ratio_pct,
    SUM(CASE WHEN is_new_business THEN premium ELSE 0 END) AS new_premium,
    SUM(CASE WHEN NOT is_new_business THEN premium ELSE 0 END) AS renewal_premium
FROM policies{where}
GROUP BY {dimension}
ORDER BY new_business_ratio_pct DESC"""

        elif metric == "product_ranking":
            return f"""SELECT
    product_name,
    product_type,
    SUM(premium) AS total_premium,
    COUNT(*) AS policy_count,
    ROUND(AVG(premium), 2) AS avg_premium,
    ROUND(AVG(customer_age), 1) AS avg_customer_age
FROM policies{where}
GROUP BY product_name, product_type
ORDER BY total_premium DESC"""

        else:  # renewal_rate
            return f"""SELECT
    p.{dimension},
    COUNT(*) AS total_renewal_records,
    SUM(CASE WHEN r.renewal_status = '已续保' THEN 1 ELSE 0 END) AS renewed_count,
    SUM(CASE WHEN r.renewal_status = '已失效' THEN 1 ELSE 0 END) AS lapsed_count,
    SUM(CASE WHEN r.renewal_status = '宽限期' THEN 1 ELSE 0 END) AS grace_period_count,
    ROUND(SUM(CASE WHEN r.renewal_status = '已续保' THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0), 2) AS renewal_rate_pct,
    ROUND(SUM(r.renewal_premium), 2) AS total_renewal_premium
FROM renewals r
JOIN policies p ON r.policy_id = p.policy_id{where}
GROUP BY p.{dimension}
ORDER BY renewal_rate_pct DESC"""


registry.register(ProductMixSkill())
