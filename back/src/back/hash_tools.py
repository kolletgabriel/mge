from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from argon2.profiles import CHEAPEST
from fastapi.concurrency import run_in_threadpool
from pydantic import SecretStr


_ph = PasswordHasher.from_parameters(CHEAPEST)
_dummy_pw = 'dummypassword'
_dummy_hash = _ph.hash(_dummy_pw)


async def hash_pw(provided_pw: SecretStr) -> str:
    return await run_in_threadpool(_ph.hash, provided_pw.get_secret_value())


async def matches(hashed_pw: str, provided_pw: SecretStr) -> bool:
    try:
        return await run_in_threadpool(
            _ph.verify,
            hashed_pw,
            provided_pw.get_secret_value()
        )
    except VerifyMismatchError:
        return False


async def verify_dummy() -> None:
    try:
        await run_in_threadpool(_ph.verify, _dummy_hash, f'not{_dummy_pw}')
    except VerifyMismatchError:
        return
