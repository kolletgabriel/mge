import os
from pathlib import Path

from fastapi.testclient import TestClient
from pytest import fixture
from testcontainers.postgres import PostgresContainer

from back import app, Settings


@fixture(scope='session', autouse=True)
def init_test_db():
    with (
        PostgresContainer('postgres:18.3-trixie', driver='asyncpg')
            .with_volume_mapping(
                host=str(Path(__file__).parent.parent.parent / 'init.sql'),
                container='/docker-entrypoint-initdb.d/init.sql'
            )
    ) as pg:
        Settings.DB_URL = pg.get_connection_url()

        yield


@fixture(scope='session')
def test_client():
    with TestClient(app) as c:
        yield c
