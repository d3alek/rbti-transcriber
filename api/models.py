"""Pydantic models for the API."""

from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime
from enum import Enum


class TranscriptionStatus(str, Enum):
    """Transcription status enumeration."""
    NONE = "none"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class PublicationStatus(BaseModel):
    """Publication status model."""
    is_published: bool
    published_url: Optional[str] = None
    published_date: Optional[datetime] = None
    github_commit_hash: Optional[str] = None


class AudioFileInfo(BaseModel):
    """Audio file information model."""
    id: str
    name: str
    path: str
    size: int
    duration: float
    has_transcription: bool
    transcription_status: TranscriptionStatus
    last_modified: datetime
    publication_status: Optional[PublicationStatus] = None


class TranscriptionRequest(BaseModel):
    """Transcription request model."""
    file_id: str
    service: Literal['assemblyai', 'deepgram']
    compress_audio: bool = True
    output_formats: List[str] = ['html', 'markdown']


class TranscriptionProgress(BaseModel):
    """Transcription progress model."""
    job_id: str
    status: TranscriptionStatus
    progress: float
    message: str
    error: Optional[str] = None


class SpeakerSegment(BaseModel):
    """Speaker segment model."""
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float


class TranscriptionData(BaseModel):
    """Transcription data model."""
    text: str
    speakers: List[SpeakerSegment]
    duration: float
    confidence: float
    audio_duration: float
    processing_time: float


class PublicationRequest(BaseModel):
    """Publication request model."""
    file_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []


class ExportRequest(BaseModel):
    """Export request model."""
    file_id: str
    format: Literal['html', 'markdown', 'txt']


class APIResponse(BaseModel):
    """Generic API response model."""
    success: bool
    message: str
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None