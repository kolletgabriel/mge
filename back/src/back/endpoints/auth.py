from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, Request, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text

from back.dependencies import ConnDep, HashToolDep
from back.models import Credentials


router = APIRouter()


@router.post('/login', status_code=204)
async def login(
    req: Request,
    conn: ConnDep,
    hash_tool: HashToolDep,
    creds: Credentials,
) -> None:
    req.session.clear()  # garante sessão nova

    result = (await conn.execute(
        text(
            '''
            SELECT id, name, hashed_password, role_id
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

        user_id, user_name, user_hpw, user_role = result
        await run_in_threadpool(hasher.verify, user_hpw, creds.password)

    except VerifyMismatchError:
        raise HTTPException(status_code=401)

    req.session.update(id=user_id, name=user_name, role=user_role)
