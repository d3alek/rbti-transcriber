"""AssemblyAI transcription service client implementation."""

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


class AssemblyAIClient(TranscriptionClient):
    """AssemblyAI transcription service client with async support."""
    
    BASE_URL = "https://api.assemblyai.com/v2"
    UPLOAD_URL = f"{BASE_URL}/upload"
    TRANSCRIPT_URL = f"{BASE_URL}/transcript"
    
    # Polling configuration
    POLL_INTERVAL_SECONDS = 5
    MAX_POLL_ATTEMPTS = 720  # 1 hour max (720 * 5 seconds)
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        self.custom_vocabulary_words: List[str] = []
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers."""
        if self.session is None or self.session.closed:
            headers = {
                "authorization": self.api_key,
                "content-type": "application/json"
            }
            timeout = aiohttp.ClientTimeout(total=300)  # 5 minute timeout
            self.session = aiohttp.ClientSession(headers=headers, timeout=timeout)
        return self.session
    
    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def upload_audio(self, file_path: Path) -> str:
        """Upload audio file to AssemblyAI and return upload URL."""
        if not file_path.exists():
            raise AudioUploadError(f"Audio file does not exist: {file_path}")
        
        session = await self._get_session()
        
        try:
            # Upload file in chunks
            async with aiofiles.open(file_path, 'rb') as f:
                file_data = await f.read()
            
            upload_headers = {"authorization": self.api_key}
            
            async with session.post(self.UPLOAD_URL, data=file_data, headers=upload_headers) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid AssemblyAI API key")
                elif response.status != 200:
                    error_text = await response.text()
                    raise AudioUploadError(f"Upload failed with status {response.status}: {error_text}")
                
                result = await response.json()
                upload_url = result.get("upload_url")
                
                if not upload_url:
                    raise AudioUploadError("No upload URL returned from AssemblyAI")
                
                return upload_url
        
        except aiohttp.ClientError as e:
            raise AudioUploadError(f"Network error during upload: {str(e)}")
    
    async def submit_transcription_job(self, audio_url: str, config: TranscriptionConfig) -> str:
        """Submit transcription job to AssemblyAI and return job ID."""
        session = await self._get_session()
        
        # Build transcription request
        transcript_request = {
            "audio_url": audio_url,
            "speaker_labels": config.speaker_labels,
            "speakers_expected": min(config.max_speakers, 3),  # AssemblyAI max is typically 3
            "punctuate": config.punctuate,
            "format_text": config.format_text,
            "language_code": config.language_code
        }
        
        # Add custom vocabulary if available
        if self.custom_vocabulary_words:
            # Limit to 1000 terms as per requirements
            vocabulary = self.custom_vocabulary_words[:1000]
            transcript_request["word_boost"] = vocabulary
            transcript_request["boost_param"] = "high"
        
        try:
            async with session.post(self.TRANSCRIPT_URL, json=transcript_request) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid AssemblyAI API key")
                elif response.status != 200:
                    error_text = await response.text()
                    raise TranscriptionJobError(f"Job submission failed with status {response.status}: {error_text}")
                
                result = await response.json()
                job_id = result.get("id")
                
                if not job_id:
                    raise TranscriptionJobError("No job ID returned from AssemblyAI")
                
                return job_id
        
        except aiohttp.ClientError as e:
            raise TranscriptionJobError(f"Network error during job submission: {str(e)}")
    
    async def poll_transcription_status(self, job_id: str) -> TranscriptionResult:
        """Poll transcription status until complete and return result."""
        session = await self._get_session()
        poll_url = f"{self.TRANSCRIPT_URL}/{job_id}"
        
        start_time = time.time()
        
        for attempt in range(self.MAX_POLL_ATTEMPTS):
            try:
                async with session.get(poll_url) as response:
                    if response.status == 401:
                        raise AuthenticationError("Invalid AssemblyAI API key")
                    elif response.status != 200:
                        error_text = await response.text()
                        raise TranscriptionJobError(f"Status check failed with status {response.status}: {error_text}")
                    
                    result = await response.json()
                    status = result.get("status")
                    
                    if status == "completed":
                        return self._parse_transcription_result(result, time.time() - start_time)
                    elif status == "error":
                        error_msg = result.get("error", "Unknown transcription error")
                        raise TranscriptionJobError(f"Transcription failed: {error_msg}")
                    elif status in ["queued", "processing"]:
                        # Continue polling
                        await asyncio.sleep(self.POLL_INTERVAL_SECONDS)
                        continue
                    else:
                        raise TranscriptionJobError(f"Unknown transcription status: {status}")
            
            except aiohttp.ClientError as e:
                raise TranscriptionJobError(f"Network error during status polling: {str(e)}")
        
        # Timeout reached
        raise TranscriptionTimeoutError(f"Transcription timed out after {self.MAX_POLL_ATTEMPTS * self.POLL_INTERVAL_SECONDS} seconds")
    
    def _parse_transcription_result(self, api_response: Dict[str, Any], processing_time: float) -> TranscriptionResult:
        """Parse AssemblyAI API response into TranscriptionResult."""
        text = api_response.get("text", "")
        confidence = api_response.get("confidence", 0.0)
        audio_duration = api_response.get("audio_duration", 0.0)
        
        # Parse speaker segments
        speakers = []
        utterances = api_response.get("utterances", [])
        
        for utterance in utterances:
            speaker_segment = SpeakerSegment(
                speaker=f"Speaker {utterance.get('speaker', 'Unknown')}",
                start_time=utterance.get("start", 0) / 1000.0,  # Convert ms to seconds
                end_time=utterance.get("end", 0) / 1000.0,
                text=utterance.get("text", ""),
                confidence=utterance.get("confidence", 0.0)
            )
            speakers.append(speaker_segment)
        
        return TranscriptionResult(
            text=text,
            speakers=speakers,
            confidence=confidence,
            audio_duration=audio_duration / 1000.0 if audio_duration else 0.0,  # Convert ms to seconds
            processing_time=processing_time,
            raw_response=api_response
        )
    
    def apply_custom_vocabulary(self, words: List[str]) -> None:
        """Apply custom vocabulary to the client configuration."""
        # Store vocabulary words for use in transcription requests
        self.custom_vocabulary_words = words[:1000]  # Limit to 1000 terms
    
    async def transcribe_file(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult:
        """Complete transcription workflow: upload, submit, and poll for results."""
        try:
            # Step 1: Upload audio file
            audio_url = await self.upload_audio(file_path)
            
            # Step 2: Submit transcription job
            job_id = await self.submit_transcription_job(audio_url, config)
            
            # Step 3: Poll for results
            result = await self.poll_transcription_status(job_id)
            
            return result
        
        finally:
            # Ensure session is closed
            await self.close()
    
    def __del__(self):
        """Cleanup session on deletion."""
        if self.session and not self.session.closed:
            # Note: This is not ideal for async cleanup, but serves as a fallback
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass