# Design Document

## Overview

This design creates a modern React-based web interface for the audio transcription system, centered around the BBC's react-transcript-editor component. The system consists of a React frontend and a FastAPI backend that integrates with the existing transcription infrastructure.

## Architecture

### Frontend Architecture
- **React Application**: Modern React app with TypeScript
- **BBC React Transcript Editor**: Core editing component with audio synchronization
- **Material-UI**: Component library for consistent design
- **WebSocket Client**: Real-time updates for transcription progress
- **Audio Player Integration**: Synchronized playback with transcript editing

### Backend Architecture
- **FastAPI Server**: RESTful API server with WebSocket support
- **Transcription Integration**: Uses existing orchestrator and service factory
- **File Management**: Endpoints for browsing and managing audio files
- **Real-time Updates**: WebSocket connections for progress tracking
- **GitHub Integration**: Service for publishing to GitHub Pages repository

## Components and Interfaces

### React Frontend Components

#### FileManager Component
```typescript
interface FileManagerProps {
  audioDirectory: string;
  onFileSelect: (file: AudioFile) => void;
}

interface AudioFile {
  name: string;
  path: string;
  size: number;
  duration: number;
  hasTranscription: boolean;
  transcriptionStatus: 'none' | 'processing' | 'completed' | 'error';
  lastModified: Date;
}
```

#### TranscriptEditor Component
```typescript
interface TranscriptEditorProps {
  audioFile: AudioFile;
  transcriptionData: TranscriptionData;
  onSave: (data: TranscriptionData) => void;
  onExport: (format: ExportFormat) => void;
  onPublish: (approved: boolean) => void;
}

interface PublicationStatus {
  isPublished: boolean;
  publishedUrl?: string;
  publishedDate?: Date;
  githubCommitHash?: string;
}

interface TranscriptionData {
  text: string;
  speakers: SpeakerSegment[];
  duration: number;
  confidence: number;
}
```

#### TranscriptionTrigger Component
```typescript
interface TranscriptionTriggerProps {
  audioFile: AudioFile;
  onTranscriptionStart: (jobId: string) => void;
  onProgress: (progress: TranscriptionProgress) => void;
}
```

### Backend API Endpoints

#### File Management
```python
GET /api/files
POST /api/files/scan
GET /api/files/{file_id}/info
GET /api/files/{file_id}/transcription
```

#### Transcription Operations
```python
POST /api/transcribe
GET /api/transcribe/{job_id}/status
POST /api/transcribe/{job_id}/cancel
```

#### Export Operations
```python
POST /api/export/{file_id}
GET /api/export/{export_id}/download
```

#### Publication Operations
```python
POST /api/publish/{file_id}
DELETE /api/publish/{file_id}
GET /api/publish/status
GET /api/publish/{file_id}/status
```

#### WebSocket Endpoints
```python
WS /ws/transcription/{job_id}
WS /ws/files
```

## Data Models

### Frontend Data Models
```typescript
interface AudioFile {
  id: string;
  name: string;
  path: string;
  size: number;
  duration: number;
  hasTranscription: boolean;
  transcriptionStatus: TranscriptionStatus;
  lastModified: Date;
  metadata?: AudioMetadata;
  publicationStatus?: PublicationStatus;
}

interface TranscriptionJob {
  id: string;
  audioFile: AudioFile;
  service: 'assemblyai' | 'deepgram';
  status: 'queued' | 'processing' | 'completed' | 'failed';
  progress: number;
  startTime: Date;
  endTime?: Date;
  error?: string;
}

interface SpeakerSegment {
  speaker: string;
  startTime: number;
  endTime: number;
  text: string;
  confidence: number;
}
```

### Backend Data Models
```python
class AudioFileInfo(BaseModel):
    id: str
    name: str
    path: str
    size: int
    duration: float
    has_transcription: bool
    transcription_status: TranscriptionStatus
    last_modified: datetime
    publication_status: Optional[PublicationStatus] = None

class PublicationRequest(BaseModel):
    file_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = []

class PublicationStatus(BaseModel):
    is_published: bool
    published_url: Optional[str] = None
    published_date: Optional[datetime] = None
    github_commit_hash: Optional[str] = None

class TranscriptionRequest(BaseModel):
    file_id: str
    service: Literal['assemblyai', 'deepgram']
    compress_audio: bool = True
    output_formats: List[str] = ['html', 'markdown']

class TranscriptionProgress(BaseModel):
    job_id: str
    status: TranscriptionStatus
    progress: float
    message: str
    error: Optional[str] = None
```

## Integration with Existing System

### Transcription Orchestrator Integration
```python
class WebTranscriptionManager:
    def __init__(self, config_manager: ConfigManager):
        self.orchestrator = TranscriptionOrchestrator(config_manager, ...)
        self.active_jobs: Dict[str, TranscriptionJob] = {}
    
    async def start_transcription(self, request: TranscriptionRequest) -> str:
        # Use existing orchestrator with WebSocket progress updates
        
    async def get_transcription_result(self, file_id: str) -> TranscriptionResult:
        # Load from existing cache system
```

### File System Integration
```python
class AudioFileManager:
    def __init__(self, audio_directory: Path):
        self.scanner = MP3FileScanner(audio_directory)
        self.cache_manager = CacheManager(...)
    
    def list_files(self) -> List[AudioFileInfo]:
        # Use existing file scanner
        
    def get_transcription_status(self, file_path: Path) -> TranscriptionStatus:
        # Check existing cache
```

### GitHub Pages Integration
```python
class GitHubPublisher:
    def __init__(self, repo_url: str, token: str, branch: str = "gh-pages"):
        self.repo_url = repo_url
        self.token = token
        self.branch = branch
        self.git_repo = self._clone_or_pull_repo()
    
    async def publish_transcription(self, file_id: str, html_content: str, metadata: dict) -> PublicationStatus:
        # Commit HTML file to GitHub repository
        # Update index.html with new transcription listing
        # Push changes and trigger GitHub Pages deployment
        
    async def unpublish_transcription(self, file_id: str) -> bool:
        # Remove HTML file from repository
        # Update index.html to remove listing
        # Push changes
        
    def generate_index_page(self, published_files: List[dict]) -> str:
        # Generate index.html with list of all published transcriptions
        # Include search functionality and metadata
```

## User Interface Design

### Main Layout
```
┌─────────────────────────────────────────────────────────┐
│ Header: Audio Transcription Manager                      │
├─────────────────┬───────────────────────────────────────┤
│ File Browser    │ Main Content Area                     │
│                 │                                       │
│ [📁 Files]      │ ┌─────────────────────────────────┐   │
│ [⚙️ Settings]   │ │ Transcript Editor               │   │
│ [📊 Jobs]       │ │                                 │   │
│                 │ │ [Audio Player Controls]         │   │
│                 │ │                                 │   │
│                 │ │ Speaker 1: [Editable text...]  │   │
│                 │ │ Speaker 2: [Editable text...]  │   │
│                 │ │                                 │   │
│                 │ └─────────────────────────────────┘   │
└─────────────────┴───────────────────────────────────────┘
```

### File Browser Interface
- **List View**: Table with file name, duration, size, status, actions
- **Grid View**: Card-based layout with thumbnails and metadata
- **Filters**: By transcription status, file size, date range
- **Search**: Real-time search by filename
- **Bulk Actions**: Select multiple files for batch operations

### Transcript Editor Interface
- **Audio Waveform**: Visual representation with playback position
- **Speaker Labels**: Color-coded speaker identification
- **Text Editing**: Inline editing with auto-save
- **Keyboard Shortcuts**: Standard editing shortcuts (Ctrl+S, Space for play/pause)
- **Export Options**: Dropdown with format selection
- **Publication Controls**: "Approve for Publication" button with metadata form
- **Publication Status**: Indicator showing if transcript is published with link to live site

## Error Handling

### Frontend Error Handling
- **Network Errors**: Retry mechanisms with exponential backoff
- **Transcription Errors**: Clear error messages with retry options
- **File Access Errors**: Graceful degradation with error notifications
- **WebSocket Disconnections**: Automatic reconnection with status updates

### Backend Error Handling
- **File System Errors**: Proper HTTP status codes and error messages
- **Transcription Service Errors**: Error propagation from existing error handlers
- **Resource Limits**: Rate limiting and queue management
- **Validation Errors**: Clear field-level validation messages

## Performance Considerations

### Frontend Optimization
- **Lazy Loading**: Load transcription data only when needed
- **Virtual Scrolling**: Handle large file lists efficiently
- **Audio Streaming**: Progressive audio loading for large files
- **Caching**: Browser caching for static assets and API responses

### Backend Optimization
- **Async Operations**: Non-blocking transcription processing
- **Connection Pooling**: Efficient database and service connections
- **File Streaming**: Stream large audio files without loading into memory
- **Background Jobs**: Queue system for long-running transcription tasks

## GitHub Pages Configuration

### Repository Setup
```yaml
# config.yaml additions
github:
  repository_url: "https://github.com/username/transcriptions-site"
  token: "${GITHUB_TOKEN}"  # Environment variable
  branch: "gh-pages"
  base_url: "https://username.github.io/transcriptions-site"
  
publication:
  auto_generate_index: true
  include_metadata: true
  enable_search: true
  theme: "default"
```

### Generated Site Structure
```
gh-pages/
├── index.html                 # Main listing page with search
├── transcriptions/
│   ├── audio-file-1.html     # Individual transcription pages
│   ├── audio-file-2.html
│   └── ...
├── assets/
│   ├── css/
│   │   └── styles.css        # Styling for published pages
│   └── js/
│       └── search.js         # Client-side search functionality
└── metadata.json             # Machine-readable index for API access
```

### Index Page Features
- **Search Functionality**: Client-side search through transcriptions
- **Filtering**: By date, speaker count, duration, tags
- **Metadata Display**: Title, description, publication date, duration
- **Direct Links**: Links to individual transcription pages
- **RSS Feed**: Optional RSS feed for new publications

## Security Considerations

### Authentication & Authorization
- **File Access Control**: Ensure users can only access authorized directories
- **API Security**: Rate limiting and input validation
- **WebSocket Security**: Secure WebSocket connections with authentication
- **File Upload Security**: Validate file types and sizes
- **GitHub Token Security**: Secure storage of GitHub personal access tokens

### Data Protection
- **Sensitive Data**: Secure handling of audio content and transcriptions
- **API Keys**: Secure storage and transmission of service API keys
- **Audit Logging**: Track user actions and system events
- **CORS Configuration**: Proper cross-origin resource sharing setup
- **Publication Approval**: Ensure only authorized users can publish content