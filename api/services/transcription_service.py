"""TranscriptionService class for web manager integration."""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Import from existing transcription system
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.transcription_orchestrator import TranscriptionOrchestrator
from src.utils.config import ConfigManager
from src.services.transcription_client import TranscriptionConfig
from src.utils.file_scanner import OutputDirectoryManager
from src.utils.audio_processor import AudioProcessor
from src.utils.exceptions import TranscriptionSystemError

from ..models import (
    TranscriptionResult as APITranscriptionResult,
    TranscriptionStatus,
    SpeakerSegment,
    CachedTranscriptionResponse,
    DeepgramResponse,
    DeepgramMetadata,
    DeepgramResults,
    DeepgramChannel,
    DeepgramAlternative,
    WordData
)
from ..config import Settings


class TranscriptionService:
    """Service class for handling transcription operations in the web manager."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config_manager = ConfigManager(settings.config_file)
        
        # Initialize orchestrator for transcription operations
        self.orchestrator = TranscriptionOrchestrator(
            config_manager=self.config_manager,
            output_dir=settings.audio_directory / "transcriptions",
            verbose=True,
            fail_fast=False
        )
        
        # Setup audio processing for compression
        self.orchestrator.setup_audio_processing(enable_compression=True)
    
    async def transcribe_audio(self, audio_file_path: Path, compress_audio: bool = True) -> APITranscriptionResult:
        """
        Transcribe an audio file using the existing Deepgram transcription system.
        Creates initial CorrectedDeepgramResponse from raw Deepgram response.
        Generates compressed audio during transcription process.
        """
        try:
            # Validate audio file exists
            if not audio_file_path.exists():
                raise TranscriptionSystemError(f"Audio file not found: {audio_file_path}")
            
            # Create output manager for this specific audio file
            output_manager = OutputDirectoryManager(audio_file_path)
            output_manager.create_output_structure()
            
            # Get transcription configuration
            transcription_config = self._build_transcription_config()
            
            # Create transcription client
            service_factory = self.orchestrator.service_factory
            client = service_factory.create_client('deepgram', None)  # No glossary files for now
            
            # Always compress audio for transcription - REQUIRED
            if not compress_audio:
                raise TranscriptionSystemError("Audio compression is required but was disabled")
            
            if not self.orchestrator.audio_processor:
                raise TranscriptionSystemError("Audio processor not available for compression")
            
            # Compress audio for transcription and storage - NO FALLBACK
            try:
                compressed_file = self.orchestrator.audio_processor.compress_audio(
                    audio_file_path, force=True
                )
                
                if not compressed_file.exists():
                    raise TranscriptionSystemError(f"Compression failed: output file not created: {compressed_file}")
                
                # Move compressed file to correct location
                compressed_audio_path = output_manager.get_compressed_audio_path()
                import shutil
                shutil.move(str(compressed_file), str(compressed_audio_path))
                
                if not compressed_audio_path.exists():
                    raise TranscriptionSystemError(f"Failed to move compressed file to: {compressed_audio_path}")
                
                # Use compressed file for transcription - ALWAYS
                file_to_transcribe = compressed_audio_path
                
            except Exception as compression_error:
                raise TranscriptionSystemError(f"Audio compression failed (required): {compression_error}")
            
            # Perform transcription using compressed WebM file
            start_time = time.time()
            result = await client.transcribe_file(file_to_transcribe, transcription_config)
            processing_time = time.time() - start_time
            
            # Create RichWordsTranscript format and save raw response to cache
            corrected_deepgram_response = self._create_corrected_deepgram_response(
                audio_file_path, result, transcription_config, processing_time, output_manager
            )
            
            # Save transcription to correct location
            transcription_path = output_manager.get_transcription_path()
            with open(transcription_path, 'w', encoding='utf-8') as f:
                json.dump(corrected_deepgram_response, f, indent=2, ensure_ascii=False)
            
            # Return API result
            # Note: result field is TranscriptionData, but we save transcript separately
            # so we return None and provide cache_file path instead
            return APITranscriptionResult(
                success=True,
                audio_file=str(audio_file_path),
                result=None,  # Transcript is saved separately, accessible via cache_file
                processing_time=processing_time,
                cache_file=str(transcription_path),
                compressed_audio=str(compressed_audio_path) if compressed_audio_path else None
            )
            
        except Exception as e:
            return APITranscriptionResult(
                success=False,
                audio_file=str(audio_file_path),
                error=str(e),
                processing_time=0.0
            )
    
    def get_transcription_status(self, audio_file_path: Path) -> Dict[str, Any]:
        """
        Check transcription status for an audio file.
        Returns status information including completion, error states, and file paths.
        """
        try:
            output_manager = OutputDirectoryManager(audio_file_path)
            transcription_path = output_manager.get_transcription_path()
            compressed_path = output_manager.get_compressed_audio_path()
            
            status_info = {
                'exists': transcription_path.exists(),
                'status': 'none',
                'transcription_file': str(transcription_path) if transcription_path.exists() else None,
                'compressed_audio': str(compressed_path) if compressed_path.exists() else None,
                'last_attempt': None,
                'processing_time': None,
                'error': None
            }
            
            if transcription_path.exists():
                try:
                    # Load transcription data to get status details
                    with open(transcription_path, 'r', encoding='utf-8') as f:
                        transcription_data = json.load(f)
                    
                    # Check if this is a valid transcription result
                    # Support both formats:
                    # 1. New format: RichWordsTranscript (has 'words' at top-level)
                    # 2. Old format: { "result": { "text": "..." } }
                    is_new_format = 'words' in transcription_data and isinstance(transcription_data.get('words'), list)
                    is_old_format = 'result' in transcription_data and transcription_data['result'].get('text')
                    
                    if is_new_format or is_old_format:
                        status_info['status'] = 'completed'
                        # Try to get timestamp from various possible locations
                        status_info['last_attempt'] = (
                            transcription_data.get('_metadata', {}).get('timestamp') or
                            transcription_data.get('timestamp') or
                            transcription_data.get('result', {}).get('timestamp')
                        )
                        status_info['processing_time'] = (
                            transcription_data.get('_metadata', {}).get('processing_time') or
                            transcription_data.get('result', {}).get('processing_time')
                        )
                    else:
                        status_info['status'] = 'failed'
                        status_info['error'] = 'Invalid transcription data: missing words or result.text'
                        
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    status_info['status'] = 'failed'
                    status_info['error'] = f'Corrupted transcription file: {str(e)}'
            
            return status_info
            
        except Exception as e:
            return {
                'exists': False,
                'status': 'failed',
                'error': str(e),
                'transcription_file': None,
                'compressed_audio': None,
                'last_attempt': None,
                'processing_time': None
            }
    
    async def retry_transcription(self, audio_file_path: Path, compress_audio: bool = True) -> APITranscriptionResult:
        """
        Retry transcription for a failed audio file.
        Removes existing transcription files and starts fresh.
        """
        try:
            # Clean up existing transcription files
            output_manager = OutputDirectoryManager(audio_file_path)
            transcription_path = output_manager.get_transcription_path()
            
            if transcription_path.exists():
                transcription_path.unlink()
            
            # Retry transcription
            return await self.transcribe_audio(audio_file_path, compress_audio)
            
        except Exception as e:
            return APITranscriptionResult(
                success=False,
                audio_file=str(audio_file_path),
                error=f"Retry failed: {str(e)}",
                processing_time=0.0
            )
    
    def load_corrected_deepgram_response(self, audio_file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Load existing CorrectedDeepgramResponse from transcription file.
        Returns None if file doesn't exist or is invalid.
        """
        try:
            output_manager = OutputDirectoryManager(audio_file_path)
            transcription_path = output_manager.get_transcription_path()
            
            if not transcription_path.exists():
                return None
            
            with open(transcription_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            print(f"Error loading transcription data: {e}")
            return None
    
    def save_corrected_deepgram_response(self, audio_file_path: Path, corrected_response: Dict[str, Any]) -> bool:
        """
        Save CorrectedDeepgramResponse to transcription file.
        Used when manual corrections are made to the transcript.
        """
        try:
            output_manager = OutputDirectoryManager(audio_file_path)
            transcription_path = output_manager.get_transcription_path()
            
            # Ensure output directory exists
            transcription_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save with proper formatting
            with open(transcription_path, 'w', encoding='utf-8') as f:
                json.dump(corrected_response, f, indent=2, ensure_ascii=False)
            
            return True
            
        except Exception as e:
            print(f"Error saving corrected transcription: {e}")
            return False
    
    def _convert_to_rich_words_transcript(
        self,
        raw_response: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Convert raw Deepgram response to RichWordsTranscript format.
        Extracts words to top-level and enriches them with paragraph markers.
        """
        # Extract words from raw Deepgram response
        results = raw_response.get("results", {})
        channels = results.get("channels", [])
        
        if not channels:
            raise ValueError("No channels found in Deepgram response")
        
        channel = channels[0]
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            raise ValueError("No alternatives found in Deepgram response")
        
        alternative = alternatives[0]
        words = alternative.get("words", [])
        
        if not words:
            raise ValueError("No words found in Deepgram response")
        
        # Extract paragraphs to mark word boundaries
        paragraphs = alternative.get("paragraphs", {}).get("paragraphs", [])
        
        # Initialize paragraph markers
        enriched_words = []
        for word in words:
            enriched_word = {
                **word,
                "paragraph_start": False,
                "paragraph_end": False
            }
            enriched_words.append(enriched_word)
        
        # Mark paragraph boundaries
        if paragraphs:
            for paragraph in paragraphs:
                para_start = paragraph.get("start")
                para_end = paragraph.get("end")
                
                # Find words that match paragraph boundaries (within 0.1s tolerance)
                for word in enriched_words:
                    # Mark paragraph start
                    if para_start is not None and abs(word.get("start", 0) - para_start) < 0.1:
                        word["paragraph_start"] = True
                    
                    # Mark paragraph end
                    if para_end is not None and abs(word.get("end", 0) - para_end) < 0.1:
                        word["paragraph_end"] = True
        
        # Return RichWordsTranscript format
        return {
            "words": enriched_words,
            "corrections": {
                "version": 1,
                "timestamp": datetime.now().isoformat(),
                "speaker_names": {}
            }
        }
    
    def _save_raw_response_cache(
        self,
        audio_file_path: Path,
        raw_response: Dict[str, Any],
        output_manager
    ) -> Path:
        """
        Save raw Deepgram response to cache directory for archival purposes.
        Returns the path to the cache file.
        """
        # Create cache directory for raw responses (inside transcriptions directory)
        cache_dir = output_manager.transcriptions_dir / "cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate cache filename
        cache_filename = f"{audio_file_path.stem}_raw.json"
        cache_path = cache_dir / cache_filename
        
        # Save raw response
        cache_data = {
            "audio_file": str(audio_file_path),
            "timestamp": datetime.now().isoformat(),
            "raw_response": raw_response
        }
        
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(cache_data, f, indent=2, ensure_ascii=False)
        
        return cache_path
    
    def _create_corrected_deepgram_response(
        self, 
        audio_file_path: Path, 
        transcription_result, 
        config: TranscriptionConfig,
        processing_time: float,
        output_manager
    ) -> Dict[str, Any]:
        """
        Create RichWordsTranscript format from raw Deepgram response.
        Saves raw response separately in cache directory.
        """
        # Get raw response
        raw_response = transcription_result.raw_response
        
        # Convert to RichWordsTranscript format
        rich_words_transcript = self._convert_to_rich_words_transcript(raw_response)
        
        # Save raw response to cache
        cache_path = self._save_raw_response_cache(audio_file_path, raw_response, output_manager)
        
        # Add metadata (optional, for tracking) - prefix with _ to indicate it's metadata, not part of RichWordsTranscript
        # Frontend will ignore fields prefixed with _ when processing
        rich_words_transcript["_metadata"] = {
            "audio_file": str(audio_file_path),
            "service": "deepgram",
            "timestamp": datetime.now().isoformat(),
            "raw_response_cache": str(cache_path),
            "config": {
                "speaker_labels": config.speaker_labels,
                "punctuate": config.punctuate,
                "format_text": config.format_text,
                "language_code": config.language_code,
                "max_speakers": config.max_speakers
            }
        }
        
        return rich_words_transcript
    
    def _build_transcription_config(self) -> TranscriptionConfig:
        """Build transcription configuration from config manager."""
        return TranscriptionConfig(
            speaker_labels=self.config_manager.get('transcription.speaker_diarization', True),
            max_speakers=self.config_manager.get('transcription.max_speakers', 3),
            punctuate=True,
            format_text=True,
            language_code='en'
        )
    
    def get_compressed_audio_path(self, audio_file_path: Path) -> Optional[Path]:
        """Get the path to compressed audio file if it exists."""
        try:
            output_manager = OutputDirectoryManager(audio_file_path)
            compressed_path = output_manager.get_compressed_audio_path()
            return compressed_path if compressed_path.exists() else None
        except Exception:
            return None
    
    def get_transcription_file_path(self, audio_file_path: Path) -> Path:
        """Get the path where transcription file should be stored."""
        output_manager = OutputDirectoryManager(audio_file_path)
        return output_manager.get_transcription_path()