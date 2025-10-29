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
    service: Literal['deepgram'] = 'deepgram'
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


# Enhanced Transcript Editor Models

class WordData(BaseModel):
    """Word-level timing and confidence data from Deepgram."""
    word: str
    start: float
    end: float
    confidence: float
    speaker: int
    speaker_confidence: float
    punctuated_word: str
    index: Optional[int] = None


class SentenceData(BaseModel):
    """Sentence-level data with word breakdown."""
    id: str
    text: str
    start: float
    end: float
    words: List[WordData]
    speaker: int


class ParagraphData(BaseModel):
    """Paragraph-level data for editor display."""
    id: str
    text: str
    start_time: float
    end_time: float
    speaker: int
    sentences: List[SentenceData]
    words: List[WordData]
    confidence: float


class DeepgramMetadata(BaseModel):
    """Deepgram response metadata."""
    request_id: str
    sha256: Optional[str] = None
    created: str
    duration: float
    channels: int
    models: List[str]
    model_info: dict


class DeepgramAlternative(BaseModel):
    """Deepgram alternative transcription."""
    transcript: str
    words: List[WordData]
    paragraphs: Optional[dict] = None


class DeepgramChannel(BaseModel):
    """Deepgram channel data."""
    alternatives: List[DeepgramAlternative]


class DeepgramResults(BaseModel):
    """Deepgram results structure."""
    channels: List[DeepgramChannel]


class DeepgramResponse(BaseModel):
    """Complete Deepgram API response structure."""
    metadata: DeepgramMetadata
    results: DeepgramResults


class VersionInfo(BaseModel):
    """Version metadata information."""
    version: int
    filename: str
    timestamp: str
    changes: str
    file_size: int


class VersionMetadata(BaseModel):
    """Version management metadata."""
    versions: List[VersionInfo]
    current_version: int
    last_modified: str


class DeepgramVersion(BaseModel):
    """Complete version data including response."""
    version: int
    filename: str
    timestamp: str
    changes: str
    response: DeepgramResponse


class CachedTranscriptionResponse(BaseModel):
    """Extended cached response with raw Deepgram data."""
    audio_file: str
    service: Literal['deepgram'] = 'deepgram'
    config: dict
    timestamp: str
    text: str
    speakers: List[SpeakerSegment]
    confidence: float
    audio_duration: float
    processing_time: float
    raw_response: DeepgramResponse


# API Request/Response Models for Enhanced Editor

class ParagraphUpdateRequest(BaseModel):
    """Request to update paragraph text."""
    paragraph_id: str
    new_text: str


class VersionSaveRequest(BaseModel):
    """Request to save a new version."""
    changes: str
    response: DeepgramResponse


class VersionListResponse(BaseModel):
    """Response with list of available versions."""
    versions: List[VersionInfo]
    current_version: int


class TranscriptLoadResponse(BaseModel):
    """Response when loading a transcript version."""
    version: int
    paragraphs: List[ParagraphData]
    audio_duration: float
    confidence: float


class ValidationError(BaseModel):
    """Validation error details."""
    field: str
    message: str
    value: Optional[str] = None


class ValidationResult(BaseModel):
    """Validation result with errors and warnings."""
    is_valid: bool
    errors: List[ValidationError]
    warnings: List[ValidationError]