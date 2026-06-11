from uuid import uuid4

from pytest import raises
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine


async def assert_integrity_error(
    engine: AsyncEngine,
    statement: str,
    params: dict | None = None
) -> None:
    with raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(text(statement), params or {})


async def insert_user(
    conn: AsyncConnection,
    role_id: int = 1,
    *,
    mail: str | None = None,
    name: str | None = None,
) -> dict[str, int | str]:
    name = name or f'Test User {uuid4()}'
    mail = mail or f'{uuid4()}@example.com'

    user_id = await conn.scalar(
        text(
            '''
            INSERT INTO users(mail, name, hashed_password, role_id)
            VALUES (:mail, :name, 'hash', :role_id)
            RETURNING id;
            '''
        ),
        {'mail': mail, 'name': name, 'role_id': role_id},
    )

    return {'id': user_id, 'mail': mail, 'name': name}


async def insert_class(
    conn: AsyncConnection,
    *,
    title: str | None = None,
) -> dict[str, int | str]:
    title = title or f'Test Class {uuid4()}'

    class_id = await conn.scalar(
        text(
            '''
            INSERT INTO classes(title)
            VALUES (:title)
            RETURNING id;
            '''
        ),
        {'title': title},
    )

    return {'id': class_id, 'title': title}


async def insert_review_session(
    conn: AsyncConnection,
    class_id: int,
    *,
    max_participants: int = 5,
) -> int:
    return await conn.scalar(
        text(
            '''
            INSERT INTO review_sessions(class_id, starts_at, ends_at, max_participants)
            VALUES (:class_id, '2030-01-01 10:00Z', '2030-01-01 11:00Z', :max_participants)
            RETURNING id;
            '''
        ),
        {'class_id': class_id, 'max_participants': max_participants},
    )
