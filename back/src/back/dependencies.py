from typing import Any, Annotated, AsyncIterator, Literal

from fastapi import Depends, Request, HTTPException
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncConnection

from back import db
from back.models import SessionData, ReviewSessionRequest


async def _get_db(req: Request) -> AsyncIterator[AsyncConnection]:
    async with req.state['db'].begin() as conn:
        yield conn

ConnDep = Annotated[AsyncConnection, Depends(_get_db, scope='function')]


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


async def _require_sched_perms(
    conn: ConnDep,
    sess: CurrentSessionDep,
    provided: ReviewSessionRequest,
) -> None:
    access = await db.get_sched_perms(
        conn,
        sess.uid,
        sess.rid,
        provided.class_id,
    )

    if access == 'missing':
        raise HTTPException(status_code=404)
    if access == 'forbidden':
        raise HTTPException(status_code=403)
    if sess.rid == 1 and any(
        assistant_id != sess.uid
        for assistant_id in provided.assistant_ids
    ):
        raise HTTPException(status_code=403)

SchedPermsDep = Depends(_require_sched_perms)


class RolePermission:
    def __init__(self, for_rid: Literal[0, 1, 2], flag: bool) -> None:
        self.for_rid = for_rid
        self.flag = flag

    async def __call__(self, sess: CurrentSessionDep) -> None:
        if self.flag:
            if self.for_rid != sess.rid:
                raise HTTPException(status_code=403)
            return
        if self.for_rid == sess.rid:
            raise HTTPException(status_code=403)

AdminRequiredDep = Depends(RolePermission(0, True))
StudentRequiredDep = Depends(RolePermission(1, True))
ProfessorRequiredDep = Depends(RolePermission(2, True))
StudentForbiddenDep = Depends(RolePermission(1, False))
ProfessorForbiddenDep = Depends(RolePermission(2, False))
