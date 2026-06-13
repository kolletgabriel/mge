from fastapi import APIRouter, HTTPException

from back import db, hash_tools
from back.dependencies import ConnDep, RawSessionDep
from back.models import Credentials, CurrentUser, CurrentUserAdpt, Registration


router = APIRouter()


@router.post('/register', status_code=201)
async def register(
    sess: RawSessionDep,
    conn: ConnDep,
    provided: Registration,
) -> CurrentUser:
    hashed_pw = await hash_tools.hash_pw(provided.password)
    user_data = await db.create_user(
        conn,
        provided.mail,
        provided.name,
        hashed_pw
    )
    if user_data is None:
        raise HTTPException(status_code=409)

    uid, rid = user_data
    await db.create_auth_session(conn, sess, uid, rid)

    return CurrentUserAdpt.validate_python(
        await db.get_current_user(conn, uid)
    )


@router.post('/login')
async def login(
    sess: RawSessionDep,
    conn: ConnDep,
    provided: Credentials,
) -> CurrentUser:
    user_data = await db.get_login_user(conn, provided.mail)
    if user_data is None:
        await hash_tools.verify_dummy()
        raise HTTPException(status_code=401)

    uid, hpw, rid = user_data
    if not await hash_tools.matches(hpw, provided.password):
        raise HTTPException(status_code=401)

    await db.create_auth_session(conn, sess, uid, rid)

    return CurrentUserAdpt.validate_python(
        await db.get_current_user(conn, uid)
    )

@router.post('/logout', status_code=204)
async def logout(sess: RawSessionDep, conn: ConnDep) -> None:
    if not (sess.get('sid') and sess.get('uid')):
        return

    await db.revoke_auth_session(conn, sess['sid'], sess['uid'])

    sess.clear()
