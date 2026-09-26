from __future__ import annotations

import uuid

from fastapi import Request, Response

SESSION_COOKIE = "jobify_sid"
SESSION_MAX_AGE = 60 * 60 * 24 * 30  # 30 days


def get_session_id(request: Request) -> str | None:
    return request.cookies.get(SESSION_COOKIE)


def ensure_session_id(request: Request, response: Response) -> str:
    """Return existing session id or create one and set the cookie."""
    sid = get_session_id(request)
    if sid:
        return sid
    sid = uuid.uuid4().hex
    response.set_cookie(
        key=SESSION_COOKIE,
        value=sid,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE,
        path="/",
    )
    return sid
