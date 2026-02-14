from typing import NewType

from backend.app.domain.user import User

AuthenticatedUser = NewType("AuthenticatedUser", User)
SuperUser = NewType("SuperUser", User)
StaffUser = NewType("StaffUser", User)
