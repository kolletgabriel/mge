from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from pydantic import TypeAdapter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from back.models import CurrentUser


CurrentUserAdapter = TypeAdapter(CurrentUser)


async def get_login_user(
    conn: AsyncConnection,
    mail: str,
) -> tuple[int, str, int] | None:
    result = (await conn.execute(
        text(
            '''
            SELECT id, hashed_password, role_id
            FROM users
            WHERE mail = :mail;
            '''
        ).bindparams(mail=mail)
    )).first()

    if result is None:
        return None

    return (*result,)


async def create_auth_session(
    conn: AsyncConnection,
    session_id: UUID,
    user_id: int,
) -> None:
    await conn.execute(
        text(
            '''
            INSERT INTO auth_sessions(id, user_id)
            VALUES (:sid, :uid);
            '''
        ).bindparams(sid=session_id, uid=user_id)
    )


async def create_user(
    conn: AsyncConnection,
    mail: str,
    name: str,
    hashed_password: str,
) -> tuple[int, int]:
    result = (await conn.execute(
        text(
            '''
            INSERT INTO users(mail, name, hashed_password)
            VALUES (:mail, :name, :hashed_password)
            RETURNING id, role_id;
            '''
        ).bindparams(mail=mail, name=name, hashed_password=hashed_password)
    )).one()

    return (*result,)


async def revoke_auth_session(
    conn: AsyncConnection,
    session_id: str,
    user_id: int,
) -> None:
    revoked_at = datetime.now(timezone.utc)
    await conn.execute(
        text(
            '''
            UPDATE auth_sessions
            SET revoked_at = :ts
            WHERE id = CAST(:sid AS UUID)
                AND user_id = :uid;
            '''
        ).bindparams(ts=revoked_at, sid=session_id, uid=user_id)
    )


async def auth_session_is_active(
    conn: AsyncConnection,
    session_id: UUID,
    user_id: int,
) -> bool:
    result = (await conn.execute(
        text(
            '''
            SELECT 1
            FROM auth_sessions
            WHERE id = CAST(:sid AS UUID)
                AND user_id = :uid
                AND revoked_at IS NULL;
            '''
        ).bindparams(sid=session_id, uid=user_id)
    )).scalar()

    return result is not None


async def get_current_user(conn: AsyncConnection, user_id: int) -> CurrentUser:
    row = (await conn.execute(
        text(
            '''
            SELECT id, mail, name, role_id, role, scope
            FROM current_users
            WHERE id = :uid;
            '''
        ).bindparams(uid=user_id)
    )).mappings().one_or_none()

    if row is None:
        raise HTTPException(status_code=401)

    data = dict(row)
    data['rid'] = data.pop('role_id')

    return CurrentUserAdapter.validate_python(data)
