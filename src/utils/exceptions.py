"""Custom exceptions for the Audio Transcription System."""


class TranscriptionSystemError(Exception):
    """Base exception for all transcription system errors."""
    pass


class AudioValidationError(TranscriptionSystemError):
    """Raised when audio file validation fails."""
    pass


class TranscriptionServiceError(TranscriptionSystemError):
    """Raised when transcription service encounters an error."""
    pass


class AuthenticationError(TranscriptionSystemError):
    """Raised when API authentication fails."""
    pass


class FileSystemError(TranscriptionSystemError):
    """Raised when file system operations fail."""
    pass


class GlossaryError(TranscriptionSystemError):
    """Raised when glossary management encounters an error."""
    pass


class ConfigurationError(TranscriptionSystemError):
    """Raised when configuration is invalid or missing."""
    pass