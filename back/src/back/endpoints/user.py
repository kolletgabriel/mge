from fastapi import APIRouter

from back import db
from back.dependencies import CurrentSessionDep, ConnDep
from back.models import CurrentUser, CurrentUserAdpt


router = APIRouter()


@router.get('/me')
async def user_data(conn: ConnDep, sess: CurrentSessionDep) -> CurrentUser:
    return CurrentUserAdpt.validate_python(
        await db.get_current_user(conn, sess.uid)
    )
