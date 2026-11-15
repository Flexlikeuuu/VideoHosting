from fastapi import HTTPException, status


class DomainException(HTTPException):
    def __init__(self, status_code: int, detail: str):
        super().__init__(status_code=status_code, detail=detail)


class NotFoundException(DomainException):
    def __init__(self, detail: str = "Ресурс не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class ForbiddenException(DomainException):
    def __init__(self, detail: str = "Недостаточно прав доступа"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)


class UnauthorizedException(DomainException):
    def __init__(self, detail: str = "Требуется аутентификация"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


class ConflictException(DomainException):
    def __init__(self, detail: str = "Конфликт данных"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)


class BadRequestException(DomainException):
    def __init__(self, detail: str = "Некорректный запрос"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class RateLimitException(DomainException):
    def __init__(self, detail: str = "Слишком много запросов. Попробуйте позже."):
        super().__init__(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=detail)
