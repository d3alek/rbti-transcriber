# Requirements Document

## Introduction

Fix critical issues in the audio transcription system including missing imports, timestamp formatting, and duration display problems.

## Glossary

- **TranscriptionResult**: Data structure containing transcription text, speaker segments, and metadata
- **HTMLFormatter**: Component responsible for generating HTML output with timestamps and speaker styling
- **ConfigManager**: Configuration management system for application settings
- **SpeakerSegment**: Individual speaker utterance with start/end times and text content

## Requirements

### Requirement 1

**User Story:** As a developer, I want the transcription system to have proper imports and function definitions, so that the CLI can run without import errors.

#### Acceptance Criteria

1. WHEN the CLI is executed, THE system SHALL import all required functions without errors
2. THE config module SHALL provide a load_config function for backward compatibility
3. THE HTMLFormatter SHALL have all required methods defined including _format_timestamp

### Requirement 2

**User Story:** As a user, I want to see accurate audio duration and timestamps in the HTML output, so that I can navigate the transcription effectively.

#### Acceptance Criteria

1. WHEN audio is transcribed, THE system SHALL extract the correct audio duration from the API response
2. THE HTML output SHALL display the audio duration in MM:SS or HH:MM:SS format
3. THE system SHALL add timestamp markers at regular intervals throughout the transcript
4. WHEN timestamps are displayed, THE system SHALL format them as MM:SS for readability

### Requirement 3

**User Story:** As a user, I want the Deepgram client to properly parse API responses, so that all timing information is preserved and displayed.

#### Acceptance Criteria

1. THE Deepgram client SHALL extract audio duration from the metadata section of the API response
2. THE system SHALL preserve start_time and end_time for each speaker segment
3. WHEN no duration is found in metadata, THE system SHALL calculate duration from the last segment end time
4. THE system SHALL handle both utterances and paragraphs response formats from Deepgram