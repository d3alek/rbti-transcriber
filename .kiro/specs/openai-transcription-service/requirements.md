# Requirements Document

## Introduction

Add OpenAI's speech-to-text transcription service to the audio transcription system using the gpt-4o-transcribe-diarize model with speaker diarization capabilities.

## Glossary

- **OpenAI Transcription API**: OpenAI's speech-to-text service using advanced language models
- **gpt-4o-transcribe-diarize**: OpenAI's audio transcription model with built-in speaker diarization
- **Speaker Diarization**: The process of partitioning audio into segments according to speaker identity
- **TranscriptionClient**: Abstract base class for transcription service implementations
- **ServiceFactory**: Factory class that creates and configures transcription service instances


## Requirements

### Requirement 1

**User Story:** As a user, I want to use OpenAI's transcription service as an alternative to AssemblyAI and Deepgram, so that I can compare transcription quality and choose the best service for my needs.

#### Acceptance Criteria

1. THE system SHALL support OpenAI as a third transcription service option alongside AssemblyAI and Deepgram
2. WHEN the user specifies --service openai, THE system SHALL use OpenAI's transcription API
3. THE OpenAI client SHALL implement the same TranscriptionClient interface as other services
4. THE system SHALL handle OpenAI API authentication using OPENAI_API_KEY environment variable

### Requirement 2

**User Story:** As a user, I want OpenAI transcription to support speaker diarization, so that I can identify different speakers in the audio transcript.

#### Acceptance Criteria

1. THE OpenAI client SHALL use the gpt-4o-transcribe-diarize model for transcription with speaker diarization
2. WHEN speaker diarization is enabled, THE system SHALL identify and label different speakers in the transcript
3. THE OpenAI client SHALL parse speaker segments with start/end timestamps from the API response
4. THE system SHALL format OpenAI speaker segments consistently with other services

### Requirement 3

**User Story:** As a user, I want OpenAI transcription to handle various audio formats and file sizes, so that I can transcribe different types of audio files.

#### Acceptance Criteria

1. THE OpenAI client SHALL support MP3 audio file uploads up to 25MB per OpenAI limits
2. WHEN audio files exceed size limits, THE system SHALL provide clear error messages
3. THE OpenAI client SHALL handle network timeouts and API rate limits gracefully
4. THE system SHALL cache OpenAI transcription responses for format-only mode support

### Requirement 4

**User Story:** As a developer, I want the OpenAI service integration to follow the existing architecture patterns, so that it's maintainable and consistent with other services.

#### Acceptance Criteria

1. THE OpenAI client SHALL extend the TranscriptionClient abstract base class
2. THE ServiceFactory SHALL create and configure OpenAI client instances
3. THE OpenAI client SHALL use the same error handling patterns as other services
4. THE system SHALL include OpenAI in CLI help text and configuration options