from os import getenv


class Settings:
    DB_URL = getenv('DB_URL', default='postgresql+asyncpg://postgres:postgres@db:5432/postgres')
    SESSION_SECRET = getenv('SESSION_SECRET', default='secret')
    MAIL_HOST = getenv('MAIL_HOST')
    MAIL_PORT = int(getenv('MAIL_PORT', default='587'))
    MAIL_USERNAME = getenv('MAIL_USERNAME')
    MAIL_PASSWORD = getenv('MAIL_PASSWORD')
    MAIL_FROM = getenv('MAIL_FROM', default='noreply@mge.local')
    MAIL_START_TLS = getenv('MAIL_START_TLS', default='true').lower() == 'true'
