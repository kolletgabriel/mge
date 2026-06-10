from uuid import uuid4

from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from back.dependencies import ConnDep, HashToolDep, RawSessionDep
from back.models import Credentials, SessionData


router = APIRouter()


@router.post('/login', status_code=204)
async def login(
    sess: RawSessionDep,
    conn: ConnDep,
    hash_tool: HashToolDep,
    creds: Credentials,
) -> None:
    sess.clear()  # garante sessão nova

    result = (await conn.execute(
        text(
            '''
            SELECT id, hashed_password, role_id
            FROM users
            WHERE mail = :mail;
            '''
        ).bindparams(mail=creds.mail)
    )).first()

    hasher, dummy_hash = hash_tool
    try:
        if result is None:
            # Mantem tempo constante. Sempre lança a exception:
            await run_in_threadpool(hasher.verify, dummy_hash, creds.password)
            raise VerifyMismatchError  # garante

        user_id, user_hpw, user_role = result
        await run_in_threadpool(hasher.verify, user_hpw, creds.password)

    except VerifyMismatchError:
        raise HTTPException(status_code=401)

    session_id = uuid4()
    await conn.execute(
        text(
            '''
            INSERT INTO auth_sessions(id, user_id)
            VALUES (:sid, :uid);
            '''
        ).bindparams(sid=session_id, uid=user_id)
    )

    sess.update(
        uid = user_id,
        rid = user_role,
        sid = str(session_id)
    )
