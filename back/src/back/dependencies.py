from typing import Any, Annotated, AsyncIterator

from argon2 import PasswordHasher
from fastapi import Depends, Request, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncConnection

from back import db
from back.models import CurrentUser, SessionData


async def _get_db(req: Request) -> AsyncIterator[AsyncConnection]:
    async with req.state['db'].begin() as conn:
        yield conn

ConnDep = Annotated[AsyncConnection, Depends(_get_db)]


async def _get_ph(req: Request) -> tuple[PasswordHasher, str]:
    return (req.state['ph'], req.state['dummy_hash'])

HashToolDep = Annotated[tuple[PasswordHasher, str], Depends(_get_ph)]


async def _session_data(req: Request) -> dict[str, Any]:
    return req.session

RawSessionDep = Annotated[dict[str, Any], Depends(_session_data)]


async def _require_session(sess: RawSessionDep, conn: ConnDep) -> SessionData:
    try:
        sess_data = SessionData(**sess)
    except ValidationError:
        raise HTTPException(status_code=401)

    if not await db.auth_session_is_active(conn, sess_data.sid, sess_data.uid):
        raise HTTPException(status_code=401)

    return sess_data

CurrentSessionDep = Annotated[SessionData, Depends(_require_session)]
SessionRequiredDep = Depends(_require_session)


async def _current_user(sess: CurrentSessionDep, conn: ConnDep) -> CurrentUser:
    return await db.get_current_user(conn, sess.uid)

CurrentUserDep = Annotated[CurrentUser, Depends(_current_user)]
