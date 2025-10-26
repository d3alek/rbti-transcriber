"""Audio file validation and quality checks with fail-fast logic."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import subprocess
import json

from .exceptions import AudioValidationError
from .audio_processor import AudioProcessor


class AudioValidator:
    """Comprehensive audio file validator with quality checks."""
    
    # Validation thresholds
    MIN_DURATION_SECONDS = 10      # Minimum 10 seconds
    MAX_DURATION_SECONDS = 14400   # Maximum 4 hours
    MIN_FILE_SIZE_BYTES = 50000    # Minimum 50KB
    MAX_FILE_SIZE_BYTES = 500 * 1024 * 1024  # Maximum 500MB
    MIN_SAMPLE_RATE = 8000         # Minimum 8kHz
    SUPPORTED_CODECS = ['mp3', 'mpeg']
    
    def __init__(self, audio_processor: Optional[AudioProcessor] = None):
        self.audio_processor = audio_processor
    
    def validate_file_basic(self, audio_file: Path) -> Dict[str, Any]:
        """Perform basic file validation checks."""
        validation_result = {
            'file_path': str(audio_file),
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check file existence
        if not audio_file.exists():
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"File does not exist: {audio_file}")
            return validation_result
        
        # Check if it's a file (not directory)
        if not audio_file.is_file():
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Path is not a file: {audio_file}")
            return validation_result
        
        # Check file extension
        if audio_file.suffix.lower() != '.mp3':
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"File is not an MP3: {audio_file}")
            return validation_result
        
        # Check file size
        file_size = audio_file.stat().st_size
        if file_size < self.MIN_FILE_SIZE_BYTES:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f"File too small ({file_size} bytes, minimum {self.MIN_FILE_SIZE_BYTES}): {audio_file}"
            )
        elif file_size > self.MAX_FILE_SIZE_BYTES:
            validation_result['is_valid'] = False
            validation_result['errors'].append(
                f"File too large ({file_size} bytes, maximum {self.MAX_FILE_SIZE_BYTES}): {audio_file}"
            )
        
        return validation_result
    
    def validate_audio_integrity(self, audio_file: Path) -> Dict[str, Any]:
        """Validate audio file integrity using FFmpeg."""
        validation_result = {
            'file_path': str(audio_file),
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'audio_info': {}
        }
        
        try:
            # Use audio processor to get detailed info
            if self.audio_processor:
                audio_info = self.audio_processor.analyze_audio_bitrate(audio_file)
                validation_result['audio_info'] = audio_info
                
                # Validate duration
                duration = audio_info.get('duration_seconds', 0)
                if duration < self.MIN_DURATION_SECONDS:
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(
                        f"Audio too short ({duration:.1f}s, minimum {self.MIN_DURATION_SECONDS}s): {audio_file}"
                    )
                elif duration > self.MAX_DURATION_SECONDS:
                    validation_result['warnings'].append(
                        f"Audio very long ({duration:.1f}s, {duration/3600:.1f}h): {audio_file}"
                    )
                
                # Validate sample rate
                sample_rate = audio_info.get('sample_rate', 0)
                if sample_rate < self.MIN_SAMPLE_RATE:
                    validation_result['warnings'].append(
                        f"Low sample rate ({sample_rate}Hz, recommended minimum {self.MIN_SAMPLE_RATE}Hz): {audio_file}"
                    )
                
                # Validate codec
                codec = audio_info.get('codec', '').lower()
                if codec not in self.SUPPORTED_CODECS:
                    validation_result['warnings'].append(
                        f"Unusual codec ({codec}), expected MP3: {audio_file}"
                    )
                
                # Check for audio streams
                if audio_info.get('channels', 0) == 0:
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(f"No audio channels detected: {audio_file}")
            
            else:
                # Fallback: basic FFprobe check without audio processor
                cmd = [
                    'ffprobe',
                    '-v', 'error',
                    '-select_streams', 'a:0',
                    '-show_entries', 'stream=duration,codec_name',
                    '-of', 'csv=p=0',
                    str(audio_file)
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                if not result.stdout.strip():
                    validation_result['is_valid'] = False
                    validation_result['errors'].append(f"No valid audio stream found: {audio_file}")
        
        except subprocess.CalledProcessError as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Audio integrity check failed: {e.stderr}")
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def validate_for_transcription(self, audio_file: Path) -> Dict[str, Any]:
        """Comprehensive validation for transcription readiness."""
        # Start with basic validation
        result = self.validate_file_basic(audio_file)
        
        # If basic validation fails, return early (fail-fast)
        if not result['is_valid']:
            return result
        
        # Perform integrity validation
        integrity_result = self.validate_audio_integrity(audio_file)
        
        # Merge results
        result['is_valid'] = result['is_valid'] and integrity_result['is_valid']
        result['errors'].extend(integrity_result['errors'])
        result['warnings'].extend(integrity_result['warnings'])
        result['audio_info'] = integrity_result.get('audio_info', {})
        
        return result
    
    def validate_batch(self, audio_files: List[Path], fail_fast: bool = True) -> Dict[str, Any]:
        """Validate a batch of audio files with optional fail-fast behavior."""
        batch_result = {
            'total_files': len(audio_files),
            'valid_files': [],
            'invalid_files': [],
            'files_with_warnings': [],
            'validation_results': {},
            'summary': {
                'valid_count': 0,
                'invalid_count': 0,
                'warning_count': 0
            }
        }
        
        for audio_file in audio_files:
            try:
                validation_result = self.validate_for_transcription(audio_file)
                batch_result['validation_results'][str(audio_file)] = validation_result
                
                if validation_result['is_valid']:
                    batch_result['valid_files'].append(audio_file)
                    batch_result['summary']['valid_count'] += 1
                    
                    if validation_result['warnings']:
                        batch_result['files_with_warnings'].append(audio_file)
                        batch_result['summary']['warning_count'] += 1
                else:
                    batch_result['invalid_files'].append(audio_file)
                    batch_result['summary']['invalid_count'] += 1
                    
                    # Fail-fast: stop on first invalid file if requested
                    if fail_fast:
                        break
            
            except Exception as e:
                # Handle unexpected validation errors
                error_result = {
                    'file_path': str(audio_file),
                    'is_valid': False,
                    'errors': [f"Validation exception: {str(e)}"],
                    'warnings': []
                }
                batch_result['validation_results'][str(audio_file)] = error_result
                batch_result['invalid_files'].append(audio_file)
                batch_result['summary']['invalid_count'] += 1
                
                if fail_fast:
                    break
        
        return batch_result
    
    def get_validation_summary(self, validation_results: Dict[str, Any]) -> str:
        """Generate human-readable validation summary."""
        summary = validation_results['summary']
        total = validation_results['total_files']
        
        lines = [
            f"Audio Validation Summary:",
            f"  Total files: {total}",
            f"  Valid files: {summary['valid_count']}",
            f"  Invalid files: {summary['invalid_count']}",
            f"  Files with warnings: {summary['warning_count']}"
        ]
        
        if validation_results['invalid_files']:
            lines.append("\nInvalid files:")
            for invalid_file in validation_results['invalid_files'][:5]:  # Show first 5
                file_result = validation_results['validation_results'][str(invalid_file)]
                errors = '; '.join(file_result['errors'][:2])  # Show first 2 errors
                lines.append(f"  - {invalid_file.name}: {errors}")
            
            if len(validation_results['invalid_files']) > 5:
                lines.append(f"  ... and {len(validation_results['invalid_files']) - 5} more")
        
        return '\n'.join(lines)