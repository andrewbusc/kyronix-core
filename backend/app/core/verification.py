from enum import Enum


class VerificationRequestStatus(str, Enum):
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    SENT = "SENT"
    DECLINED = "DECLINED"
