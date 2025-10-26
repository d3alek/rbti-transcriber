"""Deepgram transcription service client implementation."""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from .transcription_client import (
    TranscriptionClient, TranscriptionConfig, TranscriptionResult, SpeakerSegment,
    TranscriptionJobError, TranscriptionTimeoutError, AudioUploadError
)
from ..utils.exceptions import AuthenticationError


class DeepgramClient(TranscriptionClient):
    """Deepgram transcription service client with async support."""
    
    BASE_URL = "https://api.deepgram.com/v1"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        self.custom_vocabulary_words: List[str] = []
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def upload_audio(self, file_path: Path) -> str:
        """For Deepgram, we don't need separate upload - return file path as URL."""
        if not file_path.exists():
            raise AudioUploadError(f"Audio file does not exist: {file_path}")
        
        # Deepgram accepts direct file upload in transcription request
        return str(file_path)
    
    async def submit_transcription_job(self, audio_url: str, config: TranscriptionConfig) -> str:
        """Submit transcription job to Deepgram (synchronous API)."""
        session = await self._get_session()
        
        # Build query parameters for Deepgram API
        params = {
            "model": "nova-2",  # Latest model
            "language": config.language_code,
            "punctuate": str(config.punctuate).lower(),
            "diarize": str(config.speaker_labels).lower(),
            "smart_format": str(config.format_text).lower(),
            "utterances": "true"  # Get utterance-level results
        }
        
        # Add custom vocabulary if available
        if self.custom_vocabulary_words:
            # Limit to 1000 terms as per requirements
            vocabulary = self.custom_vocabulary_words[:1000]
            params["keywords"] = ",".join(vocabulary)
        
        # Deepgram uses synchronous transcription, so we'll use the listen endpoint
        url = f"{self.BASE_URL}/listen"
        
        try:
            # Read audio file
            audio_path = Path(audio_url)  # audio_url is actually file path for Deepgram
            async with aiofiles.open(audio_path, 'rb') as f:
                audio_data = await f.read()
            
            # Submit transcription request
            headers = {"Authorization": f"Token {self.api_key}"}
            
            async with session.post(url, params=params, data=audio_data, headers=headers) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Deepgram API key")
                elif response.status != 200:
                    error_text = await response.text()
                    raise TranscriptionJobError(f"Deepgram transcription failed with status {response.status}: {error_text}")
                
                result = await response.json()
                
                # For Deepgram, we return the result directly as "job_id" since it's synchronous
                return str(id(result))  # Use object id as fake job_id
        
        except aiohttp.ClientError as e:
            raise TranscriptionJobError(f"Network error during Deepgram transcription: {str(e)}")
    
    async def poll_transcription_status(self, job_id: str) -> TranscriptionResult:
        """For Deepgram, transcription is synchronous, so we return cached result."""
        # This is a bit of a hack - in a real implementation, we'd store the result
        # For now, we'll re-run the transcription since Deepgram is synchronous
        raise NotImplementedError("Use transcribe_file method for Deepgram - synchronous API")
    
    def _parse_transcription_result(self, api_response: Dict[str, Any], processing_time: float) -> TranscriptionResult:
        """Parse Deepgram API response into TranscriptionResult."""
        results = api_response.get("results", {})
        channels = results.get("channels", [])
        
        if not channels:
            raise TranscriptionJobError("No channels found in Deepgram response")
        
        channel = channels[0]  # Use first channel
        alternatives = channel.get("alternatives", [])
        
        if not alternatives:
            raise TranscriptionJobError("No alternatives found in Deepgram response")
        
        alternative = alternatives[0]  # Use best alternative
        text = alternative.get("transcript", "")
        confidence = alternative.get("confidence", 0.0)
        
        # Parse speaker segments from utterances
        speakers = []
        utterances = results.get("utterances", [])
        
        for utterance in utterances:
            speaker_segment = SpeakerSegment(
                speaker=f"Speaker {utterance.get('speaker', 0)}",
                start_time=utterance.get("start", 0.0),
                end_time=utterance.get("end", 0.0),
                text=utterance.get("transcript", ""),
                confidence=utterance.get("confidence", 0.0)
            )
            speakers.append(speaker_segment)
        
        # Get audio duration from metadata
        metadata = results.get("metadata", {})
        audio_duration = metadata.get("duration", 0.0)
        
        return TranscriptionResult(
            text=text,
            speakers=speakers,
            confidence=confidence,
            audio_duration=audio_duration,
            processing_time=processing_time,
            raw_response=api_response
        )
    
    def apply_custom_vocabulary(self, words: List[str]) -> None:
        """Apply custom vocabulary to the client configuration."""
        # Store vocabulary words for use in transcription requests
        self.custom_vocabulary_words = words[:1000]  # Limit to 1000 terms
    
    async def transcribe_file(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult:
        """Complete transcription workflow for Deepgram (synchronous API)."""
        session = await self._get_session()
        start_time = time.time()
        
        try:
            # Build query parameters
            params = {
                "model": "nova-2",
                "language": config.language_code,
                "punctuate": str(config.punctuate).lower(),
                "diarize": str(config.speaker_labels).lower(),
                "smart_format": str(config.format_text).lower(),
                "utterances": "true"
            }
            
            # Add custom vocabulary if available
            if self.custom_vocabulary_words:
                vocabulary = self.custom_vocabulary_words[:1000]
                params["keywords"] = ",".join(vocabulary)
            
            url = f"{self.BASE_URL}/listen"
            
            # Read and submit audio file
            async with aiofiles.open(file_path, 'rb') as f:
                audio_data = await f.read()
            
            headers = {"Authorization": f"Token {self.api_key}"}
            
            async with session.post(url, params=params, data=audio_data, headers=headers) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Deepgram API key")
                elif response.status != 200:
                    error_text = await response.text()
                    raise TranscriptionJobError(f"Deepgram transcription failed with status {response.status}: {error_text}")
                
                result = await response.json()
                processing_time = time.time() - start_time
                
                return self._parse_transcription_result(result, processing_time)
        
        except aiohttp.ClientError as e:
            raise TranscriptionJobError(f"Network error during Deepgram transcription: {str(e)}")
        
        finally:
            await self.close()
    
    def __del__(self):
        """Cleanup session on deletion."""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass