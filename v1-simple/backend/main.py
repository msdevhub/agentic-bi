"""Agentic BI POC - FastAPI Backend"""
from __future__ import annotations
import json
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from .skills import general_query, year_over_year, top_n, trend  # noqa: F401
from .skills import loss_ratio, claim_analysis, customer_profile, product_mix, channel_performance  # noqa: F401
from .skills.registry import registry
from .agents.router import RouterAgent, ROUTER_SYSTEM_PROMPT
from .agents.executor import ExecutorAgent
from .agents.reviewer import ReviewerAgent, REVIEWER_SYSTEM_PROMPT
from .agents.base import load_config, save_config, reload_config, AVAILABLE_MODELS
from .db.engine import get_connection, get_schema_info, execute_sql as db_execute_sql
from .session import session_manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_connection()
    print(f"🔧 已注册 {len(registry.list_skills())} 个技能: {[s.name for s in registry.list_skills()]}")
    yield


app = FastAPI(title="Agentic BI POC", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router_agent = RouterAgent()
executor_agent = ExecutorAgent()
reviewer_agent = ReviewerAgent()

MAX_CORRECTION_RETRIES = 2


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


@app.get("/api/health")
async def health():
    return {"status": "ok", "skills": [s.name for s in registry.list_skills()]}


@app.get("/api/schema")
async def schema():
    return {"schema": get_schema_info()}


@app.get("/api/system-config")
async def system_config():
    import os
    skills_info = []
    for skill in registry.list_skills():
        skills_info.append({
            "name": skill.name,
            "description": skill.description,
            "parameters": skill.parameters_schema,
        })
    tables_info = []
    for t in get_schema_info():
        count = db_execute_sql(f"SELECT COUNT(*) AS cnt FROM {t['table']}")
        sample = db_execute_sql(f"SELECT * FROM {t['table']} LIMIT 3")
        tables_info.append({
            "table": t["table"],
            "columns": t["columns"],
            "row_count": count["data"][0]["cnt"] if count["success"] else 0,
            "sample_data": sample["data"] if sample["success"] else [],
        })
    return {
        "agents": [
            {
                "name": "Router Agent",
                "role": "意图识别与技能路由",
                "description": "理解用户自然语言问题，通过 Function Calling 选择最合适的分析技能并提取参数。支持多轮对话上下文理解。",
                "model": load_config()["agents"]["router"]["model"],
                "system_prompt": ROUTER_SYSTEM_PROMPT,
            },
            {
                "name": "Executor Agent",
                "role": "SQL 生成与执行",
                "description": "调用选中的技能生成 SQL，在 DuckDB 中执行并返回结构化结果",
                "model": "N/A (无 LLM 调用)",
                "system_prompt": "Executor 不使用 LLM。它根据技能（Skill）的 generate_sql() 方法生成 SQL，然后在 DuckDB 中执行。",
            },
            {
                "name": "Reviewer Agent",
                "role": "结果审核与摘要 + Self-Correction",
                "description": "审核查询结果，生成摘要。若发现问题（is_valid=false），触发自动修正循环（最多重试2次）。",
                "model": load_config()["agents"]["reviewer"]["model"],
                "system_prompt": REVIEWER_SYSTEM_PROMPT,
            },
        ],
        "skills": skills_info,
        "tables": tables_info,
        "architecture": {
            "flow": "用户提问 → Router (LLM, 含对话上下文) → Executor (Skill + DuckDB) → Reviewer (LLM) → [若无效: 自动修正重试] → 返回结果",
            "features": ["多轮对话上下文", "Self-Correction 自动修正", "SSE 流式推理链"],
            "tech_stack": {
                "backend": "Python + FastAPI + SSE",
                "database": "DuckDB (in-process OLAP)",
                "llm": f"Azure OpenAI (Router: {load_config()['agents']['router']['model']}, Reviewer: {load_config()['agents']['reviewer']['model']})",
                "frontend": "React + TypeScript + Recharts",
            },
        },
    }


# ─── Config API ──────────────────────────────────────────────
class ConfigUpdateRequest(BaseModel):
    agents: dict = Field(default_factory=dict)


@app.get("/api/config")
async def get_config():
    """获取当前模型配置"""
    cfg = reload_config()
    return {
        "agents": cfg.get("agents", {}),
        "available_models": cfg.get("available_models", AVAILABLE_MODELS),
    }


@app.put("/api/config")
async def update_config(req: ConfigUpdateRequest):
    """更新模型配置"""
    cfg = load_config()
    for agent_name, agent_cfg in req.agents.items():
        if agent_name in cfg["agents"]:
            model = agent_cfg.get("model", "")
            if model and model in AVAILABLE_MODELS:
                cfg["agents"][agent_name]["model"] = model
    save_config(cfg)
    return {"status": "ok", "agents": cfg["agents"]}


@app.post("/api/chat")
async def chat(req: ChatRequest):
    session = session_manager.get_or_create(req.session_id)

    async def event_stream():
        # 通知前端 session_id
        yield {"event": "session", "data": json.dumps({"session_id": session.session_id})}

        # 获取对话上下文
        context = session.get_context()
        session.add_user(req.message)

        attempt = 0
        correction_hint = ""
        final_router = None
        final_exec = None
        final_review = None

        while attempt <= MAX_CORRECTION_RETRIES:
            attempt += 1
            is_retry = attempt > 1

            # --- Router ---
            if is_retry:
                yield {"event": "step", "data": json.dumps({
                    "agent": "router",
                    "status": "running",
                    "message": f"🔄 自动修正中（第{attempt-1}次重试）...",
                }, ensure_ascii=False)}
                # 将修正提示加入消息
                augmented_message = f"{req.message}\n\n[修正提示: {correction_hint}]"
            else:
                yield {"event": "step", "data": json.dumps({
                    "agent": "router",
                    "status": "running",
                    "message": "🧭 正在理解你的问题...",
                }, ensure_ascii=False)}
                augmented_message = req.message

            router_result = await router_agent.run(augmented_message, context=context)
            final_router = router_result

            # --- 反问澄清 ---
            if router_result.get("needs_clarification"):
                params = router_result["parameters"]
                question = params.get("question", "能否提供更多信息？")
                options = params.get("options", [])
                missing = params.get("missing_params", [])

                yield {"event": "step", "data": json.dumps({
                    "agent": "router",
                    "status": "done",
                    "message": f"❓ 需要补充信息",
                    "detail": {
                        "skill_name": "ask_clarification",
                        "reasoning": "用户问题需要补充参数",
                        "missing_params": missing,
                    },
                }, ensure_ascii=False)}

                # 保存到对话历史
                session.add_assistant(summary=question)

                yield {"event": "clarification", "data": json.dumps({
                    "question": question,
                    "options": options,
                    "missing_params": missing,
                    "session_id": session.session_id,
                }, ensure_ascii=False)}
                return

            yield {"event": "step", "data": json.dumps({
                "agent": "router",
                "status": "done",
                "message": f"{'🔄' if is_retry else '✅'} 选择技能: {router_result['skill_name']}",
                "detail": router_result,
            }, ensure_ascii=False)}

            # --- Executor ---
            yield {"event": "step", "data": json.dumps({
                "agent": "executor",
                "status": "running",
                "message": f"⚙️ 正在执行分析 ({router_result['skill_name']})...",
            }, ensure_ascii=False)}

            exec_result = await executor_agent.run(
                skill_name=router_result["skill_name"],
                parameters=router_result["parameters"],
            )
            final_exec = exec_result

            yield {"event": "step", "data": json.dumps({
                "agent": "executor",
                "status": "done",
                "message": f"{'✅' if exec_result['success'] else '❌'} SQL 执行{'完成' if exec_result['success'] else '失败'}，{exec_result['row_count']} 行结果",
                "detail": {
                    "sql": exec_result["sql"],
                    "success": exec_result["success"],
                    "row_count": exec_result["row_count"],
                    "chart_suggestion": exec_result["chart_suggestion"],
                    "error": exec_result.get("error", ""),
                },
            }, ensure_ascii=False)}

            # SQL 执行失败 → 直接重试
            if not exec_result["success"]:
                if attempt <= MAX_CORRECTION_RETRIES:
                    correction_hint = f"上次 SQL 执行报错: {exec_result.get('error', '未知错误')}。请换一种方式生成查询。"
                    yield {"event": "step", "data": json.dumps({
                        "agent": "reviewer",
                        "status": "done",
                        "message": f"⚠️ SQL 执行失败，自动重试...",
                        "detail": {"is_valid": False, "correction_hint": correction_hint},
                    }, ensure_ascii=False)}
                    continue
                else:
                    final_review = {
                        "summary": f"查询执行失败: {exec_result.get('error', '未知错误')}",
                        "is_valid": False,
                        "suggestions": ["请尝试换一种方式提问"],
                        "correction_hint": "",
                    }
                    break

            # --- Reviewer ---
            yield {"event": "step", "data": json.dumps({
                "agent": "reviewer",
                "status": "running",
                "message": "🔍 正在审核结果...",
            }, ensure_ascii=False)}

            review_result = await reviewer_agent.run(
                user_message=req.message,
                sql=exec_result["sql"],
                data=exec_result["data"],
                columns=exec_result["columns"],
            )
            final_review = review_result

            # 构建 Reviewer 消息：审核未通过时附带原因
            if review_result.get("is_valid", True):
                review_msg = "✅ 审核通过"
            else:
                reason = review_result.get("summary", "") or review_result.get("correction_hint", "")
                review_msg = f"⚠️ 审核未通过 — {reason}" if reason else "⚠️ 审核未通过"

            yield {"event": "step", "data": json.dumps({
                "agent": "reviewer",
                "status": "done",
                "message": review_msg,
                "detail": review_result,
            }, ensure_ascii=False)}

            # 审核通过 → 结束循环
            if review_result.get("is_valid", True):
                break

            # 审核未通过 → 自动修正
            correction_hint = review_result.get("correction_hint", "请重新分析用户问题，换一种查询方式。")
            if attempt <= MAX_CORRECTION_RETRIES:
                yield {"event": "step", "data": json.dumps({
                    "agent": "reviewer",
                    "status": "running",
                    "message": f"🔄 审核未通过，触发自动修正...",
                }, ensure_ascii=False)}

        # 保存到对话历史
        summary = final_review.get("summary", "分析完成") if final_review else "分析完成"
        session.add_assistant(
            summary=summary,
            sql=final_exec["sql"] if final_exec else "",
            skill=final_router["skill_name"] if final_router else "",
        )

        # Final result
        yield {"event": "result", "data": json.dumps({
            "session_id": session.session_id,
            "attempts": attempt,
            "router": final_router,
            "executor": {
                "sql": final_exec["sql"] if final_exec else "",
                "data": final_exec["data"] if final_exec else [],
                "columns": final_exec["columns"] if final_exec else [],
                "row_count": final_exec["row_count"] if final_exec else 0,
                "chart_suggestion": final_exec["chart_suggestion"] if final_exec else "table",
                "success": final_exec["success"] if final_exec else False,
            },
            "reviewer": final_review or {"summary": "未完成审核", "is_valid": False, "suggestions": []},
        }, ensure_ascii=False)}

    return EventSourceResponse(event_stream())


# --- 静态文件服务 ---
FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        file_path = FRONTEND_DIST / path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(FRONTEND_DIST / "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=28880, reload=True)
