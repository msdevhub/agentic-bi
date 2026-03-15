"""通用 SQL 查询技能"""
from typing import Any
from .registry import BaseSkill, registry


class GeneralQuerySkill(BaseSkill):
    name = "general_query"
    description = (
        "执行通用 SQL 查询。当其他技能无法匹配用户需求时使用此技能。"
        "可用表: policies(保单)、claims(理赔)。"
    )
    parameters_schema = {
        "sql": {
            "type": "string",
            "description": (
                "要执行的 SQL 查询语句。"
                "表 policies 列: policy_id, policy_date, region, channel, product_type, product_name, "
                "premium, sum_insured, commission, policy_status, customer_age, customer_gender, payment_years, is_new_business. "
                "表 claims 列: claim_id, claim_date, policy_id, region, product_type, claim_type, "
                "claim_amount, paid_amount, claim_status, processing_days."
            ),
        }
    }

    def generate_sql(self, params: dict[str, Any]) -> str:
        return params["sql"]


registry.register(GeneralQuerySkill())
