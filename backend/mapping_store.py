from __future__ import annotations

import threading
import time
import uuid


SESSION_TTL_SECONDS = 30 * 60

SESSION_STORE: dict[str, dict[str, str]] = {}
_SESSION_EXPIRY: dict[str, float] = {}
_STORE_LOCK = threading.RLock()


def _utc_timestamp() -> float:
    return time.time()


def _is_session_active_locked(session_id: str, now: float | None = None) -> bool:
    expires_at = _SESSION_EXPIRY.get(session_id)
    if expires_at is None:
        return False
    return expires_at > (now if now is not None else _utc_timestamp())


def create_session(ttl_seconds: int | float = SESSION_TTL_SECONDS) -> str:
    """Create a new random UUID session for server-side pseudonym mappings."""
    cleanup_expired_sessions()
    expires_at = _utc_timestamp() + float(ttl_seconds)

    with _STORE_LOCK:
        session_id = str(uuid.uuid4())
        while session_id in SESSION_STORE:
            session_id = str(uuid.uuid4())

        SESSION_STORE[session_id] = {}
        _SESSION_EXPIRY[session_id] = expires_at
        return session_id


def store_mapping(session_id: str, placeholder: str, original_value: str) -> None:
    """Store a placeholder-to-original mapping for an active session."""
    cleanup_expired_sessions()

    normalized_placeholder = placeholder.strip().strip("[]")
    if not normalized_placeholder:
        raise ValueError("placeholder cannot be empty")

    with _STORE_LOCK:
        if not _is_session_active_locked(session_id):
            raise KeyError(f"Session not found or expired: {session_id}")

        SESSION_STORE[session_id][normalized_placeholder] = original_value


def get_mapping(session_id: str) -> dict[str, str] | None:
    """Return a defensive copy of the active session mapping, or None."""
    cleanup_expired_sessions()

    with _STORE_LOCK:
        if not _is_session_active_locked(session_id):
            SESSION_STORE.pop(session_id, None)
            _SESSION_EXPIRY.pop(session_id, None)
            return None
        return dict(SESSION_STORE[session_id])


def delete_session(session_id: str) -> bool:
    """Delete a session and its mappings."""
    with _STORE_LOCK:
        existed = session_id in SESSION_STORE
        SESSION_STORE.pop(session_id, None)
        _SESSION_EXPIRY.pop(session_id, None)
        return existed


def cleanup_expired_sessions(now: float | None = None) -> int:
    """Delete expired sessions and return the number removed."""
    current_time = _utc_timestamp() if now is None else now

    with _STORE_LOCK:
        expired_session_ids = [
            session_id
            for session_id, expires_at in _SESSION_EXPIRY.items()
            if expires_at <= current_time
        ]
        for session_id in expired_session_ids:
            SESSION_STORE.pop(session_id, None)
            _SESSION_EXPIRY.pop(session_id, None)
        return len(expired_session_ids)
