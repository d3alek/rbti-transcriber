"""
FileSystemScanner service for directory-based audio file management.
Implements requirements 1.1, 1.2, 1.3 for the Audio Transcription Web Manager.
"""

import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import asyncio
import subprocess

# Import from the existing transcription system
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.audio_validator import AudioValidator
from src.utils.cache_manager import CacheManager


class FileSystemScanner:
    """
    Scans directories for MP3 audio files and manages transcription status.
    Provides directory-based organization and metadata extraction.
    """
    
    def __init__(self, base_directory: Optional[Path] = None):
        """Initialize the FileSystemScanner."""
        self.base_directory = Path(base_directory) if base_directory else None
        self.audio_validator = AudioValidator()
        
        # Cache for performance
        self._directory_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, datetime] = {}
        self._cache_ttl = 300  # 5 minutes cache TTL
    
    async def scan_directory(self, directory_path: str) -> Dict:
        """
        Scan a directory for MP3 audio files and organize by seminar groups.
        
        Args:
            directory_path: Path to the directory to scan
            
        Returns:
            Dictionary containing audio files organized by seminar groups
        """
        directory = Path(directory_path)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory_path}")
        
        if not directory.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory_path}")
        
        # Check cache first
        cache_key = str(directory.absolute())
        if self._is_cache_valid(cache_key):
            return self._directory_cache[cache_key]
        
        # Scan for MP3 files recursively, excluding compressed directories
        audio_files = []
        seminar_groups = {}
        
        for mp3_file in directory.rglob("*.mp3"):
            try:
                # Skip files in compressed directories - they're not original audio files
                if "compressed" in mp3_file.parts:
                    continue
                
                # Skip files in transcriptions directories - they're not original audio files
                if "transcriptions" in mp3_file.parts:
                    continue
                
                # Get seminar group from directory structure
                seminar_group = self._get_seminar_group(mp3_file, directory)
                
                # Get file metadata
                file_info = await self._get_audio_file_info(mp3_file)
                
                # Check transcription status
                transcription_status = await self._check_transcription_status(mp3_file)
                file_info.update(transcription_status)
                
                # Check for compressed audio
                compressed_info = await self._check_compressed_audio(mp3_file)
                file_info.update(compressed_info)
                
                # Add seminar group info
                file_info['seminar_group'] = seminar_group
                
                audio_files.append(file_info)
                
                # Organize by seminar group
                if seminar_group not in seminar_groups:
                    seminar_groups[seminar_group] = []
                seminar_groups[seminar_group].append(file_info)
                
            except Exception as e:
                print(f"❌ Error processing {mp3_file}: {e}")
                continue
        
        # Prepare result
        result = {
            'directory': str(directory),
            'total_files': len(audio_files),
            'audio_files': audio_files,
            'seminar_groups': list(seminar_groups.keys()),
            'groups_detail': seminar_groups,
            'transcribed_files': len([f for f in audio_files if f.get('transcription_status') == 'completed']),
            'scan_timestamp': datetime.now().isoformat()
        }
        
        # Cache the result
        self._directory_cache[cache_key] = result
        self._cache_timestamps[cache_key] = datetime.now()
        
        return result
    
    async def get_audio_metadata(self, file_path: str) -> Dict:
        """
        Extract detailed metadata from an audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing audio metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Audio file does not exist: {file_path}")
        
        metadata = {
            'path': str(file_path),
            'filename': file_path.name,
            'size': file_path.stat().st_size,
            'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
        
        # Get audio duration and format info
        try:
            # Use ffprobe to get detailed audio information
            duration = await self._get_audio_duration_ffprobe(file_path)
            if duration:
                metadata['duration'] = duration
            else:
                # Fallback to audio validator
                validation_result = self.audio_validator.validate_single_file(file_path)
                if validation_result.get('is_valid'):
                    metadata['duration'] = validation_result.get('duration', 0.0)
                    metadata['format_info'] = validation_result.get('format_info', {})
        except Exception as e:
            print(f"⚠️ Could not extract audio metadata for {file_path}: {e}")
            metadata['duration'] = 0.0
        
        return metadata
    
    async def check_transcription_status(self, file_path: str) -> Dict:
        """
        Check transcription status for a specific audio file.
        
        Args:
            file_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription status information
        """
        file_path = Path(file_path)
        return await self._check_transcription_status(file_path)
    
    def _get_seminar_group(self, file_path: Path, base_directory: Path) -> str:
        """
        Determine seminar group based on directory structure.
        
        Args:
            file_path: Path to the audio file
            base_directory: Base directory being scanned
            
        Returns:
            Seminar group name based on directory structure
        """
        try:
            # Get relative path from base directory
            relative_path = file_path.relative_to(base_directory)
            
            # If file is in a subdirectory, use the first subdirectory as group name
            if len(relative_path.parts) > 1:
                return relative_path.parts[0]
            else:
                # If file is directly in base directory, use directory name
                return base_directory.name
        except ValueError:
            # File is not under base directory
            return file_path.parent.name
    
    async def _get_audio_file_info(self, file_path: Path) -> Dict:
        """Get basic information about an audio file."""
        stat = file_path.stat()
        
        # Get audio duration
        duration = 0.0
        try:
            # Try ffprobe first
            duration = await self._get_audio_duration_ffprobe(file_path)
            if duration is None:
                # Fallback to audio validator
                validation_result = self.audio_validator.validate_single_file(file_path)
                if validation_result.get('is_valid'):
                    duration = validation_result.get('duration', 0.0)
        except Exception as e:
            print(f"⚠️ Could not get duration for {file_path}: {e}")
            duration = 0.0
        
        # Return relative path if base_directory is set, otherwise absolute path
        if self.base_directory:
            try:
                relative_path = str(file_path.relative_to(self.base_directory))
            except ValueError:
                # file_path is not under base_directory, use absolute path
                relative_path = str(file_path)
        else:
            relative_path = str(file_path)
        
        return {
            'path': relative_path,
            'filename': file_path.name,
            'size': stat.st_size,
            'duration': duration,
            'last_modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'file_id': self._generate_file_id(file_path)
        }
    
    async def _check_transcription_status(self, file_path: Path) -> Dict:
        """
        Check if transcription exists for the audio file.
        
        Returns:
            Dictionary with transcription status information
        """
        transcription_info = {
            'transcription_status': 'none',
            'transcription_files': [],
            'cache_files': [],
            'last_transcription_attempt': None,
            'transcription_error': None
        }
        
        try:
            # Look for transcription files in the new structure: seminar_group/transcriptions/audio.json
            base_dir = file_path.parent
            file_stem = file_path.stem
            
            # Check for new structure: transcriptions directory with JSON files
            transcriptions_dir = base_dir / "transcriptions"
            if transcriptions_dir.exists():
                # Look for the specific transcription JSON file
                transcription_file = transcriptions_dir / f"{file_stem}.json"
                if transcription_file.exists():
                    try:
                        with open(transcription_file, 'r') as f:
                            transcription_data = json.load(f)
                            
                            # Return relative path if base_directory is set, otherwise absolute path
                            if self.base_directory:
                                try:
                                    relative_path = str(transcription_file.relative_to(self.base_directory))
                                except ValueError:
                                    relative_path = str(transcription_file)
                            else:
                                relative_path = str(transcription_file)
                            
                            transcription_info['transcription_files'].append(relative_path)
                            transcription_info['last_transcription_attempt'] = transcription_data.get('timestamp')
                            
                            # Check if transcription was successful
                            if transcription_data.get('result') and transcription_data['result'].get('text'):
                                transcription_info['transcription_status'] = 'completed'
                            else:
                                transcription_info['transcription_status'] = 'failed'
                                transcription_info['transcription_error'] = transcription_data.get('error', 'Unknown error')
                    except Exception as e:
                        print(f"⚠️ Error reading transcription file {transcription_file}: {e}")
                        transcription_info['transcription_status'] = 'failed'
                        transcription_info['transcription_error'] = f"File read error: {e}"
            
            # Also check for legacy structure (for backward compatibility)
            legacy_cache_dir = base_dir / "transcriptions" / "cache"
            if legacy_cache_dir.exists() and transcription_info['transcription_status'] == 'none':
                for cache_file in legacy_cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, 'r') as f:
                            cache_data = json.load(f)
                            if cache_data.get('audio_file') == str(file_path):
                                # Return relative path if base_directory is set, otherwise absolute path
                                if self.base_directory:
                                    try:
                                        relative_path = str(cache_file.relative_to(self.base_directory))
                                    except ValueError:
                                        relative_path = str(cache_file)
                                else:
                                    relative_path = str(cache_file)
                                
                                transcription_info['cache_files'].append(relative_path)
                                transcription_info['last_transcription_attempt'] = cache_data.get('timestamp')
                                
                                if cache_data.get('result') and cache_data['result'].get('text'):
                                    transcription_info['transcription_status'] = 'completed'
                                else:
                                    transcription_info['transcription_status'] = 'failed'
                                    transcription_info['transcription_error'] = cache_data.get('error', 'Unknown error')
                                break
                    except Exception as e:
                        print(f"⚠️ Error reading legacy cache file {cache_file}: {e}")
                        continue
            
        except Exception as e:
            print(f"❌ Error checking transcription status for {file_path}: {e}")
            transcription_info['transcription_error'] = str(e)
        
        return transcription_info
    
    async def _check_compressed_audio(self, file_path: Path) -> Dict:
        """
        Check for compressed audio versions of the file.
        
        Returns:
            Dictionary with compressed audio information
        """
        compressed_info = {
            'has_compressed_version': False,
            'compressed_size': None,
            'compressed_path': None,
            'compression_ratio': None
        }
        
        try:
            # Look for compressed version in the new structure: seminar_group/compressed/audio.mp3
            base_dir = file_path.parent
            compressed_dir = base_dir / "compressed"
            
            if compressed_dir.exists():
                # Look for compressed file with the same name
                compressed_file = compressed_dir / file_path.name
                if compressed_file.exists():
                    compressed_stat = compressed_file.stat()
                    original_size = file_path.stat().st_size
                    
                    # Return relative path if base_directory is set, otherwise absolute path
                    if self.base_directory:
                        try:
                            compressed_path = str(compressed_file.relative_to(self.base_directory))
                        except ValueError:
                            compressed_path = str(compressed_file)
                    else:
                        compressed_path = str(compressed_file)
                    
                    compressed_info.update({
                        'has_compressed_version': True,
                        'compressed_size': compressed_stat.st_size,
                        'compressed_path': compressed_path,
                        'compression_ratio': round((1 - compressed_stat.st_size / original_size) * 100, 1) if original_size > 0 else 0
                    })
        
        except Exception as e:
            print(f"⚠️ Error checking compressed audio for {file_path}: {e}")
        
        return compressed_info
    
    async def _get_audio_duration_ffprobe(self, file_path: Path) -> Optional[float]:
        """
        Get audio duration using ffprobe.
        
        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=duration',
                '-of', 'csv=p=0',
                str(file_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError, FileNotFoundError):
            pass
        
        return None
    
    def _generate_file_id(self, file_path: Path) -> str:
        """Generate a unique ID for a file based on its path and metadata."""
        file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
        return hashlib.md5(file_info.encode()).hexdigest()[:12]
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid."""
        if cache_key not in self._cache_timestamps:
            return False
        
        cache_age = (datetime.now() - self._cache_timestamps[cache_key]).total_seconds()
        return cache_age < self._cache_ttl
    
    def clear_cache(self):
        """Clear the directory cache."""
        self._directory_cache.clear()
        self._cache_timestamps.clear()


# Validation and error handling functions for task 2.3 (optional)
class FileSystemValidator:
    """
    Validates file system access and handles errors.
    This is for the optional task 2.3.
    """
    
    @staticmethod
    def check_directory_permissions(directory_path: str) -> Dict:
        """
        Check directory access permissions.
        
        Returns:
            Dictionary with permission status
        """
        directory = Path(directory_path)
        
        result = {
            'path': str(directory),
            'exists': directory.exists(),
            'is_directory': directory.is_dir() if directory.exists() else False,
            'readable': False,
            'writable': False,
            'executable': False,
            'errors': []
        }
        
        if not directory.exists():
            result['errors'].append("Directory does not exist")
            return result
        
        if not directory.is_dir():
            result['errors'].append("Path is not a directory")
            return result
        
        try:
            # Test read permission
            list(directory.iterdir())
            result['readable'] = True
        except PermissionError:
            result['errors'].append("No read permission")
        
        try:
            # Test write permission by creating a temporary file
            test_file = directory / ".temp_permission_test"
            test_file.touch()
            test_file.unlink()
            result['writable'] = True
        except (PermissionError, OSError):
            result['errors'].append("No write permission")
        
        # Check execute permission (ability to traverse)
        result['executable'] = os.access(directory, os.X_OK)
        if not result['executable']:
            result['errors'].append("No execute permission")
        
        return result
    
    @staticmethod
    def validate_audio_format(file_path: str) -> Dict:
        """
        Validate audio file format.
        
        Returns:
            Dictionary with validation results
        """
        file_path = Path(file_path)
        
        result = {
            'path': str(file_path),
            'is_valid': False,
            'format': None,
            'errors': []
        }
        
        if not file_path.exists():
            result['errors'].append("File does not exist")
            return result
        
        if not file_path.suffix.lower() == '.mp3':
            result['errors'].append("File is not an MP3")
            return result
        
        try:
            # Use ffprobe to validate the file
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-show_entries', 'format=format_name',
                '-of', 'csv=p=0',
                str(file_path)
            ]
            
            result_proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result_proc.returncode == 0:
                format_name = result_proc.stdout.strip()
                if 'mp3' in format_name.lower():
                    result['is_valid'] = True
                    result['format'] = format_name
                else:
                    result['errors'].append(f"Invalid format: {format_name}")
            else:
                result['errors'].append("Could not validate audio format")
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            result['errors'].append("ffprobe not available or failed")
        
        return result
    
    @staticmethod
    def check_transcription_file_integrity(file_path: str) -> Dict:
        """
        Check integrity of transcription cache files.
        
        Returns:
            Dictionary with integrity check results
        """
        file_path = Path(file_path)
        
        result = {
            'path': str(file_path),
            'is_valid': False,
            'errors': []
        }
        
        if not file_path.exists():
            result['errors'].append("File does not exist")
            return result
        
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            # Check required fields
            required_fields = ['audio_file', 'service', 'timestamp', 'result']
            for field in required_fields:
                if field not in data:
                    result['errors'].append(f"Missing required field: {field}")
            
            # Check result structure
            if 'result' in data and isinstance(data['result'], dict):
                result_data = data['result']
                if 'text' not in result_data:
                    result['errors'].append("Missing transcription text in result")
            
            if not result['errors']:
                result['is_valid'] = True
        
        except json.JSONDecodeError as e:
            result['errors'].append(f"Invalid JSON: {e}")
        except Exception as e:
            result['errors'].append(f"Error reading file: {e}")
        
        return result