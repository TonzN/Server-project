"""Authentication context for legacy-compatible server actions."""
from dataclasses import dataclass
from functools import wraps
from typing import Any
import inspect

from server_utils import get_user_profile
from database_manager import db_get_user_profile

@dataclass(frozen=True)
class UserContext:
    token: str
    session: dict
    account: dict | None = None

    @property
    def username(self) -> str:
        return self.session["name"]

    @property
    def id(self) -> str:
        return self.session["id"]

def authenticated(*, database: bool = False, denied: Any = "invalid token"):
    """Validate token and inject 'user' without altering (data, token) dispatch.

    database=True also loads the persisted account once; requires async def.
    """
    def decorate(handler):
        if database and not inspect.iscoroutinefunction(handler):
            raise TypeError("database=True requires an async handler")

        if inspect.iscoroutinefunction(handler):
            @wraps(handler)
            async def async_handler(data, token, *args, **kwargs):
                session = get_user_profile(token)
                if not session:
                    return denied
                account = None
                if database:
                    account = await db_get_user_profile(session["name"])
                    if not account:
                        return denied
                return await handler(data, token, *args, user=UserContext(token, session, account), **kwargs)
            return async_handler

        @wraps(handler)
        def sync_handler(data, token, *args, **kwargs):
            session = get_user_profile(token)
            if not session:
                return denied
            return handler(data, token, *args, user=UserContext(token, session), **kwargs)
        return sync_handler
    return decorate
