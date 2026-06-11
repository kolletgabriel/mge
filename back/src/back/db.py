from datetime import datetime, timezone
from typing import NamedTuple
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection


async def get_login_user(
        conn: AsyncConnection,
        mail: str
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
