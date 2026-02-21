from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Protocol

try:
    from redis import asyncio as aioredis
    from redis.exceptions import WatchError
except ModuleNotFoundError:  # pragma: no cover
    aioredis = None
    WatchError = Exception

MAX_HISTORY = int(os.getenv("COEDIT_MAX_HISTORY", "25"))


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def resolve_conflict(current: str, incoming: str) -> str:
    if incoming == current:
        return current
    if current and current in incoming:
        return incoming
    if incoming and incoming in current:
        return current
    separator = "\n\n"
    return f"{current}{separator}{incoming}" if current else incoming


@dataclass
class ParticipantRecord:
    user_id: str
    user_name: str
    joined_at: str


@dataclass
class SessionRecord:
    session_id: str
    document_id: str
    tenant_id: str
    content: str
    version: int
    created_at: str
    updated_at: str
    participants: dict[str, ParticipantRecord] = field(default_factory=dict)
    cursors: dict[str, Any] = field(default_factory=dict)
    conflicts: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class HistoryRecord:
    version: int
    content: str
    updated_at: str
    updated_by: str | None
    conflict: dict[str, Any] | None = None


class SessionStore(Protocol):
    async def create(self, session: SessionRecord) -> SessionRecord: ...

    async def get(self, session_id: str) -> SessionRecord | None: ...

    async def delete(self, session_id: str) -> SessionRecord | None: ...

    async def update_content(
        self, session_id: str, incoming_content: str, base_version: int, updated_by: str
    ) -> tuple[SessionRecord | None, dict[str, Any] | None]: ...

    async def add_conflict(self, session_id: str, conflict: dict[str, Any]) -> SessionRecord | None: ...

    async def healthy(self) -> bool: ...


class PresenceStore(Protocol):
    async def add_participant(self, session_id: str, participant: ParticipantRecord) -> SessionRecord | None: ...

    async def remove_participant(self, session_id: str, user_id: str) -> SessionRecord | None: ...

    async def update_cursor(self, session_id: str, user_id: str, cursor: dict[str, Any]) -> SessionRecord | None: ...

    async def clear_cursor(self, session_id: str, user_id: str) -> SessionRecord | None: ...

    async def healthy(self) -> bool: ...


class HistoryStore(Protocol):
    async def append(self, document_id: str, entry: HistoryRecord) -> None: ...

    async def list(self, document_id: str) -> list[HistoryRecord]: ...

    async def healthy(self) -> bool: ...


class PubSubBroker(Protocol):
    async def publish(self, channel: str, payload: dict[str, Any]) -> None: ...

    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]: ...

    async def healthy(self) -> bool: ...


class InMemoryState:
    def __init__(self) -> None:
        self.sessions: dict[str, SessionRecord] = {}
        self.history: dict[str, list[HistoryRecord]] = {}
        self.lock = asyncio.Lock()
        self.subscribers: dict[str, set[asyncio.Queue[dict[str, Any]]]] = {}


_INMEMORY_STATES: dict[str, InMemoryState] = {}


def _state(namespace: str) -> InMemoryState:
    if namespace not in _INMEMORY_STATES:
        _INMEMORY_STATES[namespace] = InMemoryState()
    return _INMEMORY_STATES[namespace]


class InMemoryBackend(SessionStore, PresenceStore, HistoryStore, PubSubBroker):
    def __init__(self, namespace: str = "default") -> None:
        self.state = _state(namespace)

    async def create(self, session: SessionRecord) -> SessionRecord:
        async with self.state.lock:
            self.state.sessions[session.session_id] = session
            return session

    async def get(self, session_id: str) -> SessionRecord | None:
        return self.state.sessions.get(session_id)

    async def delete(self, session_id: str) -> SessionRecord | None:
        async with self.state.lock:
            return self.state.sessions.pop(session_id, None)

    async def update_content(
        self, session_id: str, incoming_content: str, base_version: int, updated_by: str
    ) -> tuple[SessionRecord | None, dict[str, Any] | None]:
        async with self.state.lock:
            session = self.state.sessions.get(session_id)
            if not session:
                return None, None
            conflict: dict[str, Any] | None = None
            if base_version != session.version:
                conflict = {
                    "base_version": base_version,
                    "current_version": session.version,
                    "received_at": now_iso(),
                }
                session.conflicts.append(conflict)
            resolved = resolve_conflict(session.content, incoming_content)
            if resolved != session.content or base_version == session.version:
                session.content = resolved
                session.version += 1
                session.updated_at = now_iso()
            return session, conflict

    async def add_conflict(self, session_id: str, conflict: dict[str, Any]) -> SessionRecord | None:
        async with self.state.lock:
            session = self.state.sessions.get(session_id)
            if not session:
                return None
            session.conflicts.append(conflict)
            return session

    async def add_participant(self, session_id: str, participant: ParticipantRecord) -> SessionRecord | None:
        async with self.state.lock:
            session = self.state.sessions.get(session_id)
            if not session:
                return None
            session.participants[participant.user_id] = participant
            return session

    async def remove_participant(self, session_id: str, user_id: str) -> SessionRecord | None:
        async with self.state.lock:
            session = self.state.sessions.get(session_id)
            if not session:
                return None
            session.participants.pop(user_id, None)
            return session

    async def update_cursor(self, session_id: str, user_id: str, cursor: dict[str, Any]) -> SessionRecord | None:
        async with self.state.lock:
            session = self.state.sessions.get(session_id)
            if not session:
                return None
            session.cursors[user_id] = cursor
            return session

    async def clear_cursor(self, session_id: str, user_id: str) -> SessionRecord | None:
        async with self.state.lock:
            session = self.state.sessions.get(session_id)
            if not session:
                return None
            session.cursors.pop(user_id, None)
            return session

    async def append(self, document_id: str, entry: HistoryRecord) -> None:
        async with self.state.lock:
            history = self.state.history.setdefault(document_id, [])
            history.append(entry)
            if len(history) > MAX_HISTORY:
                del history[:-MAX_HISTORY]

    async def list(self, document_id: str) -> list[HistoryRecord]:
        return list(self.state.history.get(document_id, []))

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        for q in self.state.subscribers.get(channel, set()):
            await q.put(payload)

    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self.state.subscribers.setdefault(channel, set()).add(queue)
        active = True

        async def runner() -> None:
            while active:
                payload = await queue.get()
                await handler(payload)

        task = asyncio.create_task(runner())

        async def unsubscribe() -> None:
            nonlocal active
            active = False
            self.state.subscribers.get(channel, set()).discard(queue)
            task.cancel()

        return unsubscribe

    async def healthy(self) -> bool:
        return True


class RedisBackend(SessionStore, PresenceStore, HistoryStore, PubSubBroker):
    def __init__(self, redis_url: str, namespace: str = "coedit") -> None:
        self.namespace = namespace
        if aioredis is None:
            raise RuntimeError("redis dependency is not installed")
        self.redis = aioredis.from_url(redis_url, decode_responses=True)

    def _session_key(self, session_id: str) -> str:
        return f"{self.namespace}:session:{session_id}"

    def _history_key(self, document_id: str) -> str:
        return f"{self.namespace}:history:{document_id}"

    def _channel(self, channel: str) -> str:
        return f"{self.namespace}:channel:{channel}"

    async def _load_session(self, session_id: str) -> SessionRecord | None:
        data = await self.redis.get(self._session_key(session_id))
        if not data:
            return None
        raw = json.loads(data)
        raw["participants"] = {
            k: ParticipantRecord(**v) for k, v in raw.get("participants", {}).items()
        }
        return SessionRecord(**raw)

    async def _save_session(self, session: SessionRecord) -> None:
        payload = asdict(session)
        await self.redis.set(self._session_key(session.session_id), json.dumps(payload))

    async def create(self, session: SessionRecord) -> SessionRecord:
        await self._save_session(session)
        return session

    async def get(self, session_id: str) -> SessionRecord | None:
        return await self._load_session(session_id)

    async def delete(self, session_id: str) -> SessionRecord | None:
        session = await self._load_session(session_id)
        if session:
            await self.redis.delete(self._session_key(session_id))
        return session

    async def update_content(
        self, session_id: str, incoming_content: str, base_version: int, updated_by: str
    ) -> tuple[SessionRecord | None, dict[str, Any] | None]:
        key = self._session_key(session_id)
        while True:
            try:
                async with self.redis.pipeline() as pipe:
                    await pipe.watch(key)
                    raw = await pipe.get(key)
                    if not raw:
                        await pipe.reset()
                        return None, None
                    payload = json.loads(raw)
                    session = SessionRecord(
                        **{
                            **payload,
                            "participants": {
                                k: ParticipantRecord(**v)
                                for k, v in payload.get("participants", {}).items()
                            },
                        }
                    )
                    conflict: dict[str, Any] | None = None
                    if base_version != session.version:
                        conflict = {
                            "base_version": base_version,
                            "current_version": session.version,
                            "received_at": now_iso(),
                            "updated_by": updated_by,
                        }
                        session.conflicts.append(conflict)
                    resolved = resolve_conflict(session.content, incoming_content)
                    if resolved != session.content or base_version == session.version:
                        session.content = resolved
                        session.version += 1
                        session.updated_at = now_iso()
                    pipe.multi()
                    pipe.set(key, json.dumps(asdict(session)))
                    await pipe.execute()
                    return session, conflict
            except WatchError:
                continue

    async def add_conflict(self, session_id: str, conflict: dict[str, Any]) -> SessionRecord | None:
        session = await self._load_session(session_id)
        if not session:
            return None
        session.conflicts.append(conflict)
        await self._save_session(session)
        return session

    async def add_participant(self, session_id: str, participant: ParticipantRecord) -> SessionRecord | None:
        session = await self._load_session(session_id)
        if not session:
            return None
        session.participants[participant.user_id] = participant
        await self._save_session(session)
        return session

    async def remove_participant(self, session_id: str, user_id: str) -> SessionRecord | None:
        session = await self._load_session(session_id)
        if not session:
            return None
        session.participants.pop(user_id, None)
        await self._save_session(session)
        return session

    async def update_cursor(self, session_id: str, user_id: str, cursor: dict[str, Any]) -> SessionRecord | None:
        session = await self._load_session(session_id)
        if not session:
            return None
        session.cursors[user_id] = cursor
        await self._save_session(session)
        return session

    async def clear_cursor(self, session_id: str, user_id: str) -> SessionRecord | None:
        session = await self._load_session(session_id)
        if not session:
            return None
        session.cursors.pop(user_id, None)
        await self._save_session(session)
        return session

    async def append(self, document_id: str, entry: HistoryRecord) -> None:
        key = self._history_key(document_id)
        await self.redis.rpush(key, json.dumps(asdict(entry)))
        await self.redis.ltrim(key, -MAX_HISTORY, -1)

    async def list(self, document_id: str) -> list[HistoryRecord]:
        items = await self.redis.lrange(self._history_key(document_id), 0, -1)
        return [HistoryRecord(**json.loads(item)) for item in items]

    async def publish(self, channel: str, payload: dict[str, Any]) -> None:
        await self.redis.publish(self._channel(channel), json.dumps(payload))

    async def subscribe(
        self, channel: str, handler: Callable[[dict[str, Any]], Awaitable[None]]
    ) -> Callable[[], Awaitable[None]]:
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._channel(channel))
        active = True

        async def runner() -> None:
            while active:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("data"):
                    await handler(json.loads(message["data"]))
                await asyncio.sleep(0.01)

        task = asyncio.create_task(runner())

        async def unsubscribe() -> None:
            nonlocal active
            active = False
            task.cancel()
            await pubsub.unsubscribe(self._channel(channel))
            await pubsub.close()

        return unsubscribe

    async def healthy(self) -> bool:
        try:
            pong = await self.redis.ping()
            return bool(pong)
        except Exception:
            return False


def build_backend() -> SessionStore | PresenceStore | HistoryStore | PubSubBroker:
    backend = os.getenv("COEDIT_STORAGE_BACKEND", "inmemory").lower()
    namespace = os.getenv("COEDIT_STORAGE_NAMESPACE", "default")
    if backend == "redis":
        redis_url = os.getenv("COEDIT_REDIS_URL", "redis://localhost:6379/0")
        return RedisBackend(redis_url=redis_url, namespace=namespace)
    return InMemoryBackend(namespace=namespace)
