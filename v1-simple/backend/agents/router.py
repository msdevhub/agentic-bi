"""Router Agent - 理解用户意图，选择技能，提取参数（支持多轮对话上下文）"""
from __future__ import annotations
import json
from .base import BaseAgent, get_llm_client, get_model_name
from ..skills.registry import registry


ROUTER_SYSTEM_PROMPT = """你是一个保险行业 BI 分析助手的路由 Agent。你的职责是：
1. 理解用户的自然语言问题（结合对话上下文）
2. 选择最合适的分析技能（通过 function calling）
3. 提取正确的参数

可用的数据表:
1. policies（保单表）
   列: policy_id, policy_date(日期), region(地区), channel(渠道), product_type(险种大类), product_name(产品名),
       premium(保费), sum_insured(保额), commission(佣金), policy_status(保单状态),
       customer_age(客户年龄), customer_gender(客户性别), payment_years(缴费年限), is_new_business(是否新单),
       agent_id(代理人ID，关联 agents 表)

2. claims（理赔表）
   列: claim_id, claim_date(日期), policy_id, region(地区), product_type(险种大类),
       claim_type(理赔类型), claim_amount(理赔申请金额), paid_amount(实际赔付金额),
       claim_status(理赔状态: 已结案/审核中/已拒赔/待补充材料), processing_days(处理天数)

3. agents（代理人表）
   列: agent_id, agent_name(姓名), region(地区), team(团队), level(级别: 初级/中级/高级/总监),
       join_date(入职日期), agent_status(状态: 在职/离职/停牌),
       total_premium(累计保费), policy_count(保单数), customer_count(客户数)

4. renewals（续保表）
   列: renewal_id, policy_id, renewal_date(续保日期), renewal_year(续保年份),
       renewal_premium(续保保费), renewal_status(状态: 已续保/已失效/宽限期),
       lapse_reason(失效原因)

维度值:
- 地区: 华东, 华南, 华北, 华中, 西南, 西北, 东北, 港澳
- 渠道: 代理人, 银保, 电销, 互联网, 经纪, 团险直销
- 险种大类: 寿险, 健康险, 意外险, 年金险, 投连险, 万能险
- 理赔类型: 重疾, 住院, 身故, 意外医疗, 门诊, 残疾

技能选择指南：
- 赔付率相关 → loss_ratio（跨 policies + claims JOIN）
- 理赔深度分析（时效、拒赔率、金额分布）→ claim_analysis
- 客户画像（年龄、性别、交叉分析）→ customer_profile
- 产品结构（占比、新单率、续保率）→ product_mix
- 渠道绩效（佣金、代理人产能/排名）→ channel_performance
- 简单排名 → top_n
- 时间趋势 → trend
- 同比分析 → year_over_year
- 其他复杂查询 → general_query

重要规则：
- 用户可能会引用之前的对话内容（如"按地区拆分"、"换成趋势图"、"只看华东的"）
- 当用户的问题不完整时，结合对话历史理解完整意图
- 使用 filters 参数传入过滤条件，格式为 {"列名": "值"}
  例如: {"region": "华东"}, {"product_type": "寿险"}, {"channel": "代理人"}

何时反问用户（调用 ask_clarification）：
- 用户明确提到"指定"、"某个"、"特定"类型/地区/产品，但没说具体是哪个
  例如: "指定类型产品的增长率" → 反问"您想分析哪个险种？"并提供选项
- 用户的问题存在歧义，可以有多种理解方式
  例如: "保险的趋势" → 反问是保费趋势还是保单数趋势？按月还是按季度？
- 用户提到了不存在的维度或指标

何时不反问（直接选技能执行）：
- 问题已经足够明确，如"各险种赔付率排名"、"2024年月度保费趋势"
- 问题是开放性但可以合理默认，如"保费最高的地区" → 直接用 top_n
- 用户说"所有"、"各"、"每个" → 不需要指定，直接分组查询

请根据用户问题选择最合适的分析技能并填入正确的参数。"""


class RouterAgent(BaseAgent):
    name = "router"
    role = "意图识别与技能路由"

    async def run(self, message: str, context: str = "") -> dict:
        client = get_llm_client()
        tools = registry.get_tool_schemas()

        messages = [{"role": "system", "content": ROUTER_SYSTEM_PROMPT}]

        if context:
            messages.append({"role": "system", "content": context})

        messages.append({"role": "user", "content": message})

        try:
            response = await client.chat.completions.create(
                model=get_model_name("router"),
                messages=messages,
                tools=tools,
                tool_choice="required",
            )

            choice = response.choices[0]
            tool_call = choice.message.tool_calls[0] if choice.message.tool_calls else None

            if tool_call:
                skill_name = tool_call.function.name
                params = json.loads(tool_call.function.arguments)

                if skill_name == "ask_clarification":
                    return {
                        "skill_name": "ask_clarification",
                        "parameters": params,
                        "reasoning": "用户问题需要补充信息",
                        "needs_clarification": True,
                        "raw_response": choice.message.content or "",
                    }

                reasoning = f"识别到分析意图，选择技能: {skill_name}"
            else:
                skill_name = "general_query"
                params = {"sql": "SELECT COUNT(*) AS total_policies FROM policies"}
                reasoning = "未能匹配特定技能，使用通用查询"

            return {
                "skill_name": skill_name,
                "parameters": params,
                "reasoning": reasoning,
                "raw_response": choice.message.content or "",
            }

        except Exception as e:
            return {
                "skill_name": "general_query",
                "parameters": {"sql": "SELECT COUNT(*) AS total_policies FROM policies"},
                "reasoning": f"Router 出错: {str(e)}，回退到通用查询",
                "error": str(e),
            }
