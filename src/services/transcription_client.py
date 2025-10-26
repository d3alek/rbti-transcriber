"""Abstract base class for transcription service clients."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class TranscriptionConfig:
    """Configuration for transcription requests."""
    speaker_labels: bool = True
    custom_vocabulary: List[str] = field(default_factory=list)
    punctuate: bool = True
    format_text: bool = True
    language_code: str = "en"
    max_speakers: int = 3


@dataclass
class SpeakerSegment:
    """Represents a segment of speech from a specific speaker."""
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""
    text: str
    speakers: List[SpeakerSegment]
    confidence: float
    audio_duration: float
    processing_time: float
    raw_response: dict = field(default_factory=dict)


class TranscriptionClient(ABC):
    """Abstract base class for transcription service clients."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    @abstractmethod
    async def upload_audio(self, file_path: Path) -> str:
        """Upload audio file and return URL or identifier."""
        pass
    
    @abstractmethod
    async def submit_transcription_job(self, audio_url: str, config: TranscriptionConfig) -> str:
        """Submit transcription job and return job ID."""
        pass
    
    @abstractmethod
    async def poll_transcription_status(self, job_id: str) -> TranscriptionResult:
        """Poll transcription status and return result when complete."""
        pass
    
    @abstractmethod
    def apply_custom_vocabulary(self, words: List[str]) -> None:
        """Apply custom vocabulary to the client configuration."""
        pass