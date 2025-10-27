"""File management service for the web API."""

import hashlib
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

# Import from the existing transcription system
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.file_scanner import MP3FileScanner
from src.utils.cache_manager import CacheManager
from src.utils.audio_validator import AudioValidator
from src.utils.config import ConfigManager

from ..models import AudioFileInfo, TranscriptionStatus, TranscriptionData, SpeakerSegment, PublicationStatus


class AudioFileManager:
    """Manages audio files and their transcription status."""
    
    def __init__(self, audio_directory: Path):
        self.audio_directory = Path(audio_directory)
        self.scanner = MP3FileScanner(self.audio_directory)
        
        # Initialize transcription system components
        self.config_manager = ConfigManager()
        self.cache_manager = CacheManager(self.audio_directory / "transcriptions" / "cache")
        self.validator = AudioValidator()
        
        # Cache for file information
        self._file_cache: Dict[str, AudioFileInfo] = {}
        self._cache_timestamp: Optional[datetime] = None
    
    def _generate_file_id(self, file_path: Path) -> str:
        """Generate a unique ID for a file based on its path and metadata."""
        file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
        return hashlib.md5(file_info.encode()).hexdigest()[:12]
    
    async def list_files(self) -> List[AudioFileInfo]:
        """List all MP3 files with their transcription status."""
        # Check if we need to refresh the cache
        if self._should_refresh_cache():
            await self._refresh_file_cache()
        
        return list(self._file_cache.values())
    
    async def rescan_directory(self) -> int:
        """Force rescan of the audio directory."""
        await self._refresh_file_cache()
        return len(self._file_cache)
    
    async def get_file_info(self, file_id: str) -> Optional[AudioFileInfo]:
        """Get detailed information about a specific file."""
        if file_id not in self._file_cache:
            await self._refresh_file_cache()
        
        return self._file_cache.get(file_id)
    
    async def get_transcription_data(self, file_id: str) -> Optional[TranscriptionData]:
        """Get transcription data for a specific file."""
        file_info = await self.get_file_info(file_id)
        if not file_info or not file_info.has_transcription:
            return None
        
        try:
            file_path = Path(file_info.path)
            
            # Look for cached transcription files directly
            cache_dir = self.audio_directory / "transcriptions" / "cache"
            if cache_dir.exists():
                deepgram_transcription = None
                other_transcription = None
                
                for cache_file in cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, 'r') as f:
                            import json
                            cache_data = json.load(f)
                            
                            # Check if this cache file is for our audio file
                            if cache_data.get('audio_file') == str(file_path):
                                result_data = cache_data.get('result', {})
                                service = cache_data.get('service', 'unknown')
                                
                                # Convert to our API format
                                speakers = []
                                for segment in result_data.get('speakers', []):
                                    speakers.append(SpeakerSegment(
                                        speaker=segment.get('speaker', 'Unknown'),
                                        start_time=segment.get('start_time', 0.0),
                                        end_time=segment.get('end_time', 0.0),
                                        text=segment.get('text', ''),
                                        confidence=segment.get('confidence', 0.0)
                                    ))
                                
                                transcription_data = TranscriptionData(
                                    text=result_data.get('text', ''),
                                    speakers=speakers,
                                    duration=result_data.get('audio_duration', 0.0),
                                    confidence=result_data.get('confidence', 0.0),
                                    audio_duration=result_data.get('audio_duration', 0.0),
                                    processing_time=result_data.get('processing_time', 0.0)
                                )
                                
                                # Prefer Deepgram transcriptions
                                if service.lower() == 'deepgram':
                                    deepgram_transcription = transcription_data
                                else:
                                    other_transcription = transcription_data
                                    
                    except Exception as e:
                        print(f"❌ Error reading cache file {cache_file}: {e}")
                        continue
                
                # Return Deepgram transcription if available, otherwise return any other transcription
                return deepgram_transcription or other_transcription
            
            return None
            
        except Exception as e:
            print(f"❌ Error loading transcription data: {e}")
            return None
    
    async def save_transcription_data(self, file_id: str, transcription_data: TranscriptionData) -> bool:
        """Save transcription data for a specific file."""
        file_info = await self.get_file_info(file_id)
        if not file_info:
            return False
        
        try:
            file_path = Path(file_info.path)
            
            # Create cache directory if it doesn't exist
            cache_dir = self.audio_directory / "transcriptions" / "cache"
            cache_dir.mkdir(parents=True, exist_ok=True)
            
            # Generate cache filename
            cache_filename = f"{file_path.stem}_{file_id}.json"
            cache_file_path = cache_dir / cache_filename
            
            # Convert transcription data to cache format
            cache_data = {
                "audio_file": str(file_path),
                "file_id": file_id,
                "timestamp": datetime.now().isoformat(),
                "result": {
                    "text": transcription_data.text,
                    "speakers": [
                        {
                            "speaker": segment.speaker,
                            "start_time": segment.start_time,
                            "end_time": segment.end_time,
                            "text": segment.text,
                            "confidence": segment.confidence
                        }
                        for segment in transcription_data.speakers
                    ],
                    "duration": transcription_data.duration,
                    "confidence": transcription_data.confidence,
                    "audio_duration": transcription_data.audio_duration,
                    "processing_time": transcription_data.processing_time
                }
            }
            
            # Save to cache file
            with open(cache_file_path, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            # Update file cache
            await self._refresh_single_file(file_path)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving transcription data: {e}")
            return False

    async def delete_transcription(self, file_id: str) -> bool:
        """Delete transcription data for a specific file."""
        file_info = await self.get_file_info(file_id)
        if not file_info:
            return False
        
        try:
            file_path = Path(file_info.path)
            
            # Delete cached transcriptions for all services
            deleted_any = False
            for service in ['deepgram', 'assemblyai']:
                cache_key = self._get_cache_key(file_path, service)
                if self.cache_manager.delete_result(cache_key):
                    deleted_any = True
            
            # Also delete any direct cache files
            cache_dir = self.audio_directory / "transcriptions" / "cache"
            if cache_dir.exists():
                cache_filename = f"{file_path.stem}_{file_id}.json"
                cache_file_path = cache_dir / cache_filename
                if cache_file_path.exists():
                    cache_file_path.unlink()
                    deleted_any = True
            
            # Update file cache
            if deleted_any:
                await self._refresh_single_file(file_path)
            
            return deleted_any
            
        except Exception as e:
            print(f"❌ Error deleting transcription: {e}")
            return False
    
    def _should_refresh_cache(self) -> bool:
        """Check if the file cache should be refreshed."""
        if not self._cache_timestamp:
            return True
        
        # Refresh every 30 seconds
        return (datetime.now() - self._cache_timestamp).total_seconds() > 30
    
    async def _refresh_file_cache(self):
        """Refresh the internal file cache."""
        try:
            # Scan for MP3 files
            mp3_files = self.scanner.scan_mp3_files()
            
            # Process each file
            new_cache = {}
            for file_path in mp3_files:
                file_info = await self._process_file(file_path)
                if file_info:
                    new_cache[file_info.id] = file_info
            
            self._file_cache = new_cache
            self._cache_timestamp = datetime.now()
            
        except Exception as e:
            print(f"❌ Error refreshing file cache: {e}")
    
    async def _refresh_single_file(self, file_path: Path):
        """Refresh cache for a single file."""
        try:
            file_info = await self._process_file(file_path)
            if file_info:
                self._file_cache[file_info.id] = file_info
        except Exception as e:
            print(f"❌ Error refreshing single file: {e}")
    
    async def _process_file(self, file_path: Path) -> Optional[AudioFileInfo]:
        """Process a single file and extract its information."""
        try:
            if not file_path.exists():
                return None
            
            # Generate file ID
            file_id = self._generate_file_id(file_path)
            
            # Get file stats
            stat = file_path.stat()
            
            # Get audio duration (this might be slow for many files)
            duration = 0.0
            try:
                # Use the audio validator to get duration
                validation_result = self.validator.validate_single_file(file_path)
                if validation_result['is_valid']:
                    duration = validation_result.get('duration', 0.0)
            except Exception:
                pass  # Duration will remain 0.0
            
            # Check transcription status
            has_transcription, transcription_status = self._check_transcription_status(file_path)
            
            # Check publication status (placeholder for now)
            publication_status = self._check_publication_status(file_id)
            
            return AudioFileInfo(
                id=file_id,
                name=file_path.name,
                path=str(file_path),
                size=stat.st_size,
                duration=duration,
                has_transcription=has_transcription,
                transcription_status=transcription_status,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
                publication_status=publication_status
            )
            
        except Exception as e:
            print(f"❌ Error processing file {file_path}: {e}")
            return None
    
    def _check_transcription_status(self, file_path: Path) -> tuple[bool, TranscriptionStatus]:
        """Check if a file has transcription and its status."""
        try:
            # Check for existing HTML/Markdown files in transcriptions directory
            transcriptions_dir = self.audio_directory / "transcriptions"
            
            # Check HTML directory
            html_dir = transcriptions_dir / "html"
            if html_dir.exists():
                for html_file in html_dir.glob("*.html"):
                    if file_path.stem in html_file.name:
                        return True, TranscriptionStatus.COMPLETED
            
            # Check Markdown directory  
            md_dir = transcriptions_dir / "markdown"
            if md_dir.exists():
                for md_file in md_dir.glob("*.md"):
                    if file_path.stem in md_file.name:
                        return True, TranscriptionStatus.COMPLETED
            
            # Check for cached transcriptions
            cache_dir = transcriptions_dir / "cache"
            if cache_dir.exists():
                for cache_file in cache_dir.glob("*.json"):
                    try:
                        with open(cache_file, 'r') as f:
                            import json
                            cache_data = json.load(f)
                            if cache_data.get('audio_file') == str(file_path):
                                return True, TranscriptionStatus.COMPLETED
                    except:
                        continue
            
            return False, TranscriptionStatus.NONE
            
        except Exception as e:
            print(f"❌ Error checking transcription status: {e}")
            return False, TranscriptionStatus.NONE
    
    def _check_publication_status(self, file_id: str) -> Optional[PublicationStatus]:
        """Check if a file is published (placeholder implementation)."""
        # TODO: Implement actual publication status checking
        # This would check the GitHub repository or local publication database
        return None
    
    def _get_cache_key(self, file_path: Path, service: str) -> str:
        """Generate cache key for a file and service."""
        # This should match the cache key generation in the transcription system
        file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
        return hashlib.md5(f"{file_info}_{service}".encode()).hexdigest()[:16]