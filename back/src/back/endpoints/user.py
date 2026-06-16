from typing import Mapping

from fastapi import APIRouter

from back import db
from back.dependencies import ConnDep, CurrentSessionDep
from back.models import CurrentUser


router = APIRouter()


@router.get('/me', response_model=CurrentUser)
async def user_data(conn: ConnDep, sess: CurrentSessionDep) -> Mapping:
    return await db.get_current_user(conn, sess.uid)
