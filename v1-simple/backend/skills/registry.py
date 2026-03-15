"""技能基类和注册表"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any


class BaseSkill(ABC):
    """分析技能基类"""

    name: str = ""
    description: str = ""
    parameters_schema: dict = {}

    @abstractmethod
    def generate_sql(self, params: dict[str, Any]) -> str:
        """根据参数生成 SQL"""
        ...

    def to_tool_schema(self) -> dict:
        """转为 OpenAI function calling 格式"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters_schema,
                    "required": list(self.parameters_schema.keys()),
                },
            },
        }


class SkillRegistry:
    """技能注册表"""

    def __init__(self):
        self._skills: dict[str, BaseSkill] = {}

    def register(self, skill: BaseSkill):
        self._skills[skill.name] = skill

    def get(self, name: str) -> BaseSkill | None:
        return self._skills.get(name)

    def list_skills(self) -> list[BaseSkill]:
        return list(self._skills.values())

    def get_tool_schemas(self) -> list[dict]:
        schemas = [s.to_tool_schema() for s in self._skills.values()]
        # 追加「反问澄清」工具
        schemas.append({
            "type": "function",
            "function": {
                "name": "ask_clarification",
                "description": "当用户问题不够明确、缺少必要参数时调用此工具，向用户反问以补充信息。例如：用户说'指定类型产品的增长率'但没说哪个类型。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "向用户提出的澄清问题，用中文，简洁明了",
                        },
                        "missing_params": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "缺失的参数名列表，如 ['product_type', 'year']",
                        },
                        "options": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "可选值建议列表，帮助用户快速选择。如 ['寿险', '健康险', '意外险']",
                        },
                    },
                    "required": ["question"],
                },
            },
        })
        return schemas


# 全局注册表
registry = SkillRegistry()
