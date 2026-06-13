from datetime import datetime, timezone
from typing import Any, Literal, TYPE_CHECKING
from uuid import uuid4, UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncConnection


async def create_user(
    conn: AsyncConnection,
    mail: str,
    name: str,
    hashed_password: str,
    role_id: Literal[0, 1, 2] = 1
) -> tuple[int, int] | None:
    try:
        result = (await conn.execute(
            text(
                '''
                INSERT INTO users(mail, name, hashed_password, role_id)
                VALUES (:mail, :name, :hashed_password, :role_id)
                RETURNING id, role_id;
                '''
            ).bindparams(
                mail = mail,
                name = name,
                hashed_password = hashed_password,
                role_id = role_id
            )
        )).one()
    except IntegrityError:
        return

    return (*result,)


async def get_current_user(
    conn: AsyncConnection,
    user_id: int
) -> dict[str, Any] | None:
    row = (await conn.execute(
        text(
            '''
            SELECT id, mail, name, role_id, role, scope
            FROM current_users
            WHERE id = :uid;
            '''
        ).bindparams(uid=user_id)
    )).mappings().first()

    if row is None:
        return

    result = dict(row)
    result['rid'] = result.pop('role_id')

    return result


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
        return

    return (*result,)


async def create_auth_session(
    conn: AsyncConnection,
    sess: dict[str, Any],
    user_id: int,
    user_role: int
) -> None:
    sess.clear()  # garante sessão nova

    session_id = uuid4()
    await conn.execute(
        text(
            '''
            INSERT INTO auth_sessions(id, user_id)
            VALUES (:sid, :uid);
            '''
        ).bindparams(sid=session_id, uid=user_id)
    )

    sess.update(uid=user_id, rid=user_role, sid=str(session_id))


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
