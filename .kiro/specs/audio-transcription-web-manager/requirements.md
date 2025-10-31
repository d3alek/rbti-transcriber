# Requirements Document

## Introduction

This specification defines a comprehensive web-based audio transcription management system that extends the existing deepgram-demo.html proof of concept into a full-featured application. The system provides directory-based audio file management, transcription job orchestration, interactive transcript editing with the react-transcript-editor component, and GitHub Pages publishing for static site generation.

## Glossary

- **Audio Directory**: A local filesystem directory containing MP3 audio files for transcription processing
- **Transcription Job**: An asynchronous process that converts audio files to text using Deepgram API
- **Compressed Audio**: Audio files processed through FFmpeg compression to reduce file size for web delivery
- **Transcript Editor**: Interactive editing interface based on react-transcript-editor component for word-level transcript editing
- **Manual Edits**: User modifications to transcript text that extend the original Deepgram response structure
- **Local Publishing**: Process of generating transcript bundles (HTML, audio, JSON) to a local gh-pages directory for static site hosting
- **Seminar Group**: Logical organization of audio files based on their source directory name

## Requirements

### Requirement 1

**User Story:** As a transcription manager, I want to load and browse audio directories so that I can see all available audio files and their transcription status in one interface.

#### Acceptance Criteria

1. THE System SHALL provide a directory selection interface for choosing local audio file directories
2. THE System SHALL scan selected directories for MP3 audio files and display them in a file list
3. THE System SHALL check for existing transcription files and mark audio files with transcription status indicators
4. THE System SHALL display file metadata including file size, duration, and transcription completion status
5. THE System SHALL organize files by their source directory as logical seminar groups

### Requirement 2

**User Story:** As a transcription manager, I want to start transcription jobs for audio files without transcriptions so that I can process multiple files and check their completion status by refreshing the interface.

#### Acceptance Criteria

1. THE System SHALL provide "Start Transcription" buttons for audio files without existing transcriptions
2. WHEN a transcription job is started, THE System SHALL display job status as "processing", "completed", or "failed"
3. THE System SHALL allow manual refresh of the file list to check transcription job completion status
4. THE System SHALL update file status indicators when the interface is refreshed after transcription jobs complete
5. THE System SHALL display error messages and retry options for failed transcription jobs

### Requirement 3

**User Story:** As a transcript editor, I want to open audio files with transcriptions in the react-transcript-editor interface so that I can edit transcripts with word-level precision and audio synchronization.

#### Acceptance Criteria

1. WHEN clicking on an audio file with transcription, THE System SHALL navigate to the transcript editor view
2. THE System SHALL load the raw Deepgram response and transform it to react-transcript-editor format
3. THE System SHALL display the compressed audio file for playback with file size information visible in the UI
4. THE System SHALL enable real-time word highlighting during audio playback matching the reference implementation
5. THE System SHALL provide all playback controls available in the react-transcript-editor demo including play/pause, seek, and speed control

### Requirement 4

**User Story:** As a transcript editor, I want to edit transcript text and save changes so that I can correct transcription errors while preserving the original Deepgram data structure.

#### Acceptance Criteria

1. THE System SHALL enable transcript editing by default when opening the transcript editor
2. THE System SHALL provide a "Save Edits" button to persist transcript modifications
3. WHEN saving edits, THE System SHALL extend the Deepgram JSON structure to include corrections without replacing original data
4. THE System SHALL prioritize corrected words over original Deepgram text when rendering transcripts
5. THE System SHALL provide visual indicators for manually corrected words with hover tooltips showing original Deepgram text

### Requirement 9

**User Story:** As a transcript editor, I want to customize speaker names so that I can replace generic "Speaker 0" labels with meaningful names like "Dr. Smith" or "Student A".

#### Acceptance Criteria

1. THE System SHALL provide an interface for editing speaker names in the transcript editor
2. THE System SHALL store custom speaker name mappings in the corrected Deepgram response structure
3. THE System SHALL display custom speaker names throughout the transcript interface when available
4. THE System SHALL preserve speaker name mappings when saving and loading corrected transcripts
5. THE System SHALL use custom speaker names in published static sites and exported content

### Requirement 5

**User Story:** As a transcript editor, I want to publish transcripts to a local static site folder so that I can create bundled websites for sharing transcribed seminars with others.

#### Acceptance Criteria

1. THE System SHALL provide "Publish to Local Site" buttons in both the file list and transcript editor views
2. WHEN publishing, THE System SHALL create a bundle containing HTML file, compressed audio file, and modified Deepgram response
3. THE System SHALL use the original audio file's directory name as the seminar group identifier for organization
4. THE System SHALL generate bundles in a local gh-pages directory structure that enables browsing by seminar groups
5. THE System SHALL generate static HTML pages that allow site visitors to browse different seminar groups and audio files within them

### Requirement 6

**User Story:** As a site visitor, I want to browse published transcripts in the local static site so that I can access different seminar groups and their audio files through a web interface.

#### Acceptance Criteria

1. THE System SHALL generate a main index page listing all available seminar groups in the local gh-pages directory
2. THE System SHALL create group-specific pages showing all audio files within each seminar group
3. THE System SHALL provide direct links to individual transcript pages with embedded audio players
4. THE System SHALL ensure all published content is accessible through standard web browsers without additional software
5. THE System SHALL maintain consistent navigation between group listings and individual transcript pages

### Requirement 7

**User Story:** As a transcription manager, I want to refresh the interface to check transcription job status so that I can monitor job completion without complex real-time connections.

#### Acceptance Criteria

1. THE System SHALL provide a manual refresh button or automatic page refresh capability
2. THE System SHALL display current status indicators for all transcription jobs when the interface is refreshed
3. THE System SHALL update file status indicators to reflect completed, failed, or processing states
4. THE System SHALL show processing time and completion status for finished jobs
5. THE System SHALL provide clear visual feedback when refresh operations are in progress

### Requirement 8

**User Story:** As a transcript editor, I want to see file size information for compressed audio so that I can verify compression effectiveness and manage bandwidth usage.

#### Acceptance Criteria

1. THE System SHALL display compressed audio file sizes in the transcript editor interface
2. THE System SHALL show original and compressed file sizes for comparison when available
3. THE System SHALL indicate compression ratios or savings percentages where applicable
4. THE System SHALL use compressed audio files for all playback operations in the transcript editor
5. THE System SHALL provide visual confirmation that compressed audio is being used for web delivery