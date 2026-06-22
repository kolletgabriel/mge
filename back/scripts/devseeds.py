from asyncio import run

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import create_async_engine

from back import db
from back.hash_tools import hash_pw
from back.settings import Settings


PASSWORD = 'senha123'
CLASSES = [
    'Cálculo I',
    'Cálculo II',
    'Estruturas de Dados',
]
PROFESSORS = [
    { 'mail': f'prof{n}@mail.com', 'name': f'Professor {n}', 'role_id': 2 }
    for n in range(1, 6)
]
STUDENTS = [
    { 'mail': f'aluno{n}@mail.com', 'name': f'Aluno {n}', 'role_id': 1 }
    for n in range(1, 10)
]


async def seed_classes(conn) -> tuple[int, int]:
    created = 0
    skipped = 0

    for title in CLASSES:
        if await db.create_class(conn, title) is None:
            skipped += 1
        else:
            created += 1

    return created, skipped


async def seed_users(conn) -> tuple[int, int]:
    created = 0
    skipped = 0
    hashed_password = await hash_pw(PASSWORD)

    for user in [*PROFESSORS, *STUDENTS]:
        if await db.create_user(conn, hashed_password=hashed_password, **user) is None:
            skipped += 1
        else:
            created += 1

    return created, skipped


async def main() -> None:
    engine = create_async_engine(Settings.DB_URL)

    try:
        async with engine.begin() as conn:
            created_classes, skipped_classes = await seed_classes(conn)
            created_users, skipped_users = await seed_users(conn)
    finally:
        await engine.dispose()

    print('Dev seeds finished.')
    print(f'Classes: {created_classes} created, {skipped_classes} skipped.')
    print(f'Users: {created_users} created, {skipped_users} skipped.')
    print(f'Seed password for all users: {PASSWORD}')


if __name__ == '__main__':
    run(main())
