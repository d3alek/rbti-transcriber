"""Cache manager for transcription responses and resume logic."""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

from .exceptions import FileSystemError
from ..services.transcription_client import TranscriptionResult, SpeakerSegment


class CacheManager:
    """Manages caching of transcription service responses and resume logic."""
    
    def __init__(self, cache_directory: Path):
        self.cache_directory = Path(cache_directory)
        self.cache_directory.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_key(self, audio_file: Path, service: str, config_hash: str) -> str:
        """Generate unique cache key for audio file, service, and configuration."""
        file_info = f"{audio_file.name}_{audio_file.stat().st_size}_{audio_file.stat().st_mtime}"
        cache_input = f"{file_info}_{service}_{config_hash}"
        return hashlib.md5(cache_input.encode()).hexdigest()
    
    def _get_config_hash(self, config: Dict[str, Any]) -> str:
        """Generate hash of transcription configuration for cache key."""
        # Sort config to ensure consistent hashing
        config_str = json.dumps(config, sort_keys=True)
        return hashlib.md5(config_str.encode()).hexdigest()[:8]
    
    def get_cache_path(self, audio_file: Path, service: str, config: Dict[str, Any]) -> Path:
        """Get cache file path for given audio file and configuration."""
        config_hash = self._get_config_hash(config)
        cache_key = self._get_cache_key(audio_file, service, config_hash)
        return self.cache_directory / f"{cache_key}.json"
    
    def is_cached(self, audio_file: Path, service: str, config: Dict[str, Any]) -> bool:
        """Check if transcription result is cached for given parameters."""
        cache_path = self.get_cache_path(audio_file, service, config)
        return cache_path.exists() and cache_path.stat().st_size > 0
    
    def save_result(self, audio_file: Path, service: str, config: Dict[str, Any], 
                   result: TranscriptionResult) -> None:
        """Save transcription result to cache."""
        cache_path = self.get_cache_path(audio_file, service, config)
        
        # Convert result to serializable format
        cache_data = {
            'audio_file': str(audio_file),
            'service': service,
            'config': config,
            'timestamp': datetime.now().isoformat(),
            'result': {
                'text': result.text,
                'speakers': [
                    {
                        'speaker': segment.speaker,
                        'start_time': segment.start_time,
                        'end_time': segment.end_time,
                        'text': segment.text,
                        'confidence': segment.confidence
                    }
                    for segment in result.speakers
                ],
                'confidence': result.confidence,
                'audio_duration': result.audio_duration,
                'processing_time': result.processing_time,
                'raw_response': result.raw_response
            }
        }
        
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise FileSystemError(f"Cannot save cache file {cache_path}: {e}")
    
    def load_result(self, audio_file: Path, service: str, config: Dict[str, Any]) -> Optional[TranscriptionResult]:
        """Load transcription result from cache."""
        cache_path = self.get_cache_path(audio_file, service, config)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Validate cache data structure
            if 'result' not in cache_data:
                return None
            
            result_data = cache_data['result']
            
            # Reconstruct SpeakerSegment objects
            speakers = [
                SpeakerSegment(
                    speaker=segment['speaker'],
                    start_time=segment['start_time'],
                    end_time=segment['end_time'],
                    text=segment['text'],
                    confidence=segment['confidence']
                )
                for segment in result_data.get('speakers', [])
            ]
            
            # Reconstruct TranscriptionResult
            return TranscriptionResult(
                text=result_data['text'],
                speakers=speakers,
                confidence=result_data['confidence'],
                audio_duration=result_data['audio_duration'],
                processing_time=result_data['processing_time'],
                raw_response=result_data.get('raw_response', {})
            )
            
        except (IOError, json.JSONDecodeError, KeyError) as e:
            print(f"Warning: Invalid cache file {cache_path}: {e}")
            return None
    
    def clear_cache(self, audio_file: Optional[Path] = None) -> None:
        """Clear cache files. If audio_file is specified, clear only that file's cache."""
        if audio_file:
            # Clear cache for specific file (all services and configs)
            file_prefix = f"{audio_file.name}_{audio_file.stat().st_size}_{audio_file.stat().st_mtime}"
            for cache_file in self.cache_directory.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        cache_data = json.load(f)
                    if cache_data.get('audio_file') == str(audio_file):
                        cache_file.unlink()
                except (IOError, json.JSONDecodeError):
                    continue
        else:
            # Clear all cache files
            for cache_file in self.cache_directory.glob("*.json"):
                try:
                    cache_file.unlink()
                except IOError:
                    continue
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about cached files."""
        cache_files = list(self.cache_directory.glob("*.json"))
        total_size = sum(f.stat().st_size for f in cache_files)
        
        return {
            'total_files': len(cache_files),
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_directory': str(self.cache_directory)
        }


class ResumeManager:
    """Manages resume logic for interrupted transcription sessions."""
    
    def __init__(self, cache_manager: CacheManager, output_manager):
        self.cache_manager = cache_manager
        self.output_manager = output_manager
    
    def should_skip_file(self, audio_file: Path, service: str, config: Dict[str, Any], 
                        output_formats: List[str]) -> bool:
        """Determine if file should be skipped based on existing outputs."""
        # Check if we have cached transcription result
        has_cache = self.cache_manager.is_cached(audio_file, service, config)
        
        # Check if all requested output formats exist for this service
        existing_outputs = self.output_manager.get_existing_files(audio_file, service)
        has_all_outputs = all(existing_outputs.get(fmt, False) for fmt in output_formats)
        
        # Skip if we have cache AND all outputs exist for this service
        return has_cache and has_all_outputs
    
    def get_processing_status(self, audio_files: List[Path], service: str, 
                            config: Dict[str, Any], output_formats: List[str]) -> Dict[str, Any]:
        """Get processing status for a list of audio files."""
        total_files = len(audio_files)
        skipped_files = []
        pending_files = []
        
        for audio_file in audio_files:
            if self.should_skip_file(audio_file, service, config, output_formats):
                skipped_files.append(audio_file)
            else:
                pending_files.append(audio_file)
        
        return {
            'total_files': total_files,
            'skipped_files': len(skipped_files),
            'pending_files': len(pending_files),
            'skipped_list': skipped_files,
            'pending_list': pending_files,
            'completion_percentage': round((len(skipped_files) / total_files) * 100, 1) if total_files > 0 else 0
        }