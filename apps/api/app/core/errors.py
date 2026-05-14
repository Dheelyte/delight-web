"""Typed error hierarchy mapped to HTTP responses by a single exception handler."""

from __future__ import annotations


class AppError(Exception):
    """Base for all domain-level errors. HTTP status set by subclasses."""

    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class DomainError(AppError):
    status_code = 400
    code = "domain_error"


class AuthError(AppError):
    status_code = 401
    code = "unauthorized"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationError(AppError):
    status_code = 422
    code = "validation_error"


class ExternalServiceError(AppError):
    status_code = 502
    code = "external_service_error"
