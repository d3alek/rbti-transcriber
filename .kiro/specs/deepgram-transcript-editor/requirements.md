# Requirements Document

## Introduction

This specification defines an enhanced transcript editor that works directly with raw Deepgram API responses, providing paragraph-based editing with real-time audio synchronization and Git-based version management. The system eliminates intermediary formats and leverages the rich structure of Deepgram responses for a professional editing experience.

## Glossary

- **Deepgram Response**: The raw JSON response from Deepgram API containing word-level timing, speaker data, and paragraph structure
- **Paragraph View**: UI display mode showing transcript organized by paragraphs rather than individual speaker utterances
- **Word Highlighting**: Real-time visual indication of the currently spoken word during audio playback
- **Version Management**: Git-based tracking of transcript edits with ability to switch between versions
- **Audio Synchronization**: Precise alignment between audio playback position and displayed text

## Requirements

### Requirement 1

**User Story:** As a transcript editor, I want to work directly with raw Deepgram responses so that I have access to all available timing and confidence data without data loss from format conversions.

#### Acceptance Criteria

1. THE System SHALL load raw Deepgram JSON responses as the primary data source
2. THE System SHALL preserve all original Deepgram metadata including word-level timing, confidence scores, and speaker information
3. THE System SHALL NOT create intermediary format conversions that could lose data fidelity
4. THE System SHALL maintain the complete Deepgram response structure in memory during editing sessions
5. THE System SHALL access word-level timing data directly from the raw response for audio synchronization

### Requirement 2

**User Story:** As a transcript editor, I want to view and edit the transcript in paragraph format so that I can work with natural text blocks rather than fragmented speaker utterances.

#### Acceptance Criteria

1. THE System SHALL display transcript content organized by paragraphs from the Deepgram response
2. THE System SHALL extract paragraph structure from the raw Deepgram response paragraphs field
3. THE System SHALL render each paragraph as an editable text block in the UI
4. THE System SHALL maintain speaker identification within paragraph context
5. THE System SHALL preserve sentence boundaries within paragraphs for navigation purposes

### Requirement 3

**User Story:** As a transcript editor, I want real-time word highlighting during audio playback so that I can follow along and identify specific sections that need editing.

#### Acceptance Criteria

1. WHEN audio is playing, THE System SHALL highlight the currently spoken word in the displayed paragraph
2. THE System SHALL use word-level start and end times from the Deepgram response for precise synchronization
3. THE System SHALL update word highlighting in real-time as audio playback progresses
4. THE System SHALL maintain highlighting accuracy within 100 milliseconds of actual audio position
5. THE System SHALL provide visual distinction between the current word and surrounding text

### Requirement 4

**User Story:** As a transcript editor, I want to edit paragraph text and save new versions on demand so that I can make multiple edits before creating a checkpoint and track my editing history.

#### Acceptance Criteria

1. THE System SHALL allow in-place editing of paragraph text without automatically creating versions
2. WHEN the user clicks a "Save Version" button, THE System SHALL create a new version of the modified Deepgram response
3. THE System SHALL preserve the original Deepgram response as version 0
4. THE System SHALL maintain all previous versions in chronological order
5. THE System SHALL update word-level timing and structure to reflect text changes when creating new versions

### Requirement 5

**User Story:** As a transcript editor, I want file-based version management so that each edit creates a separate version file while preserving all previous versions intact.

#### Acceptance Criteria

1. THE System SHALL store each modified Deepgram response as a separate versioned JSON file
2. THE System SHALL preserve all previous version files intact when creating new versions
3. THE System SHALL use a structured naming convention for version files (e.g., filename_v1.json, filename_v2.json)
4. THE System SHALL organize transcript versions in a predictable directory structure
5. THE System SHALL maintain metadata about version creation time and changes in each version file

### Requirement 6

**User Story:** As a transcript editor, I want to switch between different versions in the UI so that I can compare edits and restore previous versions without leaving the application.

#### Acceptance Criteria

1. THE System SHALL display a version history interface showing all available versions
2. THE System SHALL allow selection of any previous version for viewing or restoration
3. WHEN switching versions, THE System SHALL load the selected Deepgram response and update the UI
4. THE System SHALL maintain audio synchronization when switching between versions
5. THE System SHALL provide visual indicators showing the currently active version

### Requirement 7

**User Story:** As a transcript editor, I want confidence-based visual indicators so that I can quickly identify sections that may need review or correction.

#### Acceptance Criteria

1. THE System SHALL display word-level confidence scores from the Deepgram response
2. THE System SHALL use color coding to indicate confidence levels (high: green, medium: yellow, low: red)
3. THE System SHALL highlight low-confidence words for priority review
4. THE System SHALL show confidence scores on hover or click for detailed information
5. THE System SHALL maintain confidence indicators when switching between versions

### Requirement 8

**User Story:** As a transcript editor, I want speaker management capabilities so that I can identify, label, and organize content by different speakers in the audio.

#### Acceptance Criteria

1. THE System SHALL display speaker information from the Deepgram response
2. THE System SHALL allow custom speaker name assignment to replace generic "Speaker 0" labels
3. THE System SHALL maintain speaker assignments across versions and edits
4. THE System SHALL provide speaker-based filtering and navigation options
5. THE System SHALL show speaker confidence scores for uncertain assignments