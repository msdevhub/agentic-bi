"""Reviewer Agent - 审核结果、生成摘要、推荐下一步（支持 self-correction）"""
from __future__ import annotations
import json
from .base import BaseAgent, get_llm_client, get_model_name


REVIEWER_SYSTEM_PROMPT = """你是一个 BI 分析助手的审核 Agent。你的职责是：
1. 检查 SQL 查询结果是否合理回答了用户的问题
2. 用简洁的中文总结分析结果（2-3句话）
3. 推荐 2-3 个后续分析方向
4. 如果结果有问题（空结果、SQL逻辑错误、没有回答用户问题），标记 is_valid=false 并说明原因

请用 JSON 格式回复：
{
    "summary": "结果摘要",
    "is_valid": true/false,
    "suggestions": ["建议1", "建议2", "建议3"],
    "correction_hint": "如果 is_valid=false，这里描述应该如何修正查询（给 Router 的提示）"
}

只返回 JSON，不要其他内容。"""


class ReviewerAgent(BaseAgent):
    name = "reviewer"
    role = "结果审核与摘要"

    async def run(self, user_message: str, sql: str, data: list, columns: list) -> dict:
        client = get_llm_client()

        sample_data = data[:10]

        user_content = f"""用户问题: {user_message}

执行的 SQL:
{sql}

查询结果（前10行）:
列: {columns}
数据: {json.dumps(sample_data, ensure_ascii=False, default=str)}

总行数: {len(data)}"""

        try:
            response = await client.chat.completions.create(
                model=get_model_name("reviewer"),
                messages=[
                    {"role": "system", "content": REVIEWER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content or "{}"
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[-1].rsplit("```", 1)[0]

            result = json.loads(content)
            result.setdefault("correction_hint", "")
            result["reasoning"] = "结果审核完成"
            return result

        except json.JSONDecodeError:
            return {
                "summary": content if 'content' in dir() else "审核完成",
                "is_valid": True,
                "suggestions": [],
                "correction_hint": "",
                "reasoning": "审核结果非标准 JSON，已直接使用文本",
            }
        except Exception as e:
            return {
                "summary": f"审核出错: {str(e)}",
                "is_valid": True,
                "suggestions": [],
                "correction_hint": "",
                "reasoning": f"Reviewer 出错: {str(e)}",
                "error": str(e),
            }
