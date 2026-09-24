class NcbiError(RuntimeError):
    """Base class for safe NCBI-facing errors."""


class NcbiUnavailableError(NcbiError):
    """Raised when NCBI cannot be reached after retries."""


class NcbiValidationError(NcbiError):
    """Raised when NCBI data is not acceptable genomic DNA."""
