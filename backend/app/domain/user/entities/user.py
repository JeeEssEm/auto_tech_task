from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    email: str
    login: str

    firstname: str
    middlename: str
    lastname: str
