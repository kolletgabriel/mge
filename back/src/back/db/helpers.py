from datetime import datetime, timezone
from typing import Any, Literal, Mapping, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Table, select, update
from sqlalchemy.exc import IntegrityError

from .schema import (
    auth_sessions,
    class_assistants,
    class_professors,
    class_user_ref_select,
    class_user_refs,
    classes,
    created_classes_from_rows,
    created_classes_select,
    created_professors_from_rows,
    created_professors_select,
    current_users,
    users,
    roles,
)

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
            users.insert().values(
                mail = mail,
                name = name,
                hashed_password = hashed_password,
                role_id = role_id
            ).returning(
                users.c.id
            )
        )).scalar_one()
    except IntegrityError:
        return


async def create_class(conn: AsyncConnection, title: str) -> Mapping | None:
    try:
        return (await conn.execute(
            classes.insert().values(
                title=title
            ).returning(
                classes.c.id,
                classes.c.title
            )
        )).mappings().one()
    except IntegrityError:
        return


async def associate_user_to_class(
    conn: AsyncConnection,
    table: Table,
    user_id: int,
    class_id: int,
) -> Mapping | None:
    try:
        return (await conn.execute(
            table.insert().values(
                id=user_id,
                class_id=class_id
            ).returning(
                table.c.id,
                table.c.class_id
            )
        )).mappings().one()
    except IntegrityError:
        return


async def associate_professor_to_class(
    conn: AsyncConnection,
    professor_id: int,
    class_id: int,
) -> Mapping | None:
    return await associate_user_to_class(
        conn, class_professors, professor_id, class_id
    )


async def associate_assistant_to_class(
    conn: AsyncConnection,
    student_id: int,
    class_id: int,
) -> Mapping | None:
    return await associate_user_to_class(
        conn, class_assistants, student_id, class_id
    )


async def get_user_ref(conn: AsyncConnection, user_id: int) -> Mapping:
    stmt = select(
        users.c.id,
        users.c.mail,
        users.c.name
    ).where(
        users.c.id == user_id
    )

    return (await conn.execute(stmt)).mappings().one()


async def get_class_users(
    conn: AsyncConnection,
    class_id: int,
    role_id: Literal[1, 2],
) -> list[Mapping]:
    result = await conn.execute(
        class_user_ref_select(class_id, role_id)
    )

    return list(result.mappings().all())


async def get_class_professors(
    conn: AsyncConnection,
    class_id: int,
) -> list[Mapping]:
    return await get_class_users(conn, class_id, 2)


async def get_class_assistants(
    conn: AsyncConnection,
    class_id: int,
) -> list[Mapping]:
    return await get_class_users(conn, class_id, 1)


async def get_professor_classes(
    conn: AsyncConnection,
    professor_id: int,
) -> list[Mapping]:
    refs = class_user_refs.c
    stmt = (
        select(
            refs.class_id.label('id'),
            refs.class_title.label('title'),
        ).where(
            (refs.user_id == professor_id)
            & (refs.role_id == 2)
        ).order_by(
            refs.class_title,
            refs.class_id
        )
    )

    return list((await conn.execute(stmt)).mappings().all())


async def list_classes(conn: AsyncConnection) -> list[Mapping]:
    stmt = classes.select().order_by(classes.c.title, classes.c.id)

    return list((await conn.execute(stmt)).mappings().all())


async def get_created_class(
    conn: AsyncConnection,
    class_id: int
) -> dict[str, Any]:
    rows = (await conn.execute(
        created_classes_select(class_id)
    )).mappings().all()

    return created_classes_from_rows(rows)[0]


async def list_created_classes(conn: AsyncConnection) -> list[dict[str, Any]]:
    rows = (await conn.execute(
        created_classes_select()
    )).mappings().all()

    return created_classes_from_rows(rows)


async def list_professors(conn: AsyncConnection) -> list[Mapping]:
    stmt = (
        select(
            users.c.id,
            users.c.mail,
            users.c.name,
            users.c.role_id,
            roles.c.title.label('role_title'),
        ).select_from(
            users.join(
                roles, (roles.c.id == users.c.role_id)
            )
        ).where(
            users.c.role_id == 2
        ).order_by(
            users.c.name,
            users.c.id
        )
    )

    return list((await conn.execute(stmt)).mappings().all())


async def get_created_professor_payload(
    conn: AsyncConnection,
    professor_id: int,
) -> dict[str, Any]:
    rows = (await conn.execute(
        created_professors_select(professor_id)
    )).mappings().all()

    return created_professors_from_rows(rows)[0]


async def list_created_professors(
    conn: AsyncConnection
) -> list[dict[str, Any]]:
    rows = (await conn.execute(
        created_professors_select()
    )).mappings().all()

    return created_professors_from_rows(rows)


async def list_students(conn: AsyncConnection) -> list[Mapping]:
    stmt = (
        select(
            users.c.id,
            users.c.mail,
            users.c.name
        ).where(
            users.c.role_id == 1
        ).order_by(
            users.c.name,
            users.c.id
        )
    )

    return list((await conn.execute(stmt)).mappings().all())


async def get_current_user(
    conn: AsyncConnection,
    user_id: int
) -> Mapping:
    stmt = current_users.select().where(current_users.c.id == user_id)

    return (await conn.execute(stmt)).mappings().one()


async def get_login_user(
    conn: AsyncConnection,
    mail: str,
) -> Mapping | None:
    stmt = (
        select(
            users.c.id,
            users.c.hashed_password,
            users.c.role_id
        ).where(users.c.mail == mail)
    )

    return (await conn.execute(stmt)).mappings().first()


async def create_auth_session(
    conn: AsyncConnection,
    sess: dict[str, Any],
    user_id: int,
    user_role: int
) -> None:
    sess.clear()  # garante sessão nova

    session_id = uuid4()
    await conn.execute(
        auth_sessions.insert().values(id=session_id, user_id=user_id)
    )

    sess.update(uid=user_id, rid=user_role, sid=str(session_id))


async def revoke_auth_session(
    conn: AsyncConnection,
    session_id: str,
    user_id: int,
) -> None:
    session_uuid = UUID(str(session_id))
    revoked_at = datetime.now(timezone.utc)

    stmt = (
        update(auth_sessions).where(
            (auth_sessions.c.id == session_uuid)
             & (auth_sessions.c.user_id == user_id)
        ).values(revoked_at=revoked_at)
    )

    await conn.execute(stmt)


async def auth_session_is_active(
    conn: AsyncConnection,
    session_id: UUID | str,
    user_id: int,
) -> bool:
    session_uuid = UUID(str(session_id))

    stmt = (
        select(auth_sessions.c.id).where(
            (auth_sessions.c.id == session_uuid)
            & (auth_sessions.c.user_id == user_id)
            & (auth_sessions.c.revoked_at.is_(None))
        )
    )

    result = (await conn.execute(stmt)).scalar()

    return result is not None
