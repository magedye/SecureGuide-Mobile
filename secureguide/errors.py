"""Domain errors exposed by the SecureGuide service layer."""


class SecureGuideError(Exception):
    """Base error safe for presentation-layer handling."""


class NotFoundError(SecureGuideError):
    """The requested profile, artifact, template, or operational row is absent."""


class ValidationError(SecureGuideError):
    """The request violates a controlled value or workflow rule."""


class ActiveProfileRequiredError(ValidationError):
    """An operation needs either an explicit profile or a persisted active one."""


class AuthorizationError(SecureGuideError):
    """The actor is not entitled to act in the workflow role it claimed."""
