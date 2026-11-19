"""Explicit domain errors. No silent excepts anywhere in the pipeline."""


class DomainError(Exception):
    """Base class for expected domain errors."""

    code = "domain_error"

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(DomainError):
    """Input data does not satisfy the expected contract."""

    code = "validation_error"
