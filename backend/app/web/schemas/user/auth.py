from pydantic import BaseModel, EmailStr, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from backend.app.domain.user import User


class SignupUser(BaseModel):
    email: EmailStr
    login: str = Field(..., min_length=3, max_length=64)

    firstname: str = Field(..., min_length=3, max_length=64)
    middlename: str = Field(..., min_length=3, max_length=64)
    lastname: str = Field(..., min_length=3, max_length=64)

    password: str = Field(..., min_length=8, max_length=128)
    password_confirm: str = Field(..., min_length=8, max_length=128)

    @field_validator("password")
    @classmethod
    def password_validate(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Password required")
        return v

    @field_validator("password_confirm")
    @classmethod
    def password_confirm_validate(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Confirm Password Required")
        return v

    @field_validator("password_confirm", mode="after")
    @classmethod
    def check_passwords_match(cls, value: str, info: ValidationInfo) -> str:
        if value != info.data["password"]:
            raise ValueError("Passwords do not match")
        return value

    def to_domain(self) -> User:
        return User(
            email=str(self.email),
            login=self.login,
            firstname=self.firstname,
            middlename=self.middlename,
            lastname=self.middlename
        )


class LoginUser(BaseModel):
    email_or_login: EmailStr | str
    password: str = Field(..., min_length=8, max_length=128)
