from enum import StrEnum


class UserRole(StrEnum):
    USER = "user"
    MODERATOR = "moderator"
    ADMIN = "admin"


class VideoStatus(StrEnum):
    UPLOADING = "uploading"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class VideoVisibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"


class ReportStatus(StrEnum):
    PENDING = "pending"
    RESOLVED = "resolved"
    DISMISSED = "dismissed"
