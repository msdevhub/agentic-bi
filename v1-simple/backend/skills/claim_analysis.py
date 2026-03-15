"""理赔分析技能 — 理赔率、时效、拒赔率"""
from typing import Any
from .registry import BaseSkill, registry


class ClaimAnalysisSkill(BaseSkill):
    name = "claim_analysis"
    description = (
        "深度分析理赔数据：理赔率、平均处理时效、拒赔率、赔付金额分布。"
        "适用于'理赔时效分析'、'拒赔率排名'、'各险种理赔情况'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "enum": ["overview", "processing_time", "rejection_rate", "amount_distribution"],
            "description": "分析指标: overview(综合), processing_time(时效), rejection_rate(拒赔率), amount_distribution(金额分布)",
        },
        "dimensions": {
            "type": "array",
            "items": {"type": "string"},
            "description": "分组维度，如 ['product_type'], ['region'], ['claim_type']",
        },
        "filters": {
            "type": "object",
            "description": "过滤条件，如 {\"region\": \"华东\", \"claim_status\": \"已结案\"}",
        },
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        metric = params.get("metric", "overview")
        dims = params.get("dimensions", ["product_type"])
        filters = params.get("filters", {})

        conditions = [f"{col} = '{val}'" for col, val in filters.items()]
        where = ""
        if conditions:
            where = "\nWHERE " + " AND ".join(conditions)

        group_cols = ", ".join(dims)

        if metric == "processing_time":
            return f"""SELECT
    {group_cols},
    ROUND(AVG(processing_days), 1) AS avg_days,
    MIN(processing_days) AS min_days,
    MAX(processing_days) AS max_days,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY processing_days) AS median_days,
    COUNT(*) AS claim_count
FROM claims{where}
GROUP BY {group_cols}
ORDER BY avg_days DESC"""

        elif metric == "rejection_rate":
            return f"""SELECT
    {group_cols},
    COUNT(*) AS total_claims,
    SUM(CASE WHEN claim_status = '已拒赔' THEN 1 ELSE 0 END) AS rejected_count,
    ROUND(SUM(CASE WHEN claim_status = '已拒赔' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS rejection_rate_pct,
    SUM(CASE WHEN claim_status = '已结案' THEN 1 ELSE 0 END) AS settled_count,
    SUM(CASE WHEN claim_status = '审核中' THEN 1 ELSE 0 END) AS pending_count
FROM claims{where}
GROUP BY {group_cols}
ORDER BY rejection_rate_pct DESC"""

        elif metric == "amount_distribution":
            return f"""SELECT
    {group_cols},
    COUNT(*) AS claim_count,
    ROUND(SUM(claim_amount), 2) AS total_claim_amount,
    ROUND(SUM(paid_amount), 2) AS total_paid_amount,
    ROUND(AVG(claim_amount), 2) AS avg_claim_amount,
    ROUND(AVG(paid_amount), 2) AS avg_paid_amount,
    ROUND(SUM(paid_amount) / NULLIF(SUM(claim_amount), 0) * 100, 2) AS paid_ratio_pct
FROM claims{where}
GROUP BY {group_cols}
ORDER BY total_claim_amount DESC"""

        else:  # overview
            return f"""SELECT
    {group_cols},
    COUNT(*) AS total_claims,
    ROUND(SUM(claim_amount), 2) AS total_claim_amount,
    ROUND(SUM(paid_amount), 2) AS total_paid_amount,
    ROUND(AVG(processing_days), 1) AS avg_processing_days,
    ROUND(SUM(CASE WHEN claim_status = '已拒赔' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS rejection_rate_pct,
    ROUND(SUM(paid_amount) / NULLIF(SUM(claim_amount), 0) * 100, 2) AS paid_ratio_pct
FROM claims{where}
GROUP BY {group_cols}
ORDER BY total_claims DESC"""


registry.register(ClaimAnalysisSkill())
