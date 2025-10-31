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
            
            # Determine which file to use for transcription (compress if needed)
            file_to_transcribe = audio_file_path
            compressed_audio_path = None
            
            if compress_audio and self.orchestrator.audio_processor:
                try:
                    # Compress audio for transcription and storage
                    compressed_file = self.orchestrator.audio_processor.compress_audio(
                        audio_file_path, force=True
                    )
                    
                    # Move compressed file to correct location
                    compressed_audio_path = output_manager.get_compressed_audio_path()
                    import shutil
                    shutil.move(str(compressed_file), str(compressed_audio_path))
                    
                    # Use compressed file for transcription
                    file_to_transcribe = compressed_audio_path
                    
                except Exception as compression_error:
                    # Fall back to original file if compression fails
                    print(f"⚠️  Compression failed: {compression_error}")
                    file_to_transcribe = audio_file_path
            
            # Perform transcription
            start_time = time.time()
            result = await client.transcribe_file(file_to_transcribe, transcription_config)
            processing_time = time.time() - start_time
            
            # Create the complete response structure matching the cache format
            corrected_deepgram_response = self._create_corrected_deepgram_response(
                audio_file_path, result, transcription_config, processing_time
            )
            
            # Save transcription to correct location
            transcription_path = output_manager.get_transcription_path()
            with open(transcription_path, 'w', encoding='utf-8') as f:
                json.dump(corrected_deepgram_response, f, indent=2, ensure_ascii=False)
            
            # Return API result
            return APITranscriptionResult(
                success=True,
                audio_file=str(audio_file_path),
                result=result,
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
                    if 'result' in transcription_data and transcription_data['result'].get('text'):
                        status_info['status'] = 'completed'
                        status_info['last_attempt'] = transcription_data.get('timestamp')
                        status_info['processing_time'] = transcription_data.get('result', {}).get('processing_time')
                    else:
                        status_info['status'] = 'failed'
                        status_info['error'] = 'Invalid transcription data'
                        
                except (json.JSONDecodeError, KeyError) as e:
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
    
    def _create_corrected_deepgram_response(
        self, 
        audio_file_path: Path, 
        transcription_result, 
        config: TranscriptionConfig,
        processing_time: float
    ) -> Dict[str, Any]:
        """
        Create initial CorrectedDeepgramResponse from raw Deepgram response.
        This establishes the base structure that can be extended with corrections.
        """
        # Convert raw Deepgram response to our structured format
        raw_response = transcription_result.raw_response
        
        # Create the corrected response structure
        corrected_response = {
            "audio_file": str(audio_file_path),
            "service": "deepgram",
            "config": {
                "speaker_labels": config.speaker_labels,
                "custom_vocabulary": [],
                "punctuate": config.punctuate,
                "format_text": config.format_text,
                "language_code": config.language_code,
                "max_speakers": config.max_speakers
            },
            "timestamp": datetime.now().isoformat(),
            "result": {
                "text": transcription_result.text,
                "speakers": [
                    {
                        "speaker": segment.speaker,
                        "start_time": segment.start_time,
                        "end_time": segment.end_time,
                        "text": segment.text,
                        "confidence": segment.confidence
                    }
                    for segment in transcription_result.speakers
                ],
                "confidence": transcription_result.confidence,
                "audio_duration": transcription_result.audio_duration,
                "processing_time": processing_time,
                "raw_response": raw_response
            },
            # Initialize corrections structure (empty initially)
            "corrections": {
                "version": 1,
                "timestamp": datetime.now().isoformat(),
                "speaker_names": {},  # Will store custom speaker name mappings
                "word_corrections": []  # Will store individual word corrections
            }
        }
        
        return corrected_response
    
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