"""Agent 基类 + LLM 客户端 + 配置管理"""
from __future__ import annotations
import os
import yaml
from pathlib import Path
from openai import AsyncAzureOpenAI, AsyncOpenAI

_client: AsyncAzureOpenAI | AsyncOpenAI | None = None
_config: dict | None = None

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.yaml"

AVAILABLE_MODELS = [
    "gpt-5.4", "gpt-5.2", "gpt-4o", "gpt-4.1", "gpt-5.2-chat", "gpt-5.2-codex"
]

DEFAULT_CONFIG = {
    "agents": {
        "router": {"model": "gpt-4.1", "description": "意图识别与技能路由"},
        "reviewer": {"model": "gpt-4o", "description": "结果审核与摘要生成"},
    },
    "available_models": AVAILABLE_MODELS,
}


def load_config() -> dict:
    """加载配置文件（带缓存）"""
    global _config
    if _config is not None:
        return _config
    _config = _load_config_from_disk()
    return _config


def _load_config_from_disk() -> dict:
    """从磁盘加载配置"""
    try:
        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f) or {}
            # 确保结构完整
            cfg.setdefault("agents", {})
            cfg["agents"].setdefault("router", DEFAULT_CONFIG["agents"]["router"])
            cfg["agents"].setdefault("reviewer", DEFAULT_CONFIG["agents"]["reviewer"])
            cfg.setdefault("available_models", AVAILABLE_MODELS)
            return cfg
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict) -> None:
    """保存配置到磁盘并刷新缓存"""
    global _config
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False, sort_keys=False)
    _config = cfg


def reload_config() -> dict:
    """强制重新加载配置"""
    global _config
    _config = None
    return load_config()


def get_llm_client() -> AsyncAzureOpenAI | AsyncOpenAI:
    """获取 LLM 客户端（单例）- 支持 Azure OpenAI 和标准 OpenAI"""
    global _client
    if _client is None:
        base_url = os.getenv("OPENAI_BASE_URL", "")
        api_key = os.getenv("OPENAI_API_KEY", "")

        if "azure" in base_url.lower() or os.getenv("AZURE_OPENAI", ""):
            endpoint = base_url.split("/openai")[0] if "/openai" in base_url else base_url
            _client = AsyncAzureOpenAI(
                api_key=api_key,
                azure_endpoint=endpoint,
                api_version=os.getenv("AZURE_API_VERSION", "2024-12-01-preview"),
            )
        else:
            _client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url or "https://api.openai.com/v1",
            )
    return _client


def get_model_name(agent_name: str = "") -> str:
    """获取指定 agent 的模型名称"""
    cfg = load_config()
    if agent_name and agent_name in cfg.get("agents", {}):
        return cfg["agents"][agent_name].get("model", "gpt-4o")
    return os.getenv("MODEL_NAME", "gpt-4o")


class BaseAgent:
    """Agent 基类"""
    name: str = "base"
    role: str = ""

    async def run(self, **kwargs) -> dict:
        raise NotImplementedError
