"""Comprehensive error handling and logging for the transcription system."""

import logging
import traceback
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from .exceptions import (
    TranscriptionSystemError, AudioValidationError, TranscriptionServiceError,
    AuthenticationError, FileSystemError, GlossaryError, ConfigurationError
)


class ErrorHandler:
    """Centralized error handling with logging and reporting."""
    
    def __init__(self, log_file: Optional[Path] = None, verbose: bool = False):
        self.verbose = verbose
        self.error_log: List[Dict[str, Any]] = []
        
        # Set up logging
        self.logger = logging.getLogger('transcription_system')
        self.logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if log file specified
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    fail_fast: bool = True) -> bool:
        """Handle an error with appropriate logging and user feedback.
        
        Returns True if the operation should continue, False if it should stop.
        """
        context = context or {}
        error_info = self._create_error_info(error, context)
        self.error_log.append(error_info)
        
        # Log the error
        self._log_error(error, error_info, context)
        
        # Determine if we should continue or stop
        if isinstance(error, (AuthenticationError, ConfigurationError)):
            # Critical errors - always stop
            return False
        elif isinstance(error, AudioValidationError) and fail_fast:
            # Validation errors in fail-fast mode
            return False
        elif isinstance(error, TranscriptionServiceError) and fail_fast:
            # Service errors in fail-fast mode
            return False
        else:
            # Other errors - continue processing
            return True
    
    def _create_error_info(self, error: Exception, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create structured error information."""
        return {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'traceback': traceback.format_exc() if self.verbose else None,
            'severity': self._get_error_severity(error)
        }
    
    def _get_error_severity(self, error: Exception) -> str:
        """Determine error severity level."""
        if isinstance(error, (AuthenticationError, ConfigurationError)):
            return 'critical'
        elif isinstance(error, (TranscriptionServiceError, FileSystemError)):
            return 'high'
        elif isinstance(error, (AudioValidationError, GlossaryError)):
            return 'medium'
        else:
            return 'low'
    
    def _log_error(self, error: Exception, error_info: Dict[str, Any], 
                  context: Dict[str, Any]) -> None:
        """Log error with appropriate level and detail."""
        severity = error_info['severity']
        message = f"{error_info['error_type']}: {error_info['error_message']}"
        
        if context:
            context_str = ', '.join(f"{k}={v}" for k, v in context.items())
            message += f" (Context: {context_str})"
        
        if severity == 'critical':
            self.logger.critical(message)
        elif severity == 'high':
            self.logger.error(message)
        elif severity == 'medium':
            self.logger.warning(message)
        else:
            self.logger.info(message)
        
        # Log full traceback in debug mode
        if self.verbose and error_info['traceback']:
            self.logger.debug(f"Full traceback:\n{error_info['traceback']}")
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered."""
        if not self.error_log:
            return {
                'total_errors': 0,
                'by_severity': {},
                'by_type': {},
                'recent_errors': []
            }
        
        # Count by severity
        severity_counts = {}
        for error in self.error_log:
            severity = error['severity']
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Count by type
        type_counts = {}
        for error in self.error_log:
            error_type = error['error_type']
            type_counts[error_type] = type_counts.get(error_type, 0) + 1
        
        # Get recent errors (last 10)
        recent_errors = self.error_log[-10:] if len(self.error_log) > 10 else self.error_log
        
        return {
            'total_errors': len(self.error_log),
            'by_severity': severity_counts,
            'by_type': type_counts,
            'recent_errors': [
                {
                    'timestamp': error['timestamp'],
                    'type': error['error_type'],
                    'message': error['error_message'],
                    'severity': error['severity']
                }
                for error in recent_errors
            ]
        }
    
    def export_error_log(self, output_path: Path) -> None:
        """Export complete error log to JSON file."""
        try:
            with open(output_path, 'w') as f:
                json.dump({
                    'export_timestamp': datetime.now().isoformat(),
                    'total_errors': len(self.error_log),
                    'errors': self.error_log
                }, f, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to export error log: {e}")
    
    def clear_errors(self) -> None:
        """Clear the error log."""
        self.error_log.clear()


class FailFastErrorHandler(ErrorHandler):
    """Error handler that implements fail-fast behavior for critical operations."""
    
    def __init__(self, log_file: Optional[Path] = None, verbose: bool = False):
        super().__init__(log_file, verbose)
        self.critical_error_occurred = False
    
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    fail_fast: bool = True) -> bool:
        """Handle error with strict fail-fast behavior."""
        should_continue = super().handle_error(error, context, fail_fast)
        
        if not should_continue:
            self.critical_error_occurred = True
            self._log_critical_stop(error, context)
        
        return should_continue
    
    def _log_critical_stop(self, error: Exception, context: Dict[str, Any]) -> None:
        """Log when operation stops due to critical error."""
        self.logger.critical(f"Operation stopped due to critical error: {type(error).__name__}")
        if context:
            self.logger.critical(f"Error context: {context}")
    
    def has_critical_error(self) -> bool:
        """Check if a critical error has occurred."""
        return self.critical_error_occurred


def create_error_handler(output_dir: Optional[Path] = None, 
                        verbose: bool = False, 
                        fail_fast: bool = True) -> ErrorHandler:
    """Factory function to create appropriate error handler."""
    log_file = output_dir / "transcription.log" if output_dir else None
    
    if fail_fast:
        return FailFastErrorHandler(log_file, verbose)
    else:
        return ErrorHandler(log_file, verbose)


def handle_service_unavailable(service: str, error: Exception, 
                              error_handler: ErrorHandler) -> None:
    """Handle service unavailability with clear user guidance."""
    context = {'service': service}
    
    if isinstance(error, AuthenticationError):
        error_handler.logger.critical(f"❌ Authentication failed for {service}")
        error_handler.logger.critical(f"   Please check your {service.upper()}_API_KEY environment variable")
        error_handler.logger.critical(f"   You can get an API key from:")
        
        if service == 'assemblyai':
            error_handler.logger.critical(f"   https://www.assemblyai.com/")
        elif service == 'deepgram':
            error_handler.logger.critical(f"   https://deepgram.com/")
    
    elif isinstance(error, TranscriptionServiceError):
        error_handler.logger.error(f"❌ {service} service error: {error}")
        error_handler.logger.error(f"   This may be a temporary service issue")
        error_handler.logger.error(f"   Try again later or use a different service")
    
    else:
        error_handler.logger.error(f"❌ Unexpected error with {service}: {error}")
    
    error_handler.handle_error(error, context)


def handle_file_processing_error(file_path: Path, error: Exception, 
                               error_handler: ErrorHandler, 
                               fail_fast: bool = True) -> bool:
    """Handle file processing errors with context."""
    context = {
        'file_path': str(file_path),
        'file_name': file_path.name,
        'operation': 'file_processing'
    }
    
    if isinstance(error, AudioValidationError):
        error_handler.logger.warning(f"⚠️  Audio validation failed for {file_path.name}: {error}")
    elif isinstance(error, FileSystemError):
        error_handler.logger.error(f"❌ File system error for {file_path.name}: {error}")
    else:
        error_handler.logger.error(f"❌ Processing error for {file_path.name}: {error}")
    
    return error_handler.handle_error(error, context, fail_fast)