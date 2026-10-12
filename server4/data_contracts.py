"""Internal Server 4 data contracts.

These definitions are *documentation and compatibility helpers*, not a change to
the WebSocket wire format. All emitted payloads preserve Server 3 shapes.
"""
from __future__ import annotations

import json
from typing import Any, TypedDict


class DatabaseUser(TypedDict):
    username: str
    password: str  # Argon2 hash; never a plaintext password.
    id: str
    permission_level: str
    security_mode: str


class SessionProfile(TypedDict):
    name: str
    id: str
    connection_error_count: int
    heartbeat: float
    socket: Any
    subscribed_room: str | None
    rooms_joined: list[list[str]]


class DirectRoom(TypedDict):
    users: list[str]
    active_users: set[str]


class RequestPacket(TypedDict):
    v: int
    action: str
    data: Any
    tag: str
    token: str | None


class ResponseEnvelope(TypedDict):
    data: list[Any]


def build_session_profile(database_user: DatabaseUser, socket: Any, now: float) -> SessionProfile:
    """Build the same in-memory session profile as Server 3.

    A live socket is internal state and must not be serialized to the client.
    """
    return {
        "name": database_user["username"],
        "id": database_user["id"],
        "connection_error_count": 0,
        "heartbeat": now,
        "socket": socket,
        "subscribed_room": None,
        "rooms_joined": [],
    }


def build_response(data: Any, tag: str) -> str:
    """Preserve the legacy JSON envelope and terminating newline exactly."""
    return json.dumps({"data": [data, tag]}) + "\n"
