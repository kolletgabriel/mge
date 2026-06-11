from uuid import uuid4

from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from back import db
from back.dependencies import ConnDep, HashToolDep, RawSessionDep
from back.models import Credentials, CurrentUser


router = APIRouter()


@router.post('/login')
async def login(
    sess: RawSessionDep,
    conn: ConnDep,
    hash_tool: HashToolDep,
    creds: Credentials,
) -> CurrentUser:
    sess.clear()  # garante sessão nova

    result = await db.get_login_user(conn, creds.mail)

    hasher, dummy_hash = hash_tool
    try:
        if result is None:
            # Mantem tempo constante. Sempre lança a exception:
            await run_in_threadpool(
                hasher.verify,
                dummy_hash,
                creds.password.get_secret_value()
            )
            raise VerifyMismatchError  # garante

        user_id, user_hpw, user_role = result
        await run_in_threadpool(
            hasher.verify,
            user_hpw,
            creds.password.get_secret_value()
        )

    except VerifyMismatchError:
        raise HTTPException(status_code=401)

    session_id = uuid4()
    await db.create_auth_session(conn, session_id, user_id)

    sess.update(
        uid = user_id,
        rid = user_role,
        sid = str(session_id)
    )

    return await db.get_current_user(conn, user_id)


@router.post('/logout', status_code=204)
async def logout(sess: RawSessionDep, conn: ConnDep) -> None:
    if not (sess.get('sid') and sess.get('uid')):
        return

    await db.revoke_auth_session(conn, sess['sid'], sess['uid'])

    sess.clear()
