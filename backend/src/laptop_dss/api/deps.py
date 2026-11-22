"""HTTP dependencies: session cookie, current user, maintainer guard."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from laptop_dss.config import load_settings
from laptop_dss.profiles.adapters import auth
from laptop_dss.shared.domain.errors import Forbidden, Unauthorized

settings = load_settings()


def session_token(request: Request) -> str | None:
    return request.cookies.get(settings.session_cookie_name)


def current_user(request: Request) -> dict[str, Any] | None:
    return auth.current_user(session_token(request))


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if user is None:
        raise Unauthorized("Требуется вход")
    return user


def require_maintainer(request: Request) -> dict[str, Any]:
    user = require_user(request)
    if user["role"] != "maintainer":
        raise Forbidden("Требуются права администратора каталога")
    return user
