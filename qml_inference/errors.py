class InvalidInput(ValueError):
    """The request does not match the bounded research schema."""


class ArtifactError(RuntimeError):
    """A versioned inference artifact failed its readiness checks."""
