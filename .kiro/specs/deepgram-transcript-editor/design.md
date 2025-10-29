# Design Document

## Overview

The enhanced transcript editor provides a sophisticated editing interface that works directly with raw Deepgram API responses. The system displays transcripts in paragraph format with real-time audio synchronization, word-level highlighting, and file-based version management. The design leverages the rich structure of Deepgram responses to provide professional-grade editing capabilities without data loss from format conversions.

## Architecture

### High-Level Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React UI      │    │   API Backend    │    │  File System    │
│                 │    │                  │    │                 │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │ ┌─────────────┐ │
│ │ Transcript  │ │◄──►│ │ Version      │ │◄──►│ │ Deepgram    │ │
│ │ Editor      │ │    │ │ Manager      │ │    │ │ Response    │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ │ Files       │ │
│                 │    │                  │    │ └─────────────┘ │
│ ┌─────────────┐ │    │ ┌──────────────┐ │    │                 │
│ │ Audio       │ │◄──►│ │ Audio        │ │    │ ┌─────────────┐ │
│ │ Player      │ │    │ │ Service      │ │    │ │ Audio       │ │
│ └─────────────┘ │    │ └──────────────┘ │    │ │ Files       │ │
│                 │    │                  │    │ └─────────────┘ │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

### Data Flow Architecture

```
Raw Deepgram Response → Version Manager → UI State → React Components
                                ↓
                        File System Storage ← Version Files
```

## Components and Interfaces

### Frontend Components

#### TranscriptEditor Component
```typescript
interface TranscriptEditorProps {
  audioFile: string;
  transcriptVersions: DeepgramVersion[];
  currentVersion: number;
  onVersionChange: (version: number) => void;
  onSaveVersion: () => void;
}

interface TranscriptEditorState {
  currentPlaybackTime: number;
  activeWordIndex: number;
  editingParagraph: number | null;
  paragraphs: ParagraphData[];
}
```

#### ParagraphEditor Component
```typescript
interface ParagraphEditorProps {
  paragraph: ParagraphData;
  isEditing: boolean;
  currentPlaybackTime: number;
  onEdit: (paragraphId: string, newText: string) => void;
  onStartEdit: (paragraphId: string) => void;
  onEndEdit: () => void;
}
```

#### AudioPlayer Component
```typescript
interface AudioPlayerProps {
  audioFile: string;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onSeek: (time: number) => void;
}
```

#### VersionManager Component
```typescript
interface VersionManagerProps {
  versions: DeepgramVersion[];
  currentVersion: number;
  onVersionSelect: (version: number) => void;
  onSaveVersion: () => void;
  canSave: boolean;
}
```

### Backend Services

#### DeepgramVersionManager
```typescript
class DeepgramVersionManager {
  loadVersions(audioFile: string): Promise<DeepgramVersion[]>;
  saveVersion(audioFile: string, response: DeepgramResponse): Promise<string>;
  getVersion(audioFile: string, version: number): Promise<DeepgramResponse>;
  deleteVersion(audioFile: string, version: number): Promise<void>;
}
```

#### TranscriptProcessor
```typescript
class TranscriptProcessor {
  extractParagraphs(response: DeepgramResponse): ParagraphData[];
  updateParagraphText(response: DeepgramResponse, paragraphId: string, newText: string): DeepgramResponse;
  findWordAtTime(response: DeepgramResponse, time: number): WordData | null;
  calculateTimingAdjustments(originalText: string, newText: string, words: WordData[]): WordData[];
}
```

## Data Models

### Core Data Structures

```typescript
interface DeepgramVersion {
  version: number;
  filename: string;
  timestamp: string;
  changes: string;
  response: DeepgramResponse;
}

interface ParagraphData {
  id: string;
  text: string;
  startTime: number;
  endTime: number;
  speaker: number;
  sentences: SentenceData[];
  words: WordData[];
  confidence: number;
}

interface SentenceData {
  id: string;
  text: string;
  startTime: number;
  endTime: number;
  speaker: number;
  words: WordData[];
}

interface WordData {
  word: string;
  punctuatedWord: string;
  start: number;
  end: number;
  confidence: number;
  speaker: number;
  speakerConfidence: number;
  index: number;
}

interface DeepgramResponse {
  // Raw Deepgram API response structure
  metadata: {
    request_id: string;
    created: string;
    duration: number;
    channels: number;
    models: string[];
    model_info: Record<string, ModelInfo>;
  };
  results: {
    channels: Array<{
      alternatives: Array<{
        transcript: string;
        words: WordData[];
        paragraphs: {
          transcript: string;
          paragraphs: Array<{
            sentences: SentenceData[];
          }>;
        };
      }>;
    }>;
  };
}
```

### File System Structure

```
transcriptions/
├── cache/
│   └── original_deepgram_responses/
│       └── {audio_hash}.json
├── versions/
│   └── {audio_hash}/
│       ├── v0.json (original)
│       ├── v1.json
│       ├── v2.json
│       └── metadata.json
└── audio/
    └── {audio_files}
```

## Error Handling

### Error Categories

1. **File System Errors**
   - Version file corruption
   - Disk space issues
   - Permission problems

2. **Data Integrity Errors**
   - Invalid Deepgram response structure
   - Timing data inconsistencies
   - Word-paragraph mapping failures

3. **UI State Errors**
   - Audio synchronization failures
   - Version switching conflicts
   - Edit state corruption

### Error Recovery Strategies

```typescript
interface ErrorHandler {
  handleVersionLoadError(error: Error, fallbackVersion?: number): void;
  handleAudioSyncError(error: Error): void;
  handleEditConflict(error: Error): void;
  validateDeepgramResponse(response: any): DeepgramResponse | null;
}
```

## Testing Strategy

### Unit Testing
- **TranscriptProcessor**: Test paragraph extraction, text updates, timing calculations
- **DeepgramVersionManager**: Test version CRUD operations, file management
- **WordHighlighter**: Test timing synchronization, word finding algorithms

### Integration Testing
- **Audio-Text Synchronization**: Test real-time highlighting accuracy
- **Version Management**: Test version creation, switching, and data integrity
- **Edit Operations**: Test paragraph editing with timing preservation

### End-to-End Testing
- **Complete Editing Workflow**: Load transcript → Edit paragraphs → Save version → Switch versions
- **Audio Playback Integration**: Test highlighting during playback across different versions
- **Error Recovery**: Test handling of corrupted files, network issues, and data inconsistencies

### Performance Testing
- **Large Transcript Handling**: Test with 3+ hour audio files (164k+ lines of JSON)
- **Version Switching Speed**: Measure time to switch between versions
- **Real-time Highlighting**: Test highlighting performance during audio playback
- **Memory Usage**: Monitor memory consumption with multiple versions loaded

## Implementation Phases

### Phase 1: Core Data Layer
- Implement DeepgramVersionManager for file operations
- Create TranscriptProcessor for paragraph extraction
- Set up basic data models and validation

### Phase 2: UI Foundation
- Build TranscriptEditor component with paragraph display
- Implement basic editing capabilities
- Create VersionManager UI component

### Phase 3: Audio Integration
- Implement AudioPlayer component
- Add real-time word highlighting
- Synchronize audio playback with text display

### Phase 4: Advanced Features
- Add confidence-based visual indicators
- Implement speaker management
- Add keyboard shortcuts and accessibility features

### Phase 5: Polish and Optimization
- Optimize performance for large transcripts
- Add comprehensive error handling
- Implement advanced editing features (find/replace, etc.)

## Security Considerations

### Data Protection
- Validate all Deepgram response data before processing
- Sanitize user input during paragraph editing
- Implement file system access controls

### Version Integrity
- Use checksums to verify version file integrity
- Implement atomic file operations for version saves
- Prevent concurrent edit conflicts

## Performance Optimizations

### Large Transcript Handling
- Implement virtual scrolling for long transcripts
- Use React.memo for paragraph components
- Lazy load version data on demand

### Audio Synchronization
- Use Web Workers for timing calculations
- Implement efficient word lookup algorithms
- Cache frequently accessed timing data

### Memory Management
- Unload unused version data
- Implement garbage collection for large objects
- Use efficient data structures for word indexing