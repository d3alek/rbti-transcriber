# Requirements Document

## Introduction

Create a React-based web interface for managing and editing audio transcriptions, built around the BBC's react-transcript-editor component. The interface will provide file management, transcription triggering, and editing capabilities.

## Glossary

- **React Transcript Editor**: BBC's open-source React component for editing transcriptions with audio playback synchronization
- **File Browser**: Component for listing and managing MP3 files in a directory
- **Transcription Manager**: Backend service for triggering and managing transcription jobs
- **WebSocket Connection**: Real-time communication channel for transcription progress updates
- **Audio Player**: Synchronized audio playback component integrated with transcript editing
- **Export Manager**: Component for exporting edited transcriptions in various formats
- **GitHub Publisher**: Service for publishing approved transcriptions to GitHub Pages
- **Publication Status**: Tracking system for published vs unpublished transcriptions

## Requirements

### Requirement 1

**User Story:** As a user, I want to browse MP3 files in a directory through a web interface, so that I can see which files have transcriptions and which need to be transcribed.

#### Acceptance Criteria

1. THE web interface SHALL display a list of all MP3 files in the configured audio directory
2. WHEN a file has an existing transcription, THE interface SHALL show a "Edit" button
3. WHEN a file has no transcription, THE interface SHALL show a "Transcribe" button
4. THE interface SHALL display file metadata including duration, size, and modification date
5. THE interface SHALL support filtering and sorting of files by various criteria

### Requirement 2

**User Story:** As a user, I want to trigger transcription jobs from the web interface, so that I can process audio files without using the command line.

#### Acceptance Criteria

1. WHEN I click "Transcribe" on a file, THE system SHALL start a transcription job using the configured service
2. THE interface SHALL show real-time progress updates during transcription
3. THE system SHALL allow selection of transcription service (AssemblyAI or Deepgram)
4. WHEN transcription completes, THE interface SHALL automatically refresh to show the "Edit" button
5. THE system SHALL handle transcription errors gracefully with clear error messages

### Requirement 3

**User Story:** As a user, I want to edit transcriptions using a professional transcript editor, so that I can correct errors and improve accuracy.

#### Acceptance Criteria

1. THE interface SHALL integrate the BBC react-transcript-editor component
2. WHEN editing a transcription, THE system SHALL provide synchronized audio playback
3. THE editor SHALL support speaker diarization with visual speaker labels
4. THE system SHALL allow real-time editing of transcript text with automatic saving
5. THE editor SHALL support keyboard shortcuts for efficient editing workflow

### Requirement 4

**User Story:** As a user, I want to export edited transcriptions in multiple formats, so that I can use them in different contexts.

#### Acceptance Criteria

1. THE system SHALL support exporting transcriptions in HTML, Markdown, and plain text formats
2. THE export SHALL preserve speaker labels and timing information
3. THE system SHALL allow downloading exported files directly from the web interface
4. THE export SHALL maintain the same formatting quality as the CLI tool
5. THE system SHALL support batch export of multiple transcriptions

### Requirement 5

**User Story:** As a user, I want to publish approved transcriptions to a GitHub Pages website, so that they are publicly accessible and searchable.

#### Acceptance Criteria

1. THE system SHALL provide an "Approve for Publication" button for edited transcriptions
2. WHEN a transcription is approved, THE system SHALL commit the HTML file to a GitHub repository
3. THE system SHALL automatically trigger GitHub Pages deployment after publishing
4. THE published website SHALL include an index page listing all approved transcriptions
5. THE system SHALL support unpublishing transcriptions by removing them from the repository

### Requirement 6

**User Story:** As a developer, I want the web interface to integrate seamlessly with the existing transcription system, so that it uses the same backend services and configuration.

#### Acceptance Criteria

1. THE web interface SHALL use the existing transcription orchestrator and service factory
2. THE system SHALL read configuration from the same config.yaml file
3. THE web interface SHALL support the same glossary and compression settings
4. THE backend API SHALL provide RESTful endpoints for all transcription operations
5. THE system SHALL maintain the same caching and resume capabilities as the CLI tool