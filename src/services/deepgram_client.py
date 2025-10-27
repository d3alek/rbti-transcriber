"""Deepgram transcription service client implementation using latest API."""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
import time
import json

from .transcription_client import (
    TranscriptionClient, TranscriptionConfig, TranscriptionResult, SpeakerSegment,
    TranscriptionJobError, TranscriptionTimeoutError, AudioUploadError
)
from ..utils.exceptions import AuthenticationError


class DeepgramClient(TranscriptionClient):
    """Deepgram transcription service client using latest Nova-2 model."""
    
    BASE_URL = "https://api.deepgram.com/v1"
    LISTEN_URL = f"{BASE_URL}/listen"
    
    def __init__(self, api_key: str):
        super().__init__(api_key)
        self.session: Optional[aiohttp.ClientSession] = None
        self.custom_vocabulary_words: List[str] = []
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session with proper headers."""
        if self.session is None or self.session.closed:
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "audio/mpeg"  # Set for audio upload
            }
            timeout = aiohttp.ClientTimeout(total=600)  # 10 minute timeout for large files
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
        
        # Add custom vocabulary if available (Nova-3 uses keyterm)
        if self.custom_vocabulary_words:
            # Limit to 1000 terms as per requirements
            vocabulary = self.custom_vocabulary_words[:1000]
            params["keyterm"] = ",".join(vocabulary)
        
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
        """Parse modern Deepgram API response into TranscriptionResult."""
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
        
        # Parse speaker segments from utterances (modern format)
        speakers = []
        utterances = results.get("utterances", [])
        
        for utterance in utterances:
            # Handle both old and new format
            speaker_id = utterance.get("speaker", utterance.get("speaker_id", 0))
            speaker_segment = SpeakerSegment(
                speaker=f"Speaker {speaker_id}",
                start_time=utterance.get("start", 0.0),
                end_time=utterance.get("end", 0.0),
                text=utterance.get("transcript", ""),
                confidence=utterance.get("confidence", 0.0)
            )
            speakers.append(speaker_segment)
        
        # Get audio duration from metadata with fallback calculation
        metadata = results.get("metadata", {})
        audio_duration = metadata.get("duration", 0.0)
        
        # If no duration in metadata, calculate from segments
        if audio_duration == 0.0 and speakers:
            # Use the end time of the last segment as duration
            audio_duration = max(segment.end_time for segment in speakers)
        
        # If no utterances but we have paragraphs, use those
        if not speakers and "paragraphs" in results:
            paragraphs = results.get("paragraphs", {}).get("paragraphs", [])
            for i, paragraph in enumerate(paragraphs):
                speaker_segment = SpeakerSegment(
                    speaker=f"Speaker {paragraph.get('speaker', 0)}",
                    start_time=paragraph.get("start", 0.0),
                    end_time=paragraph.get("end", 0.0),
                    text=paragraph.get("text", ""),
                    confidence=confidence  # Use overall confidence
                )
                speakers.append(speaker_segment)
            
            # Calculate duration from paragraphs if still zero
            if audio_duration == 0.0 and speakers:
                audio_duration = max(segment.end_time for segment in speakers)
        
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
    
    def _get_best_keyterms(self, words: List[str], limit: int = 50) -> List[str]:
        """Select the best keyterms for Nova-3 from the glossary."""
        if not words:
            return []
        
        # Priority RBTI terms that should always be included
        priority_terms = [
            'RBTI', 'Reams', 'Carey Reams', 'biological ionization', 'ionization',
            'urine pH', 'saliva pH', 'conductivity', 'brix', 'refractometer',
            'energy level', 'mineral deficiency', 'calcium', 'magnesium', 
            'potassium', 'phosphorus', 'perfect range', 'zone one', 'zone two',
            'nitrate nitrogen', 'ammonia nitrogen', 'carbohydrate reading',
            'biological age', 'conductivity reading', 'pH meter', 'debris reading'
        ]
        
        # Find priority terms that exist in our glossary
        selected_terms = []
        words_lower = [w.lower() for w in words]
        
        for priority_term in priority_terms:
            # Look for exact matches or partial matches
            for word in words:
                if (priority_term.lower() == word.lower() or 
                    priority_term.lower() in word.lower() or
                    word.lower() in priority_term.lower()):
                    if word not in selected_terms:
                        selected_terms.append(word)
                        break
        
        # Add remaining high-value terms
        remaining_slots = limit - len(selected_terms)
        if remaining_slots > 0:
            # Prefer shorter, more specific terms
            remaining_words = [w for w in words if w not in selected_terms]
            
            # Score terms by RBTI relevance and length
            scored_terms = []
            for word in remaining_words:
                score = 0
                word_lower = word.lower()
                
                # Boost RBTI-specific patterns
                if any(pattern in word_lower for pattern in ['ph', 'ion', 'bio', 'mineral', 'calc', 'magn', 'reams']):
                    score += 3
                if any(pattern in word_lower for pattern in ['reading', 'level', 'test', 'range', 'zone']):
                    score += 2
                if any(pattern in word_lower for pattern in ['conductivity', 'brix', 'energy', 'calcium']):
                    score += 4
                
                # Prefer shorter terms (more focused)
                if len(word.split()) == 1:
                    score += 1
                elif len(word.split()) == 2:
                    score += 2
                
                # Penalize very long terms
                if len(word) > 20:
                    score -= 1
                
                scored_terms.append((word, score))
            
            # Sort by score and take the best remaining terms
            scored_terms.sort(key=lambda x: x[1], reverse=True)
            selected_terms.extend([term for term, score in scored_terms[:remaining_slots]])
        
        return selected_terms[:limit]
    
    async def transcribe_file(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult:
        """Complete transcription workflow using Deepgram's latest API."""
        session = await self._get_session()
        start_time = time.time()
        
        try:
            # Build modern query parameters using latest model
            params = {
                "model": "nova-3",  # Latest Nova-3 model for best accuracy
                "language": config.language_code,
                "punctuate": str(config.punctuate).lower(),
                "diarize": str(config.speaker_labels).lower(),
                "smart_format": str(config.format_text).lower(),
                "utterances": "true",
                "paragraphs": "true",  # Enable paragraph detection
                "summarize": "false",  # Disable summary for transcription
                "detect_topics": "false"  # Disable topic detection
            }
            
            # Add custom vocabulary if available (Nova-3 uses keyterm with max 50 terms)
            if self.custom_vocabulary_words:
                # For Nova-3, use only the 50 best keyterms for optimal performance
                best_keyterms = self._get_best_keyterms(self.custom_vocabulary_words, 50)
                if best_keyterms:
                    params["keyterm"] = ",".join(best_keyterms)
                    # Optional: log the selected keyterms for debugging
                    # print(f"Using {len(best_keyterms)} keyterms for Nova-3: {best_keyterms[:10]}...")
            
            # Read audio file
            async with aiofiles.open(file_path, 'rb') as f:
                audio_data = await f.read()
            
            # Make request to Deepgram
            async with session.post(self.LISTEN_URL, params=params, data=audio_data) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Deepgram API key")
                elif response.status == 413:
                    raise AudioUploadError("File too large for Deepgram. Try compressing the audio file.")
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
    
    async def _transcribe_sync(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult:
        """Transcribe using synchronous endpoint (for files < 2MB)."""
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
    
    async def _transcribe_async(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult:
        """Transcribe using asynchronous endpoint (for larger files)."""
        session = await self._get_session()
        start_time = time.time()
        
        try:
            # Step 1: Submit transcription job
            response = await self._submit_async_job(file_path, config, session)
            
            # Step 2: Handle response (could be immediate results or request_id for polling)
            if isinstance(response, dict) and "results" in response:
                # Got immediate results (synchronous response)
                result = response
            else:
                # Got request_id, need to poll
                result = await self._poll_async_job(response, session)
            
            processing_time = time.time() - start_time
            return self._parse_transcription_result(result, processing_time)
        
        finally:
            await self.close()
    
    async def _submit_async_job(self, file_path: Path, config: TranscriptionConfig, session: aiohttp.ClientSession) -> str:
        """Submit async transcription job to Deepgram."""
        # Build query parameters for async transcription
        params = {
            "language": config.language_code,
            "punctuate": str(config.punctuate).lower(),
            "diarize": str(config.speaker_labels).lower(),
            "smart_format": str(config.format_text).lower(),
            "utterances": "true",
            "callback_method": "post"  # Enable async processing
        }
        
        # Add custom vocabulary if available
        if self.custom_vocabulary_words:
            vocabulary = self.custom_vocabulary_words[:1000]
            params["keywords"] = ",".join(vocabulary)
        
        # Use the correct async transcription endpoint
        url = f"{self.BASE_URL}/listen"
        
        # Read the audio file
        async with aiofiles.open(file_path, 'rb') as f:
            audio_data = await f.read()
        
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/mpeg"
        }
        
        async with session.post(url, params=params, data=audio_data, headers=headers) as response:
            if response.status == 401:
                raise AuthenticationError("Invalid Deepgram API key")
            elif response.status not in [200, 201]:
                error_text = await response.text()
                raise TranscriptionJobError(f"Deepgram async job submission failed with status {response.status}: {error_text}")
            
            result = await response.json()
            
            # Deepgram's /listen endpoint returns results immediately, not a request_id
            # Check if we got transcription results directly
            if "results" in result:
                # This is a synchronous response with results
                return result
            elif "request_id" in result:
                # This is an async response with request_id for polling
                return result.get("request_id")
            else:
                raise TranscriptionJobError("Unexpected response format from Deepgram")
    
    async def _poll_async_job(self, request_id: str, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Poll async transcription job until completion."""
        url = f"{self.BASE_URL}/listen/{request_id}"
        headers = {"Authorization": f"Token {self.api_key}"}
        
        max_attempts = 240  # 20 minutes max (5 second intervals)
        
        for attempt in range(max_attempts):
            async with session.get(url, headers=headers) as response:
                if response.status == 401:
                    raise AuthenticationError("Invalid Deepgram API key")
                elif response.status != 200:
                    error_text = await response.text()
                    raise TranscriptionJobError(f"Deepgram async polling failed with status {response.status}: {error_text}")
                
                result = await response.json()
                status = result.get("status")
                
                if status == "completed":
                    # Return the results directly
                    return result.get("results", result)
                elif status == "failed":
                    error_msg = result.get("error", "Unknown error")
                    raise TranscriptionJobError(f"Deepgram async transcription failed: {error_msg}")
                elif status in ["queued", "processing"]:
                    # Continue polling
                    await asyncio.sleep(5)
                    continue
                else:
                    raise TranscriptionJobError(f"Unknown Deepgram status: {status}")
        
        raise TranscriptionTimeoutError(f"Deepgram async transcription timed out after {max_attempts * 5} seconds")
    
    def __del__(self):
        """Cleanup session on deletion."""
        if self.session and not self.session.closed:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.close())
            except RuntimeError:
                pass