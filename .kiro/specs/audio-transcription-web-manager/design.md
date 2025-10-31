# Design Document

## Overview

The Audio Transcription Web Manager is a comprehensive web application that extends the existing deepgram-demo.html proof of concept into a full-featured transcription management system. The system provides directory-based file management, transcription job orchestration with manual status checking, interactive transcript editing using the react-transcript-editor component, and local static site generation for bundled publishing.

## Architecture

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                        │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   File Manager  │ Transcript      │    Static Site Publisher    │
│   Component     │ Editor          │    Component                │
│                 │ Component       │                             │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   HTTP API        │
                    │   Requests        │
                    └─────────┬─────────┘
                              │
┌─────────────────────────────┴─────────────────────────────────────┐
│                    Backend API (FastAPI)                         │
├─────────────────┬─────────────────┬─────────────────────────────┤
│   File System   │ Transcription   │    Static Site              │
│   Scanner        │ Service         │    Generator                │
└─────────────────┴─────────────────┴─────────────────────────────┘
                              │
┌─────────────────────────────┴─────────────────────────────────────┐
│                      External Services                           │
├─────────────────┬─────────────────────────────────────────────────┤
│   Deepgram API  │ File System (Local Audio & Static Sites)       │
└─────────────────┴─────────────────────────────────────────────────┘
```

### Component Architecture

```
Frontend Components:
├── App.tsx (Main Router)
├── FileManager/
│   ├── DirectorySelector.tsx
│   ├── AudioFileList.tsx
│   ├── TranscriptionStatus.tsx
│   └── SeminarGroupView.tsx
├── TranscriptEditor/
│   ├── TranscriptEditorWrapper.tsx
│   ├── DeepgramTransformer.ts
│   ├── ManualEditManager.tsx
│   └── AudioPlayerIntegration.tsx
├── Publisher/
│   ├── LocalSitePublisher.tsx
│   ├── PublishingStatus.tsx
│   └── StaticSiteGenerator.tsx
└── Shared/
    ├── APIClient.ts
    └── StatusIndicators.tsx
```

## Components and Interfaces

### Frontend Components

#### FileManager Component
```typescript
interface FileManagerProps {
  onFileSelect: (audioFile: AudioFileInfo) => void;
  onTranscriptionStart: (audioFile: AudioFileInfo) => void;
  onPublish: (audioFile: AudioFileInfo) => void;
}

interface AudioFileInfo {
  path: string;
  filename: string;
  size: number;
  duration?: number;
  transcriptionStatus: 'none' | 'completed' | 'failed';
  seminarGroup: string;
  hasCompressedVersion: boolean;
  compressedSize?: number;
  lastTranscriptionAttempt?: string;
  transcriptionError?: string;
}

interface DirectoryScanResult {
  audioFiles: AudioFileInfo[];
  seminarGroups: string[];
  totalFiles: number;
  transcribedFiles: number;
}
```

#### TranscriptEditor Component
```typescript
interface TranscriptEditorWrapperProps {
  audioFile: AudioFileInfo;
  onSave: (correctedTranscript: CorrectedDeepgramResponse) => void;
  onPublish: () => void;
  onBack: () => void;
}

interface CorrectedDeepgramResponse extends DeepgramResponse {
  corrections?: {
    version: number;
    timestamp: string;
    speaker_names?: {
      [speakerIndex: number]: string; // Maps "0" -> "Dr. Smith", "1" -> "Student A", etc.
    };
  };
  // Deep modification of results.channels[0].alternatives[0].words
  // Each word can have: corrected: boolean, original_word?: string
}

interface DeepgramTransformer {
  transformToReactTranscriptEditor(response: CorrectedDeepgramResponse): ReactTranscriptEditorData;
  mergeCorrectionsIntoDeepgramResponse(original: CorrectedDeepgramResponse, edited: ReactTranscriptEditorData): CorrectedDeepgramResponse;
}
```

#### Local Site Publisher Component
```typescript
interface LocalSitePublisherProps {
  audioFile: AudioFileInfo;
  transcriptData: CorrectedDeepgramResponse;
  onPublishComplete: (localPath: string) => void;
  onPublishError: (error: string) => void;
}

interface PublishBundle {
  htmlFile: string;
  audioFile: string;
  transcriptData: CorrectedDeepgramResponse;
  seminarGroup: string;
  metadata: {
    title: string;
    duration: number;
    publishDate: string;
    fileSize: number;
    compressedSize: number;
    speakerNames?: {[speakerIndex: number]: string};
  };
}

interface LocalPagesStructure {
  'index.html': string; // Main landing page
  'groups/': {
    [groupName: string]: {
      'index.html': string; // Group listing page
      'transcripts/': {
        [audioFileName: string]: {
          'index.html': string; // Individual transcript page
          'audio.mp3': Buffer; // Compressed audio
          'transcript.json': CorrectedDeepgramResponse;
        };
      };
    };
  };
}
```

### Backend Services

#### FileSystemScanner
```typescript
class FileSystemScanner {
  scanDirectory(directoryPath: string): Promise<DirectoryScanResult>;
  checkTranscriptionStatus(audioFile: string): Promise<TranscriptionStatus>;
  getAudioMetadata(audioFile: string): Promise<AudioMetadata>;
  findCompressedVersion(audioFile: string): Promise<string | null>;
}

interface TranscriptionStatus {
  exists: boolean;
  status: 'completed' | 'failed';
  error?: string;
  cacheFile?: string;
  compressedAudio?: string;
  lastAttempt?: string;
  processingTime?: number;
}
```

#### TranscriptionService
```typescript
class TranscriptionService {
  transcribeAudio(audioFile: string): Promise<TranscriptionResult>;
  getTranscriptionStatus(audioFile: string): Promise<TranscriptionStatus>;
  retryTranscription(audioFile: string): Promise<TranscriptionResult>;
}

interface TranscriptionResult {
  success: boolean;
  audioFile: string;
  result?: DeepgramResponse;
  error?: string;
  processingTime?: number;
  cacheFile?: string;
  compressedAudio?: string;
}
```

#### LocalSitePublisher
```typescript
class LocalSitePublisher {
  publishTranscript(bundle: PublishBundle): Promise<PublishResult>;
  updateSiteIndex(seminarGroups: string[]): Promise<void>;
  updateGroupIndex(groupName: string, transcripts: TranscriptMetadata[]): Promise<void>;
  generateStaticPages(bundle: PublishBundle): Promise<StaticPageSet>;
  writeToLocalDirectory(structure: LocalPagesStructure, outputPath: string): Promise<void>;
}

interface PublishResult {
  success: boolean;
  localPath: string;
  error?: string;
}

interface StaticPageSet {
  transcriptPage: string;
  groupPage: string;
  mainIndex: string;
}
```

## Data Models

### Core Data Structures

```typescript
interface ReactTranscriptEditorData {
  words: Array<{
    start: number;
    end: number;
    word: string;
    confidence: number;
    punct: string;
    index: number;
    speaker: number;
    corrected?: boolean;
    original_word?: string;
    original_punct?: string;
  }>;
  speakers: Array<{
    speaker: string;
    start_time: number;
    end_time: number;
    text: string;
    confidence: number;
  }>;
  speaker_names?: {
    [speakerIndex: number]: string; // Maps 0 -> "Dr. Smith", 1 -> "Student A", etc.
  };
  transcript: string;
  metadata: {
    duration: number;
    confidence: number;
    service: string;
  };
}

// ManualEdit interface removed - corrections are embedded directly in the data structures

interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}
```

### File System Structure

```
audio_files/
├── seminar_group_1/
│   ├── audio1.mp3
│   ├── audio2.mp3
│   ├── transcriptions/
│   │   ├── audio1.json (CorrectedDeepgramResponse - starts as original, gets corrections added)
│   │   └── audio2.json
│   └── compressed/
│       ├── audio1.mp3
│       └── audio2.mp3
└── seminar_group_2/
    └── ...
```

### Local gh-pages Directory Structure

```
gh-pages/
├── index.html (Main seminar groups listing)
├── assets/
│   ├── styles.css
│   └── scripts.js
└── groups/
    ├── seminar_group_1/
    │   ├── index.html (Group transcript listing)
    │   └── transcripts/
    │       ├── audio1/
    │       │   ├── index.html (Transcript page)
    │       │   ├── audio.mp3 (Compressed)
    │       │   └── transcript.json (Edited)
    │       └── audio2/
    │           └── ...
    └── seminar_group_2/
        └── ...
```

## Error Handling

### Error Categories and Strategies

1. **File System Errors**
   - Directory access permissions
   - Missing audio files
   - Corrupted transcription cache files
   - Disk space limitations

2. **Transcription Service Errors**
   - Deepgram API failures
   - Network connectivity issues
   - Audio format incompatibilities
   - Service timeout handling

3. **Local Site Publishing Errors**
   - File system write permissions
   - Disk space limitations
   - Template generation failures
   - Asset copying errors

4. **API Communication Errors**
   - HTTP request failures
   - Response parsing errors
   - Network timeout issues

### Error Recovery Mechanisms

```typescript
interface ErrorHandler {
  handleFileSystemError(error: FileSystemError): Promise<void>;
  handleTranscriptionError(audioFile: string, error: TranscriptionError): Promise<void>;
  handleLocalSiteError(bundle: PublishBundle, error: LocalSiteError): Promise<void>;
  handleAPIError(error: APIError): Promise<void>;
}

interface RetryStrategy {
  maxRetries: number;
  backoffMultiplier: number;
  retryableErrors: string[];
  onRetryExhausted: (error: Error) => void;
}
```

## Testing Strategy

### Unit Testing
- **FileSystemScanner**: Test directory scanning, file detection, status checking
- **DeepgramTransformer**: Test data transformation between formats
- **TranscriptionService**: Test transcription processing and error handling
- **LocalSitePublisher**: Test local static site generation and file writing

### Integration Testing
- **API Communication**: Test HTTP request/response handling
- **Transcript Editor Integration**: Test react-transcript-editor component integration
- **End-to-End Publishing**: Test complete publish workflow from transcript to local gh-pages directory

### End-to-End Testing
- **Complete Workflow**: Directory scan → Transcription → Editing → Local Publishing
- **Multi-file Processing**: Test batch transcription and local site generation
- **Error Recovery**: Test system behavior under various failure conditions

## Security Considerations

### Data Protection
- Validate all file paths to prevent directory traversal attacks
- Sanitize user input in transcript edits
- Secure local file system access
- Implement rate limiting for API endpoints

### Access Control
- Validate directory access permissions
- Secure local file writing operations
- Secure HTTP API endpoints
- Protect sensitive configuration data

## Performance Optimizations

### Frontend Optimizations
- Implement virtual scrolling for large file lists
- Use React.memo for expensive components
- Lazy load transcript editor components
- Cache transformed transcript data

### Backend Optimizations
- Implement job queuing for transcription requests
- Use connection pooling for database operations
- Cache file system scan results
- Optimize file system operations with batch writes

### API Communication
- Implement efficient HTTP request batching
- Use compression for large data transfers
- Add request timeout and retry mechanisms
- Cache API responses where appropriate

## Implementation Phases

### Phase 1: Core Infrastructure
- Set up React application structure
- Implement file system scanning backend
- Create HTTP API communication
- Build directory selection interface

### Phase 2: Transcription Management
- Integrate transcription service
- Implement manual status checking and refresh functionality
- Add transcription triggering for missing files
- Create transcription status UI components

### Phase 3: Transcript Editor Integration
- Integrate react-transcript-editor component
- Implement Deepgram data transformation
- Add manual edit management
- Create save/load functionality for edits

### Phase 4: Local Static Site Publishing
- Implement local gh-pages directory publishing
- Create static site generation for local folders
- Build publishing UI components
- Add local directory status tracking

### Phase 5: Polish and Optimization
- Add comprehensive error handling
- Implement performance optimizations
- Add advanced features (batch operations, etc.)
- Create comprehensive documentation

## Technology Stack Integration

### Frontend Stack
- **React 19**: Main UI framework with hooks and context
- **TypeScript**: Type safety for complex data structures
- **Material-UI**: Consistent component library
- **React-transcript-editor**: Specialized transcript editing component

### Backend Stack
- **FastAPI**: Async API framework for HTTP operations
- **File System Operations**: Local file management and static site generation
- **FFmpeg**: Audio compression for web delivery

### External Integrations
- **Deepgram API**: Transcription service integration
- **File System**: Local audio file and static site management
- **HTTP Protocol**: Standard API communication