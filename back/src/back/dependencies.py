from typing import Any, Annotated, AsyncIterator

from fastapi import Depends, Request, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncConnection

from back import db
from back.models import SessionData


async def _get_db(req: Request) -> AsyncIterator[AsyncConnection]:
    async with req.state['db'].begin() as conn:
        yield conn

ConnDep = Annotated[AsyncConnection, Depends(_get_db)]


async def _raw_session(req: Request) -> dict[str, Any]:
    return req.session

RawSessionDep = Annotated[dict[str, Any], Depends(_raw_session)]


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
