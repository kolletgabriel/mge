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


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[State]:
    from .db import create_user
    from .hash_tools import hash_pw

    engine = create_async_engine(Settings.DB_URL)
    async with engine.begin() as conn:
        await create_user(
            conn,
            mail = Settings.MGE_ADMIN_SEED_MAIL,
            name = Settings.MGE_ADMIN_SEED_NAME,
            hashed_password = await hash_pw(Settings.MGE_ADMIN_SEED_PW),
            role_id = 0
        )

    try:
        yield {'db': engine}
    finally:
        await engine.dispose()


app = FastAPI(root_path='/api', lifespan=lifespan)
app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(user.router)
app.add_middleware(SessionMiddleware, secret_key=Settings.SESSION_SECRET, max_age=None)
