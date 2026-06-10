from typing import Literal

from pydantic import BaseModel, PositiveInt, UUID4


class Credentials(BaseModel):
    mail: str
    password: str


class SessionData(BaseModel):
    uid: PositiveInt
    rid: Literal[0, 1, 2]
    sid: UUID4
