from typing import Mapping

from fastapi import APIRouter, HTTPException

from back import db
from back.dependencies import ConnDep, CurrentSessionDep, SchedPermsDep
from back.models import SchedulableClass, ReviewSession, ReviewSessionRequest


router = APIRouter(prefix='/review-sessions')


@router.get('/scheduling-options', response_model=list[SchedulableClass])
async def scheduling_options(
    conn: ConnDep,
    sess: CurrentSessionDep,
) -> list[Mapping]:
    return await db.list_schedulable_classes(conn, sess.uid, sess.rid)


@router.post(
    '',
    status_code=201,
    response_model=ReviewSession,
    dependencies=[SchedPermsDep],
)
async def create_review_session(
    conn: ConnDep,
    sess: CurrentSessionDep,
    provided: ReviewSessionRequest,
) -> Mapping:
    assistant_ids = provided.assistant_ids
    if sess.rid != 1:
        class_assistant_ids = await db.list_class_assistant_ids(
            conn,
            provided.class_id,
        )
        if any(
            assistant_id not in class_assistant_ids
            for assistant_id in assistant_ids
        ):
            raise HTTPException(status_code=400)

    session = await db.create_review_session(
        conn,
        provided.class_id,
        provided.starts_at,
        provided.ends_at,
        provided.location,
        provided.max_participants,
    )
    if session is None:
        raise HTTPException(status_code=400)

    for assistant_id in assistant_ids:
        relation = await db.associate_assistant_to_session(
            conn,
            session['id'],
            provided.class_id,
            assistant_id,
        )
        if relation is None:
            raise HTTPException(status_code=400)

    return await db.get_review_session_payload(conn, session['id'])
