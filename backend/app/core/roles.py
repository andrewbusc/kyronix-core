from enum import Enum


class RoleEnum(str, Enum):
    EMPLOYEE = "EMPLOYEE"
    ADMIN = "ADMIN"


class EmploymentStatus(str, Enum):
    ACTIVE = "ACTIVE"
    FORMER_EMPLOYEE = "FORMER_EMPLOYEE"
