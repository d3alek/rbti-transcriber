"""Pydantic models for the API."""

from pydantic import BaseModel
from typing import Optional, List, Literal, Dict
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


class TranscriptionResult(BaseModel):
    """Result of transcription operation."""
    success: bool
    audio_file: str
    result: Optional[TranscriptionData] = None
    error: Optional[str] = None
    processing_time: float
    cache_file: Optional[str] = None
    compressed_audio: Optional[str] = None


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


# Directory Scanning Models for FileSystemScanner

class DirectoryScanRequest(BaseModel):
    """Request to scan a directory for audio files."""
    directory_path: str


class SeminarGroupInfo(BaseModel):
    """Information about a seminar group."""
    name: str
    file_count: int
    transcribed_count: int
    total_size: int
    total_duration: float


class AudioFileDetail(BaseModel):
    """Detailed audio file information from directory scan."""
    path: str
    filename: str
    size: int
    duration: float
    file_id: str
    last_modified: str
    seminar_group: str
    transcription_status: str
    transcription_files: List[str]
    cache_files: List[str]
    last_transcription_attempt: Optional[str] = None
    transcription_error: Optional[str] = None
    has_compressed_version: bool
    compressed_size: Optional[int] = None
    compressed_path: Optional[str] = None
    compression_ratio: Optional[float] = None


class DirectoryScanResult(BaseModel):
    """Result of directory scanning operation."""
    directory: str
    total_files: int
    transcribed_files: int
    audio_files: List[AudioFileDetail]
    seminar_groups: List[str]
    groups_detail: Dict[str, List[AudioFileDetail]]
    scan_timestamp: str


class AudioMetadataResponse(BaseModel):
    """Response containing audio file metadata."""
    path: str
    filename: str
    size: int
    duration: float
    last_modified: str
    format_info: Optional[dict] = None


class TranscriptionStatusDetail(BaseModel):
    """Detailed transcription status information."""
    transcription_status: str
    transcription_files: List[str]
    cache_files: List[str]
    last_transcription_attempt: Optional[str] = None
    transcription_error: Optional[str] = None


# File System Validation Models (for optional task 2.3)

class DirectoryPermissions(BaseModel):
    """Directory permission check results."""
    path: str
    exists: bool
    is_directory: bool
    readable: bool
    writable: bool
    executable: bool
    errors: List[str]


class AudioFormatValidation(BaseModel):
    """Audio format validation results."""
    path: str
    is_valid: bool
    format: Optional[str] = None
    errors: List[str]


class TranscriptionFileIntegrity(BaseModel):
    """Transcription file integrity check results."""
    path: str
    is_valid: bool
    errors: List[str]