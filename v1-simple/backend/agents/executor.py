"""Executor Agent - 调用技能生成 SQL 并执行"""
from __future__ import annotations
from .base import BaseAgent
from ..skills.registry import registry
from ..db.engine import execute_sql


class ExecutorAgent(BaseAgent):
    name = "executor"
    role = "SQL 生成与执行"

    async def run(self, skill_name: str, parameters: dict) -> dict:
        skill = registry.get(skill_name)
        if not skill:
            return {
                "success": False,
                "error": f"未找到技能: {skill_name}",
                "sql": "",
                "data": [],
                "columns": [],
                "reasoning": f"技能 {skill_name} 不存在",
            }

        try:
            sql = skill.generate_sql(parameters)
        except Exception as e:
            return {
                "success": False,
                "error": f"SQL 生成失败: {str(e)}",
                "sql": "",
                "data": [],
                "columns": [],
                "reasoning": f"技能 {skill_name} 生成 SQL 时出错",
            }

        result = execute_sql(sql)

        # 推荐图表类型
        chart = self._suggest_chart(skill_name, result)

        return {
            "success": result["success"],
            "sql": sql,
            "data": result["data"][:200],  # 限制返回行数
            "columns": result["columns"],
            "row_count": result["row_count"],
            "error": result.get("error", ""),
            "chart_suggestion": chart,
            "reasoning": f"使用技能 {skill_name} 生成 SQL 并执行，返回 {result['row_count']} 行",
        }

    def _suggest_chart(self, skill_name: str, result: dict) -> str:
        """根据技能类型推荐图表"""
        if not result["success"]:
            return "table"
        chart_map = {
            "trend": "line",
            "top_n": "bar",
            "year_over_year": "bar",
            "general_query": "bar",
            "loss_ratio": "bar",
            "claim_analysis": "bar",
            "customer_profile": "bar",
            "product_mix": "bar",
            "channel_performance": "bar",
        }
        # 默认也给 bar，除非只有 1 行数据
        default = "bar" if result.get("row_count", 0) > 1 else "table"
        return chart_map.get(skill_name, default)
