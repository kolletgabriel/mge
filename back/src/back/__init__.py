from typing import TYPE_CHECKING, TypedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from starlette.middleware.sessions import SessionMiddleware

from .endpoints import admin, auth, user
from .settings import Settings

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class State(TypedDict):
    db: AsyncEngine


async def ensure_adm(engine: AsyncEngine) -> None:
    from .db import create_user, get_login_user

    async def _create_adm(conn):
        from .hash_tools import hash_pw
        await create_user(
            conn,
            mail = Settings.MGE_ADMIN_SEED_MAIL,
            name = Settings.MGE_ADMIN_SEED_NAME,
            hashed_password = await hash_pw(Settings.MGE_ADMIN_SEED_PW),
            role_id = 0
        )

    async with engine.begin() as conn:
        adm = await get_login_user(conn, Settings.MGE_ADMIN_SEED_MAIL)
        if adm is None:
            await _create_adm(conn)
        elif adm['role_id'] != 0:
            from uuid import uuid4
            Settings.MGE_ADMIN_SEED_MAIL = f'{uuid4()}_admin@mge.com'
            await _create_adm(conn)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[State]:
    engine = create_async_engine(Settings.DB_URL)
    try:
        await ensure_adm(engine)
        yield {'db': engine}
    finally:
        await engine.dispose()


app = FastAPI(root_path='/api', lifespan=lifespan)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(user.router)
app.add_middleware(SessionMiddleware, secret_key=Settings.SESSION_SECRET, max_age=None)
