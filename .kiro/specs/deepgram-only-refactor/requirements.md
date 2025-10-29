# Requirements Document

## Introduction

This feature involves refactoring the Audio Transcription System to use Deepgram as the sole transcription service, removing OpenAI and AssemblyAI clients that have been outperformed by Deepgram in terms of accuracy, speed, and segment quality.

## Glossary

- **Transcription_System**: The Audio Transcription System for processing MP3 audio files
- **Deepgram_Client**: The Deepgram transcription service client implementation
- **OpenAI_Client**: The OpenAI transcription service client (to be removed)
- **AssemblyAI_Client**: The AssemblyAI transcription service client (to be removed)
- **Service_Factory**: Factory class that creates transcription service instances
- **Web_API**: FastAPI backend that provides REST endpoints for transcription
- **Web_UI**: React frontend interface for transcription management
- **Configuration_System**: YAML-based configuration management system

## Requirements

### Requirement 1

**User Story:** As a system administrator, I want to simplify the transcription system by removing underperforming services, so that the codebase is cleaner and maintenance is reduced.

#### Acceptance Criteria

1. WHEN the system starts, THE Transcription_System SHALL only support Deepgram as a transcription service
2. THE Transcription_System SHALL remove all OpenAI_Client code and dependencies
3. THE Transcription_System SHALL remove all AssemblyAI_Client code and dependencies
4. THE Service_Factory SHALL only create Deepgram_Client instances
5. THE Configuration_System SHALL remove OpenAI and AssemblyAI configuration options

### Requirement 2

**User Story:** As a developer, I want the Web API to only expose Deepgram as an option, so that users are not confused by multiple service choices.

#### Acceptance Criteria

1. THE Web_API SHALL only accept 'deepgram' as a valid transcription service parameter
2. THE Web_API SHALL remove OpenAI and AssemblyAI service validation options
3. THE Web_API SHALL update API documentation to reflect Deepgram-only support
4. THE Web_API SHALL maintain backward compatibility for existing Deepgram transcriptions
5. THE Web_API SHALL return appropriate error messages for unsupported service requests

### Requirement 3

**User Story:** As a user, I want the Web UI to streamline the transcription service selection, so that I can focus on transcription quality rather than service choice.

#### Acceptance Criteria

1. THE Web_UI SHALL remove service selection dropdowns and options
2. THE Web_UI SHALL automatically use Deepgram for all transcription requests
3. THE Web_UI SHALL update user interface text to reflect Deepgram-only operation
4. THE Web_UI SHALL maintain all existing transcription management features
5. THE Web_UI SHALL display appropriate messaging about the streamlined service approach

### Requirement 4

**User Story:** As a system maintainer, I want to clean up configuration files and dependencies, so that the system has minimal external dependencies and clearer configuration.

#### Acceptance Criteria

1. THE Transcription_System SHALL remove OpenAI and AssemblyAI API key requirements from configuration
2. THE Transcription_System SHALL update requirements.txt to remove unused service dependencies
3. THE Transcription_System SHALL clean up environment variable documentation
4. THE Transcription_System SHALL update configuration examples to show Deepgram-only setup
5. THE Transcription_System SHALL maintain existing Deepgram configuration options

### Requirement 5

**User Story:** As a developer, I want comprehensive testing to ensure the refactored system works correctly, so that existing functionality is preserved while removing unused code.

#### Acceptance Criteria

1. THE Transcription_System SHALL pass all existing Deepgram transcription tests
2. THE Transcription_System SHALL handle migration of existing cached transcriptions gracefully
3. THE Transcription_System SHALL maintain compatibility with existing output formats
4. THE Transcription_System SHALL preserve all existing Deepgram-specific features
5. THE Transcription_System SHALL validate that removed services are no longer accessible