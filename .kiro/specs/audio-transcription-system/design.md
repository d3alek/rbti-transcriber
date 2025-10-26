# Design Document

## Overview

The Audio Transcription System is a command-line application that automatically processes directories of MP3 files containing RBTI seminars, generating rich-text transcriptions with speaker identification. The system uses cloud-based transcription services with custom vocabulary support and implements fail-fast error handling with resume capabilities.

## Architecture

The system follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CLI Interface │────│  File Processor  │────│ Transcription   │
│                 │    │                  │    │ Service Client  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌──────────────────┐    ┌─────────────────┐
                       │ Progress Tracker │    │ Custom Glossary │
                       │                  │    │ Manager         │
                       └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ Rich Text        │
                       │ Formatter        │
                       └──────────────────┘
```

### Technology Stack
- **Language**: Python 3.8+
- **Transcription Services**: AssemblyAI and Deepgram (configurable via CLI switch)
- **Rich Text Format**: HTML with embedded CSS for cross-platform compatibility
- **Configuration**: YAML for glossary and settings management
- **CLI Framework**: Click for command-line interface

## Components and Interfaces

### 1. CLI Interface (`cli.py`)
**Purpose**: Entry point for the application, handles command-line arguments and orchestrates the transcription process.

**Interface**:
```python
@click.command()
@click.argument('audio_directory', type=click.Path(exists=True))
@click.option('--service', type=click.Choice(['assemblyai', 'deepgram']), default='assemblyai', help='Transcription service to use')
@click.option('--mode', type=click.Choice(['transcribe', 'format-only']), default='transcribe', help='Transcribe audio or reformat cached responses')
@click.option('--output-format', type=click.Choice(['html', 'markdown', 'both']), default='both', help='Output format for transcriptions')
@click.option('--compress-audio', is_flag=True, help='Compress audio files before upload to reduce upload time')
@click.option('--glossary', type=click.Path(), help='Path to custom glossary file')
@click.option('--api-key', help='Transcription service API key')
def transcribe(audio_directory: str, service: str, mode: str, output_format: str, glossary: str, api_key: str) -> None
```

### 2. File Processor (`file_processor.py`)
**Purpose**: Handles directory scanning, file validation, resume logic, and output management.

**Key Methods**:
- `scan_audio_files(directory: Path) -> List[Path]`
- `get_pending_files(audio_files: List[Path], transcription_dir: Path, mode: str) -> List[Path]`
- `validate_audio_file(file_path: Path) -> bool`
- `get_cached_responses(transcription_dir: Path) -> Dict[str, Path]`
- `create_output_structure(transcription_dir: Path) -> None`

**Output Directory Structure**:
```
transcription/
├── html/           # HTML formatted transcriptions
├── markdown/       # Markdown formatted transcriptions
├── cache/          # Raw service responses (JSON)
└── metadata/       # Processing metadata and logs
```

### 3. Transcription Service Client (`transcription_client.py`)
**Purpose**: Abstract interface for transcription services with concrete implementations for AssemblyAI and Deepgram.

**Abstract Base Class**:
```python
class TranscriptionClient(ABC):
    @abstractmethod
    def upload_audio(self, file_path: Path) -> str
    @abstractmethod
    def submit_transcription_job(self, audio_url: str, config: TranscriptionConfig) -> str
    @abstractmethod
    def poll_transcription_status(self, job_id: str) -> TranscriptionResult
    @abstractmethod
    def apply_custom_vocabulary(self, words: List[str]) -> None
```

**Concrete Implementations**:
- `AssemblyAIClient`: Implements AssemblyAI-specific API calls
- `DeepgramClient`: Implements Deepgram-specific API calls

### 4. Custom Glossary Manager (`glossary_manager.py`)
**Purpose**: Manages RBTI terminology and integrates with transcription service.

**Glossary Management**:
- Loads terms from configurable text files (one term per line)
- Supports multiple glossary files that can be combined
- No built-in default terms - user provides their own vocabulary
- Standardized limit of 1,000 terms for compatibility across all services
- Automatic truncation with warnings if limit exceeded

### 5. Output Formatters (`formatters/`)
**Purpose**: Converts transcription results into multiple output formats.

#### HTML Formatter (`formatters/html_formatter.py`)
**Features**:
- Speaker labels with distinct colors
- Timestamp markers every 30 seconds
- Paragraph breaks for natural speech flow
- Embedded CSS styling for readability

#### Markdown Formatter (`formatters/markdown_formatter.py`)
**Features**:
- Speaker labels as headers (## Speaker A, ## Speaker B)
- Timestamp markers as blockquotes
- Clean text formatting with proper line breaks
- Compatible with standard markdown parsers

#### Raw Response Cache (`cache_manager.py`)
**Purpose**: Manages caching and retrieval of raw service responses.
**Features**:
- JSON storage of complete API responses
- Metadata tracking (service used, timestamp, audio file info)
- Cache validation and integrity checking

#### Audio Processor (`audio_processor.py`)
**Purpose**: Handles audio file optimization before upload.
**Features**:
- FFmpeg integration for audio compression
- Bitrate analysis and optimization (target: 64kbps for speech)
- Quality preservation for speech content
- Compressed file caching to avoid re-processing

### 6. Progress Tracker (`progress_tracker.py`)
**Purpose**: Provides real-time feedback on transcription progress.

**Features**:
- File-by-file progress indication
- Time estimates based on audio duration
- Summary reporting of successes/failures

## Data Models

### TranscriptionConfig
```python
@dataclass
class TranscriptionConfig:
    speaker_labels: bool = True
    custom_vocabulary: List[str] = field(default_factory=list)
    punctuate: bool = True
    format_text: bool = True
    language_code: str = "en"
```

### TranscriptionResult
```python
@dataclass
class TranscriptionResult:
    text: str
    speakers: List[SpeakerSegment]
    confidence: float
    audio_duration: float
    processing_time: float
```

### SpeakerSegment
```python
@dataclass
class SpeakerSegment:
    speaker: str
    start_time: float
    end_time: float
    text: str
    confidence: float
```

## Error Handling

### Fail-Fast Strategy
The system implements fail-fast error handling as specified in requirements:

1. **Audio File Validation**: Invalid MP3 files cause immediate termination
2. **API Connectivity**: Service unavailability terminates processing
3. **Authentication**: Invalid API keys cause immediate failure
4. **File System**: Permission errors terminate processing

### Error Types and Responses
- `AudioValidationError`: Invalid or corrupted MP3 file
- `TranscriptionServiceError`: API service unavailable or rate limited
- `AuthenticationError`: Invalid API credentials
- `FileSystemError`: Directory permissions or disk space issues

## Testing Strategy

### Unit Tests
- File validation logic
- Glossary management functions
- Rich text formatting output
- Progress tracking calculations

### Integration Tests
- End-to-end transcription workflow with sample audio
- API client integration with mock responses
- File system operations with temporary directories

### Test Data
- Sample MP3 files with known RBTI terminology
- Mock API responses for various scenarios
- Test glossaries with specialized vocabulary

## Configuration Management

### Default Configuration (`config.yaml`)
```yaml
transcription:
  default_service: "assemblyai"
  speaker_diarization: true
  max_speakers: 3
  confidence_threshold: 0.8

services:
  assemblyai:
    api_base_url: "https://api.assemblyai.com/v2"
    supports_custom_vocabulary: true
    supports_speaker_diarization: true
  deepgram:
    api_base_url: "https://api.deepgram.com/v1"
    supports_custom_vocabulary: true
    supports_speaker_diarization: true

output:
  formats: ["html", "markdown"]
  timestamp_interval: 30
  speaker_colors: ["#2E86AB", "#A23B72", "#F18F01"]
  cache_responses: true
  
formatting:
  html:
    embed_css: true
    speaker_styling: true
    timestamp_links: true
  markdown:
    speaker_headers: true
    timestamp_blockquotes: true
    preserve_paragraphs: true

glossary:
  files: []  # User-specified glossary files
  max_terms: 1000  # Standardized limit for all services
  warn_on_truncation: true
```

### Environment Variables
- `ASSEMBLYAI_API_KEY`: API key for AssemblyAI service
- `DEEPGRAM_API_KEY`: API key for Deepgram service
- `TRANSCRIPTION_OUTPUT_DIR`: Override default output directory

## Performance Considerations

### Batch Processing
- Process files sequentially to avoid API rate limits
- Implement exponential backoff for API calls
- Cache uploaded audio URLs to avoid re-uploads on resume

### Memory Management
- Stream large audio files rather than loading into memory
- Process transcription results incrementally
- Clean up temporary files after processing

### API Optimization
- Use async APIs from both services for better throughput
- Implement connection pooling for HTTP requests
- **Audio Compression for Faster Uploads**:
  - Convert MP3 files to lower bitrate (e.g., 64kbps) before upload if original exceeds 128kbps
  - Use FFmpeg to compress while preserving speech quality
  - Skip compression if file is already optimally sized
  - Cache compressed versions to avoid re-compression on resume
- Service-specific optimizations:
  - AssemblyAI: Leverage their advanced speaker diarization models
  - Deepgram: Utilize their real-time streaming capabilities for faster processing