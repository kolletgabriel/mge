from pydantic import BaseModel


class Credentials(BaseModel):
    mail: str
    password: str
