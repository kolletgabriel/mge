from os import getenv
from typing import TYPE_CHECKING, TypedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine
from starlette.middleware.sessions import SessionMiddleware

from .endpoints import auth, user

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class Settings:
    DB_URL = getenv('DB_URL', default='postgresql+asyncpg://postgres:postgres@db:5432/postgres')
    SESSION_SECRET = getenv('SESSION_SECRET', default='secret')
    MAIL_HOST = getenv('MAIL_HOST')
    MAIL_PORT = int(getenv('MAIL_PORT', default='587'))
    MAIL_USERNAME = getenv('MAIL_USERNAME')
    MAIL_PASSWORD = getenv('MAIL_PASSWORD')
    MAIL_FROM = getenv('MAIL_FROM', default='noreply@mge.local')
    MAIL_START_TLS = getenv('MAIL_START_TLS', default='true').lower() == 'true'


class State(TypedDict):
    db: AsyncEngine


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[State]:
    engine = create_async_engine(Settings.DB_URL)

    yield {'db': engine}

    await engine.dispose()


app = FastAPI(root_path='/api', lifespan=lifespan)
app.include_router(auth.router)
app.include_router(user.router)
app.add_middleware(SessionMiddleware, secret_key=Settings.SESSION_SECRET, max_age=None)
