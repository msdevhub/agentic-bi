"""渠道绩效分析技能"""
from typing import Any
from .registry import BaseSkill, registry


class ChannelPerformanceSkill(BaseSkill):
    name = "channel_performance"
    description = (
        "分析渠道绩效：件均保费、佣金率、新单率、代理人产能。"
        "适用于'各渠道保费对比'、'渠道佣金率'、'代理人人均产能'、'代理人排名'等问题。"
    )
    parameters_schema = {
        "metric": {
            "type": "string",
            "enum": ["channel_overview", "commission_analysis", "agent_productivity", "agent_ranking"],
            "description": "channel_overview(渠道概览), commission_analysis(佣金分析), agent_productivity(代理人产能), agent_ranking(代理人排名)",
        },
        "dimension": {
            "type": "string",
            "description": "分组维度（仅部分指标用）: channel, region. 默认 channel",
        },
        "n": {
            "type": "integer",
            "description": "排名数（agent_ranking 用），默认 20",
        },
        "filters": {
            "type": "object",
            "description": "过滤条件",
        },
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        metric = params.get("metric", "channel_overview")
        dimension = params.get("dimension", "channel")
        n = params.get("n", 20)
        filters = params.get("filters", {})

        conditions = [f"{col} = '{val}'" for col, val in filters.items()]

        if metric == "channel_overview":
            where = ""
            if conditions:
                where = "\nWHERE " + " AND ".join(conditions)
            return f"""SELECT
    {dimension},
    COUNT(*) AS policy_count,
    SUM(premium) AS total_premium,
    ROUND(AVG(premium), 2) AS avg_premium,
    SUM(commission) AS total_commission,
    ROUND(SUM(commission) / NULLIF(SUM(premium), 0) * 100, 2) AS commission_rate_pct,
    SUM(CASE WHEN is_new_business THEN 1 ELSE 0 END) AS new_business_count,
    ROUND(SUM(CASE WHEN is_new_business THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) AS new_biz_ratio_pct
FROM policies{where}
GROUP BY {dimension}
ORDER BY total_premium DESC"""

        elif metric == "commission_analysis":
            where = ""
            if conditions:
                where = "\nWHERE " + " AND ".join(conditions)
            return f"""SELECT
    channel,
    product_type,
    COUNT(*) AS policy_count,
    ROUND(SUM(commission), 2) AS total_commission,
    ROUND(AVG(commission), 2) AS avg_commission,
    ROUND(SUM(commission) / NULLIF(SUM(premium), 0) * 100, 2) AS commission_rate_pct
FROM policies{where}
GROUP BY channel, product_type
ORDER BY total_commission DESC"""

        elif metric == "agent_productivity":
            p_conds = [f"p.{c}" if not c.startswith('a.') else c for c in conditions]
            where = ""
            if p_conds:
                where = " AND " + " AND ".join(p_conds)
            return f"""SELECT
    a.region,
    a.level,
    COUNT(DISTINCT a.agent_id) AS agent_count,
    COUNT(p.policy_id) AS total_policies,
    ROUND(SUM(p.premium), 2) AS total_premium,
    ROUND(SUM(p.premium) / NULLIF(COUNT(DISTINCT a.agent_id), 0), 2) AS premium_per_agent,
    ROUND(COUNT(p.policy_id) * 1.0 / NULLIF(COUNT(DISTINCT a.agent_id), 0), 1) AS policies_per_agent
FROM agents a
LEFT JOIN policies p ON a.agent_id = p.agent_id{where}
WHERE a.agent_status = '在职'
GROUP BY a.region, a.level
ORDER BY premium_per_agent DESC"""

        else:  # agent_ranking
            a_conds = [f"a.{c}" if not c.startswith('p.') else c for c in conditions]
            where = ""
            if a_conds:
                where = " AND " + " AND ".join(a_conds)
            return f"""SELECT
    a.agent_id,
    a.agent_name,
    a.region,
    a.level,
    a.team,
    COUNT(p.policy_id) AS policy_count,
    ROUND(SUM(p.premium), 2) AS total_premium,
    ROUND(AVG(p.premium), 2) AS avg_premium
FROM agents a
LEFT JOIN policies p ON a.agent_id = p.agent_id
WHERE a.agent_status = '在职'{where}
GROUP BY a.agent_id, a.agent_name, a.region, a.level, a.team
ORDER BY total_premium DESC
LIMIT {n}"""


registry.register(ChannelPerformanceSkill())
