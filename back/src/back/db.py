from datetime import datetime, timezone
from typing import Any, Literal, Mapping, TYPE_CHECKING
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
    role_id: Literal[0, 1, 2]
) -> int | None:
    try:
        return (await conn.execute(
            text(
                '''
                INSERT INTO users(mail, name, hashed_password, role_id)
                VALUES (:mail, :name, :hashed_password, :role_id)
                RETURNING id;
                '''
            ).bindparams(
                mail = mail,
                name = name,
                hashed_password = hashed_password,
                role_id = role_id
            )
        )).scalar_one()
    except IntegrityError:
        return


async def create_class(conn: AsyncConnection, title: str) -> Mapping | None:
    try:
        return (await conn.execute(
            text(
                '''
                INSERT INTO classes(title)
                VALUES (:title)
                RETURNING id, title;
                '''
            ).bindparams(title=title)
        )).mappings().one()
    except IntegrityError:
        return


async def associate_professor_to_class(
    conn: AsyncConnection,
    professor_id: int,
    class_id: int,
) -> Mapping | None:
    try:
        return (await conn.execute(
            text(
                '''
                INSERT INTO class_professors(id, class_id)
                VALUES (:professor_id, :class_id)
                RETURNING id, class_id;
                '''
            ).bindparams(professor_id=professor_id, class_id=class_id)
        )).mappings().one()
    except IntegrityError:
        return


async def associate_assistant_to_class(
    conn: AsyncConnection,
    student_id: int,
    class_id: int,
) -> Mapping | None:
    try:
        return (await conn.execute(
            text(
                '''
                INSERT INTO class_assistants(id, class_id)
                VALUES (:student_id, :class_id)
                RETURNING id, class_id;
                '''
            ).bindparams(student_id=student_id, class_id=class_id)
        )).mappings().one()
    except IntegrityError:
        return


async def get_user_ref(conn: AsyncConnection, user_id: int) -> Mapping:
    return (await conn.execute(
        text(
            '''
            SELECT id, mail, name
            FROM users
            WHERE id = :user_id;
            '''
        ).bindparams(user_id=user_id)
    )).mappings().one()


async def get_class_professors(
    conn: AsyncConnection,
    class_id: int,
) -> list[Mapping]:
    return list((await conn.execute(
        text(
            '''
            SELECT u.id, u.mail, u.name
            FROM class_professors AS cp
                JOIN users AS u ON u.id = cp.id
            WHERE cp.class_id = :class_id
            ORDER BY u.name, u.id;
            '''
        ).bindparams(class_id=class_id)
    )).mappings().all())


async def get_professor_classes(
    conn: AsyncConnection,
    professor_id: int,
) -> list[Mapping]:
    return list((await conn.execute(
        text(
            '''
            SELECT c.id, c.title
            FROM class_professors AS cp
                JOIN classes AS c ON c.id = cp.class_id
            WHERE cp.id = :professor_id
            ORDER BY c.title, c.id;
            '''
        ).bindparams(professor_id=professor_id)
    )).mappings().all())


async def get_created_professor(
    conn: AsyncConnection,
    professor_id: int,
) -> Mapping:
    return (await conn.execute(
        text(
            '''
            SELECT u.id, u.mail, u.name, u.role_id, r.title AS role_title
            FROM users AS u
                JOIN roles AS r ON r.id = u.role_id
            WHERE u.id = :professor_id;
            '''
        ).bindparams(professor_id=professor_id)
    )).mappings().one()


async def list_classes(conn: AsyncConnection) -> list[Mapping]:
    return list((await conn.execute(
        text(
            '''
            SELECT id, title
            FROM classes
            ORDER BY title, id;
            '''
        )
    )).mappings().all())


async def list_professors(conn: AsyncConnection) -> list[Mapping]:
    return list((await conn.execute(
        text(
            '''
            SELECT u.id, u.mail, u.name, u.role_id, r.title AS role_title
            FROM users AS u
                JOIN roles AS r ON r.id = u.role_id
            WHERE u.role_id = 2
            ORDER BY u.name, u.id;
            '''
        )
    )).mappings().all())


async def get_current_user(
    conn: AsyncConnection,
    user_id: int
) -> Mapping:
    return (await conn.execute(
        text(
            '''
            SELECT *
            FROM current_users
            WHERE id = :uid;
            '''
        ).bindparams(uid=user_id)
    )).mappings().one()


async def get_login_user(
    conn: AsyncConnection,
    mail: str,
) -> Mapping | None:
    return (await conn.execute(
        text(
            '''
            SELECT id, hashed_password, role_id
            FROM users
            WHERE mail = :mail;
            '''
        ).bindparams(mail=mail)
    )).mappings().first()


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
