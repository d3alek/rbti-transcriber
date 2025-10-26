"""Factory for creating and managing output formatters."""

from pathlib import Path
from typing import Dict, Any, List, Optional

from .base_formatter import BaseFormatter
from .html_formatter import HTMLFormatter
from .markdown_formatter import MarkdownFormatter
from ..services.transcription_client import TranscriptionResult
from ..utils.cache_manager import CacheManager
from ..utils.exceptions import FileSystemError, ConfigurationError


class FormatterFactory:
    """Factory for creating output formatters and managing format-only operations."""
    
    SUPPORTED_FORMATS = ['html', 'markdown']
    
    def __init__(self, config_manager, cache_manager: CacheManager):
        self.config_manager = config_manager
        self.cache_manager = cache_manager
    
    def create_formatter(self, format_type: str) -> BaseFormatter:
        """Create a formatter for the specified format type."""
        format_type = format_type.lower()
        
        if format_type not in self.SUPPORTED_FORMATS:
            raise ConfigurationError(f"Unsupported format: {format_type}. Supported: {self.SUPPORTED_FORMATS}")
        
        # Get format-specific configuration
        format_config = self.config_manager.get(f'formatting.{format_type}', {})
        
        if format_type == 'html':
            return HTMLFormatter(format_config)
        elif format_type == 'markdown':
            return MarkdownFormatter(format_config)
        else:
            raise ConfigurationError(f"Formatter implementation not found: {format_type}")
    
    def format_from_cache(self, audio_file: Path, service: str, config: Dict[str, Any], 
                         output_formats: List[str], output_manager) -> Dict[str, Any]:
        """Format transcription from cached results without re-transcribing."""
        result = {
            'audio_file': str(audio_file),
            'service': service,
            'success': False,
            'formatted_files': {},
            'errors': [],
            'cache_found': False
        }
        
        # Try to load cached result
        try:
            cached_result = self.cache_manager.load_result(audio_file, service, config)
            
            if cached_result is None:
                result['errors'].append(f"No cached transcription found for {audio_file.name}")
                return result
            
            result['cache_found'] = True
            
            # Validate cached result
            validation_result = self._validate_cached_result(cached_result)
            if not validation_result['is_valid']:
                result['errors'].extend(validation_result['errors'])
                return result
            
            # Format in requested formats
            for format_type in output_formats:
                try:
                    formatter = self.create_formatter(format_type)
                    output_path = output_manager.get_output_path(audio_file, format_type)
                    
                    # Ensure output directory exists
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Format and save
                    formatter.format(cached_result, output_path)
                    result['formatted_files'][format_type] = str(output_path)
                    
                except Exception as e:
                    result['errors'].append(f"Failed to format {format_type}: {str(e)}")
            
            result['success'] = len(result['formatted_files']) > 0
            
        except Exception as e:
            result['errors'].append(f"Error processing cached result: {str(e)}")
        
        return result
    
    def format_from_result(self, transcription_result: TranscriptionResult, audio_file: Path,
                          output_formats: List[str], output_manager) -> Dict[str, Any]:
        """Format transcription result in multiple formats."""
        result = {
            'audio_file': str(audio_file),
            'success': False,
            'formatted_files': {},
            'errors': []
        }
        
        for format_type in output_formats:
            try:
                formatter = self.create_formatter(format_type)
                output_path = output_manager.get_output_path(audio_file, format_type)
                
                # Ensure output directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Format and save
                formatter.format(transcription_result, output_path)
                result['formatted_files'][format_type] = str(output_path)
                
            except Exception as e:
                result['errors'].append(f"Failed to format {format_type}: {str(e)}")
        
        result['success'] = len(result['formatted_files']) > 0
        return result
    
    def batch_format_from_cache(self, audio_files: List[Path], service: str, 
                               config: Dict[str, Any], output_formats: List[str], 
                               output_manager) -> Dict[str, Any]:
        """Format multiple files from cache in batch mode."""
        batch_result = {
            'total_files': len(audio_files),
            'successful_files': 0,
            'failed_files': 0,
            'files_without_cache': 0,
            'results': {},
            'summary': {
                'success_rate': 0.0,
                'cache_hit_rate': 0.0
            }
        }
        
        files_with_cache = 0
        
        for audio_file in audio_files:
            file_result = self.format_from_cache(
                audio_file, service, config, output_formats, output_manager
            )
            
            batch_result['results'][str(audio_file)] = file_result
            
            if file_result['success']:
                batch_result['successful_files'] += 1
            else:
                batch_result['failed_files'] += 1
            
            if file_result['cache_found']:
                files_with_cache += 1
            else:
                batch_result['files_without_cache'] += 1
        
        # Calculate summary statistics
        total = batch_result['total_files']
        if total > 0:
            batch_result['summary']['success_rate'] = batch_result['successful_files'] / total
            batch_result['summary']['cache_hit_rate'] = files_with_cache / total
        
        return batch_result
    
    def _validate_cached_result(self, cached_result: TranscriptionResult) -> Dict[str, Any]:
        """Validate cached transcription result for completeness."""
        validation = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required fields
        if not cached_result.text:
            validation['is_valid'] = False
            validation['errors'].append("Cached result has no text content")
        
        if not cached_result.speakers:
            validation['warnings'].append("Cached result has no speaker segments")
        
        if cached_result.confidence < 0.3:
            validation['warnings'].append(f"Low confidence in cached result: {cached_result.confidence:.1%}")
        
        if cached_result.audio_duration <= 0:
            validation['warnings'].append("Invalid audio duration in cached result")
        
        return validation
    
    def get_cache_formatting_status(self, audio_files: List[Path], service: str, 
                                   config: Dict[str, Any]) -> Dict[str, Any]:
        """Get status of which files can be formatted from cache."""
        status = {
            'total_files': len(audio_files),
            'files_with_cache': [],
            'files_without_cache': [],
            'cache_hit_rate': 0.0
        }
        
        for audio_file in audio_files:
            if self.cache_manager.is_cached(audio_file, service, config):
                status['files_with_cache'].append(audio_file)
            else:
                status['files_without_cache'].append(audio_file)
        
        if status['total_files'] > 0:
            status['cache_hit_rate'] = len(status['files_with_cache']) / status['total_files']
        
        return status
    
    def get_supported_formats(self) -> List[str]:
        """Get list of supported output formats."""
        return self.SUPPORTED_FORMATS.copy()
    
    def validate_format_configuration(self, format_type: str) -> Dict[str, Any]:
        """Validate configuration for a specific format."""
        validation = {
            'format': format_type,
            'is_configured': True,
            'errors': [],
            'warnings': []
        }
        
        if format_type not in self.SUPPORTED_FORMATS:
            validation['is_configured'] = False
            validation['errors'].append(f"Unsupported format: {format_type}")
            return validation
        
        # Check format-specific configuration
        format_config = self.config_manager.get(f'formatting.{format_type}')
        if not format_config:
            validation['warnings'].append(f"No configuration found for {format_type} format")
        
        return validation