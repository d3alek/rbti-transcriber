"""OpenAI transcription service client implementation."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from openai import OpenAI
from openai import OpenAIError, AuthenticationError as OpenAIAuthError, RateLimitError

from .transcription_client import (
    TranscriptionClient, TranscriptionConfig, TranscriptionResult, SpeakerSegment,
    TranscriptionJobError, TranscriptionTimeoutError, AudioUploadError
)
from ..utils.exceptions import AuthenticationError


class OpenAITranscriptionError(TranscriptionJobError):
    """OpenAI-specific transcription errors."""
    pass


class OpenAIFileSizeError(AudioUploadError):
    """File too large for OpenAI API."""
    pass


class OpenAIRateLimitError(TranscriptionJobError):
    """OpenAI API rate limit exceeded."""
    pass


class OpenAIClient(TranscriptionClient):
    """OpenAI transcription service client using gpt-4o-transcribe-diarize model."""
    
    MAX_FILE_SIZE_MB = 25
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.client = OpenAI(api_key=api_key)
    
    async def close(self):
        """Close the OpenAI client (no-op for OpenAI client)."""
        pass
    
    async def upload_audio(self, file_path: Path) -> str:
        """For OpenAI, we don't need separate upload - return file path as URL."""
        if not file_path.exists():
            raise AudioUploadError(f"Audio file does not exist: {file_path}")
        
        # Check file size limit (25MB for OpenAI)
        file_size_mb = file_path.stat().st_size / (1024 * 1024)
        if file_size_mb > self.MAX_FILE_SIZE_MB:
            raise OpenAIFileSizeError(
                f"File size ({file_size_mb:.1f}MB) exceeds OpenAI limit of {self.MAX_FILE_SIZE_MB}MB. "
                f"Please compress the audio file or use a different service."
            )
        
        # OpenAI accepts direct file upload in transcription request
        return str(file_path)
    
    async def submit_transcription_job(self, audio_url: str, config: TranscriptionConfig) -> str:
        """Submit transcription job to OpenAI (synchronous API)."""
        # OpenAI uses synchronous transcription, so we'll use the transcriptions endpoint directly
        # This method is not used in the current implementation but kept for interface compatibility
        raise NotImplementedError("Use transcribe_file method for OpenAI - synchronous API")
    
    async def poll_transcription_status(self, job_id: str) -> TranscriptionResult:
        """For OpenAI, transcription is synchronous, so we return cached result."""
        # This is not used since OpenAI is synchronous
        raise NotImplementedError("Use transcribe_file method for OpenAI - synchronous API")
    
    def _parse_transcription_result(self, api_response: Dict[str, Any], processing_time: float) -> TranscriptionResult:
        """Parse OpenAI diarized_json API response into TranscriptionResult."""
        text = api_response.get("text") or ""
        duration = api_response.get("duration") or 0.0
        segments = api_response.get("segments", [])
        
        if not segments:
            raise OpenAITranscriptionError("No segments found in OpenAI response")
        
        # Parse speaker segments from diarized_json format
        speakers = []
        for segment in segments:
            # Convert OpenAI speaker format (SPEAKER_00, SPEAKER_01) to consistent format
            openai_speaker = segment.get("speaker", "SPEAKER_00")
            speaker_num = openai_speaker.replace("SPEAKER_", "")
            try:
                speaker_id = int(speaker_num)
            except ValueError:
                speaker_id = 0
            
            # Handle None values with proper defaults
            start_time = segment.get("start")
            end_time = segment.get("end")
            text = segment.get("text")
            
            speaker_segment = SpeakerSegment(
                speaker=f"Speaker {speaker_id}",
                start_time=start_time if start_time is not None else 0.0,
                end_time=end_time if end_time is not None else 0.0,
                text=text if text is not None else "",
                confidence=1.0  # OpenAI doesn't provide confidence scores
            )
            speakers.append(speaker_segment)
        
        # Calculate overall confidence (OpenAI doesn't provide this, so we use 1.0)
        confidence = 1.0
        
        return TranscriptionResult(
            text=text,
            speakers=speakers,
            confidence=confidence,
            audio_duration=duration,
            processing_time=processing_time,
            raw_response=api_response
        )
    
    def apply_custom_vocabulary(self, words: List[str]) -> None:
        """OpenAI doesn't support custom vocabulary, so this is a no-op."""
        # OpenAI's gpt-4o-transcribe-diarize model doesn't support custom vocabulary
        pass
    
    async def transcribe_file(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult:
        """Complete transcription workflow using OpenAI's API."""
        start_time = time.time()
        
        try:
            # Check file size before upload
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.MAX_FILE_SIZE_MB:
                raise OpenAIFileSizeError(
                    f"File size ({file_size_mb:.1f}MB) exceeds OpenAI limit of {self.MAX_FILE_SIZE_MB}MB"
                )
            
            print(f"🔄 Making OpenAI API request...")
            
            # Open the audio file
            with open(file_path, 'rb') as audio_file:
                # Make request to OpenAI using the official client
                transcript = self.client.audio.transcriptions.create(
                    model="gpt-4o-transcribe-diarize",
                    file=audio_file,
                    response_format="diarized_json",
                    chunking_strategy="auto",
                    language=config.language_code,
                )
            
            print(f"✅ Received OpenAI response")
            processing_time = time.time() - start_time
            
            # Convert the response to dict if it's not already
            if hasattr(transcript, 'model_dump'):
                result = transcript.model_dump()
            elif hasattr(transcript, 'dict'):
                result = transcript.dict()
            else:
                result = dict(transcript)
            
            print(f"📊 Response contains {len(result.get('segments', []))} segments")
            
            return self._parse_transcription_result(result, processing_time)
        
        except OpenAIAuthError as e:
            raise AuthenticationError(f"Invalid OpenAI API key: {str(e)}")
        except RateLimitError as e:
            raise OpenAIRateLimitError(f"OpenAI API rate limit exceeded: {str(e)}")
        except OpenAIError as e:
            raise OpenAITranscriptionError(f"OpenAI transcription failed: {str(e)}")
        except Exception as e:
            raise OpenAITranscriptionError(f"Unexpected error during OpenAI transcription: {str(e)}")
        
        finally:
            await self.close()
    
    def __del__(self):
        """Cleanup on deletion."""
        pass