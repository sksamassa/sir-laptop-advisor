"""Domain errors shared by all contexts.

Every domain error carries a stable machine-readable code and a Russian
user-facing message, so the HTTP layer never invents wording.
"""

from __future__ import annotations


class DomainError(Exception):
    """Base class for expected, user-correctable failures."""

    code = "domain_error"
    status_code = 400
    message_ru = "Некорректный запрос"

    def __init__(self, message_ru: str | None = None, **details: object) -> None:
        self.message_ru = message_ru or self.message_ru
        self.details = details
        super().__init__(self.message_ru)

    def to_payload(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message_ru,
                "details": self.details or None,
            }
        }


class ValidationError(DomainError):
    code = "validation_error"
    status_code = 400
    message_ru = "Некорректные данные"


class InvalidWeights(ValidationError):
    code = "invalid_weights"
    message_ru = "Сумма весов должна быть 100%"


class NotFound(DomainError):
    code = "not_found"
    status_code = 404
    message_ru = "Не найдено"


class Forbidden(DomainError):
    code = "forbidden"
    status_code = 403
    message_ru = "Нет доступа"


class Unauthorized(DomainError):
    code = "unauthorized"
    status_code = 401
    message_ru = "Требуется вход"


class Conflict(DomainError):
    code = "conflict"
    status_code = 409
    message_ru = "Конфликт данных"


class EmptyCatalog(ValidationError):
    code = "empty_catalog"
    message_ru = "Каталог пуст"
