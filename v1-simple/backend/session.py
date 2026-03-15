"""对话会话管理 - 维护多轮对话上下文"""
from __future__ import annotations
import uuid
import time
from dataclasses import dataclass, field


@dataclass
class Turn:
    """一轮对话"""
    role: str  # user | assistant
    content: str
    sql: str = ""
    skill: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class Session:
    """对话会话"""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    turns: list[Turn] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def add_user(self, message: str):
        self.turns.append(Turn(role="user", content=message))

    def add_assistant(self, summary: str, sql: str = "", skill: str = ""):
        self.turns.append(Turn(role="assistant", content=summary, sql=sql, skill=skill))

    def get_context(self, max_turns: int = 6) -> str:
        """生成对话上下文摘要，供 Router 使用"""
        recent = self.turns[-(max_turns * 2):]  # 最近 N 轮
        if not recent:
            return ""

        lines = ["以下是之前的对话历史："]
        for t in recent:
            if t.role == "user":
                lines.append(f"用户: {t.content}")
            else:
                detail = f"（技能: {t.skill}, SQL: {t.sql[:80]}...）" if t.sql else ""
                lines.append(f"助手: {t.content}{detail}")
        return "\n".join(lines)


class SessionManager:
    """会话管理器 - 内存存储"""

    def __init__(self, max_sessions: int = 100, expire_seconds: int = 3600):
        self._sessions: dict[str, Session] = {}
        self._max = max_sessions
        self._expire = expire_seconds

    def get_or_create(self, session_id: str | None = None) -> Session:
        self._cleanup()
        if session_id and session_id in self._sessions:
            return self._sessions[session_id]
        session = Session()
        self._sessions[session.session_id] = session
        return session

    def _cleanup(self):
        now = time.time()
        expired = [k for k, v in self._sessions.items() if now - v.created_at > self._expire]
        for k in expired:
            del self._sessions[k]
        # LRU: 超出数量限制时删除最老的
        while len(self._sessions) > self._max:
            oldest = min(self._sessions, key=lambda k: self._sessions[k].created_at)
            del self._sessions[oldest]


# 全局实例
session_manager = SessionManager()
