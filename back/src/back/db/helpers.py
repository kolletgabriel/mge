from datetime import datetime, timezone
from typing import Any, Literal, Mapping, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Table, literal, select, update
from sqlalchemy.exc import IntegrityError

from .schema import (
    admin_class_schedule_access_select,
    associate_classes_to_user_insert,
    associate_users_to_class_insert,
    assistant_class_schedule_access_select,
    auth_sessions,
    class_assistants,
    class_professors,
    class_user_refs,
    classes,
    created_classes_from_rows,
    created_classes_select,
    created_professors_from_rows,
    created_professors_select,
    current_users,
    professor_class_schedule_access_select,
    review_session_payload_from_rows,
    review_session_payload_select,
    review_sessions,
    session_assistants,
    users,
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


def class_association_target(
    which: Literal['assistant', 'professor']
) -> tuple[Table, Literal[1, 2]]:
    if which == 'assistant':
        return class_assistants, 1
    return class_professors, 2


async def associate_users_to_class(
    conn: AsyncConnection,
    which: Literal['assistant', 'professor'],
    user_ids: list[int],
    class_id: int,
) -> bool:
    if not user_ids:
        return True

    table, role_id = class_association_target(which)
    stmt = associate_users_to_class_insert(
        table,
        role_id,
        user_ids,
        class_id,
    )

    try:
        inserted = (await conn.execute(stmt)).scalars().all()
    except IntegrityError:
        return False

    return len(inserted) == len(user_ids)


async def associate_classes_to_user(
    conn: AsyncConnection,
    which: Literal['assistant', 'professor'],
    user_id: int,
    class_ids: list[int],
) -> bool:
    if not class_ids:
        return True

    table, role_id = class_association_target(which)
    stmt = associate_classes_to_user_insert(
        table,
        role_id,
        user_id,
        class_ids,
    )

    try:
        inserted = (await conn.execute(stmt)).scalars().all()
    except IntegrityError:
        return False

    return len(inserted) == len(class_ids)


async def get_user_ref(conn: AsyncConnection, user_id: int) -> Mapping:
    stmt = select(
        users.c.id,
        users.c.mail,
        users.c.name
    ).where(
        users.c.id == user_id
    )

    return (await conn.execute(stmt)).mappings().one()


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


async def list_schedulable_classes(
    conn: AsyncConnection,
    user_id: int,
    role_id: Literal[0, 1, 2],
) -> list[dict[str, Any]]:
    assistants = class_user_refs.alias('assistants')
    source = classes.outerjoin(
        assistants,
        (assistants.c.class_id == classes.c.id)
        & (assistants.c.role_id == 1)
    )
    if role_id == 1:
        source = source.join(
            class_assistants,
            (class_assistants.c.class_id == classes.c.id)
            & (class_assistants.c.id == user_id)
        )
    elif role_id == 2:
        source = source.join(
            class_professors,
            (class_professors.c.class_id == classes.c.id)
            & (class_professors.c.id == user_id)
        )

    stmt = (
        select(
            classes.c.id,
            classes.c.title,
            assistants.c.user_id.label('assistant_id'),
            assistants.c.mail.label('assistant_mail'),
            assistants.c.name.label('assistant_name'),
        ).select_from(source).order_by(
            classes.c.title,
            classes.c.id,
            assistants.c.name,
            assistants.c.user_id,
        )
    )

    if role_id == 1:
        stmt = stmt.where(assistants.c.user_id == user_id)

    rows = (await conn.execute(stmt)).mappings().all()
    by_class: dict[int, dict[str, Any]] = {}
    for row in rows:
        class_ = by_class.setdefault(
            row['id'],
            {'id': row['id'], 'title': row['title'], 'assistants': []},
        )
        if row['assistant_id'] is not None:
            class_['assistants'].append({
                'id': row['assistant_id'],
                'mail': row['assistant_mail'],
                'name': row['assistant_name'],
            })

    return list(by_class.values())


async def get_sched_perms(
    conn: AsyncConnection,
    user_id: int,
    role_id: Literal[0, 1, 2],
    class_id: int,
) -> Literal['missing', 'forbidden', 'allowed']:
    if role_id == 0:
        stmt = admin_class_schedule_access_select(class_id)
    elif role_id == 1:
        stmt = assistant_class_schedule_access_select(user_id, class_id)
    else:
        stmt = professor_class_schedule_access_select(user_id, class_id)

    row = (await conn.execute(stmt)).first()

    if row is None:
        return 'missing'
    if role_id == 0 or row[0] is not None:
        return 'allowed'
    return 'forbidden'


async def create_review_session(
    conn: AsyncConnection,
    class_id: int,
    starts_at: datetime | None,
    ends_at: datetime | None,
    location: str,
    max_participants: int,
) -> Mapping | None:
    try:
        return (await conn.execute(
            review_sessions.insert().values(
                class_id=class_id,
                starts_at=starts_at,
                ends_at=ends_at,
                location=location,
                max_participants=max_participants,
            ).returning(review_sessions.c.id)
        )).mappings().one()
    except IntegrityError:
        return


async def associate_class_assistants_to_session(
    conn: AsyncConnection,
    session_id: int,
    class_id: int,
    assistant_ids: list[int],
) -> bool:
    if not assistant_ids:
        return True

    stmt = (
        session_assistants.insert().from_select(
            ['id', 'class_id', 'session_id'],
            select(
                class_assistants.c.id,
                class_assistants.c.class_id,
                literal(session_id),
            ).where(
                class_assistants.c.class_id == class_id,
                class_assistants.c.id.in_(assistant_ids),
            )
        ).returning(session_assistants.c.id)
    )

    try:
        inserted = (await conn.execute(stmt)).scalars().all()
    except IntegrityError:
        return False

    return len(inserted) == len(assistant_ids)


async def get_review_session_payload(
    conn: AsyncConnection,
    session_id: int,
) -> dict[str, Any]:
    rows = (await conn.execute(
        review_session_payload_select(session_id)
    )).mappings().all()

    return review_session_payload_from_rows(rows)


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
