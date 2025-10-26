# Implementation Plan

- [x] 1. Set up project structure and core interfaces
  - Create directory structure for CLI, services, formatters, and utilities
  - Define abstract base classes for transcription clients and formatters
  - Set up configuration management with YAML support
  - _Requirements: 1.1, 1.3_

- [ ] 2. Implement file processing and directory management
  - [x] 2.1 Create file scanner and validator for MP3 files
    - Implement directory scanning to find all MP3 files
    - Add audio file format validation using file headers
    - Create output directory structure (html/, markdown/, cache/, metadata/)
    - _Requirements: 1.1, 1.2, 1.3, 6.6_

  - [x] 2.2 Implement resume logic and cache detection
    - Build logic to detect existing transcription files
    - Create cache manager for raw service responses
    - Implement skip logic for already processed files
    - _Requirements: 5.6, 6.3_

- [x] 3. Build audio processing and compression system
  - [x] 3.1 Implement FFmpeg integration for audio compression
    - Create audio processor class with FFmpeg wrapper
    - Add bitrate analysis and compression logic (target 64kbps)
    - Implement compressed file caching system
    - _Requirements: Performance optimization for slow uploads_

  - [x] 3.2 Add audio file validation and quality checks
    - Validate MP3 file integrity before processing
    - Check audio duration and format compatibility
    - Implement fail-fast validation as specified
    - _Requirements: 5.1, 5.5_

- [ ] 4. Create transcription service clients
  - [x] 4.1 Implement abstract transcription client interface
    - Define base class with common methods for both services
    - Create data models for transcription config and results
    - Add error handling classes for service-specific errors
    - _Requirements: 2.1, 3.1, 3.2_

  - [x] 4.2 Build AssemblyAI client implementation
    - Implement AssemblyAI API integration with async support
    - Add speaker diarization configuration (up to 3 speakers)
    - Integrate custom vocabulary support with 1000 term limit
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.4_

  - [x] 4.3 Build Deepgram client implementation
    - Implement Deepgram API integration with async support
    - Add speaker diarization configuration (up to 3 speakers)
    - Integrate custom vocabulary support with 1000 term limit
    - _Requirements: 2.1, 2.2, 2.3, 3.1, 3.4_

- [x] 5. Implement custom glossary management
  - [x] 5.1 Create glossary loader and validator
    - Load terms from text files (one term per line)
    - Validate and limit to 1000 terms maximum
    - Implement truncation with warnings for oversized glossaries
    - _Requirements: 3.1, 3.3, 3.4_

  - [x] 5.2 Integrate glossary with transcription services
    - Apply custom vocabulary to AssemblyAI requests
    - Apply custom vocabulary to Deepgram requests
    - Handle service-specific vocabulary formatting
    - _Requirements: 3.2, 3.5_

- [x] 6. Build output formatters
  - [x] 6.1 Implement HTML formatter with rich styling
    - Create HTML templates with embedded CSS
    - Add speaker identification with distinct colors
    - Implement timestamp markers every 30 seconds
    - Format paragraph breaks and speech flow
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 6.1_

  - [x] 6.2 Implement Markdown formatter
    - Create markdown output with speaker headers
    - Add timestamp markers as blockquotes
    - Preserve paragraph structure and line breaks
    - Ensure compatibility with standard markdown parsers
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 6.1_

  - [x] 6.3 Add format-only mode for cached responses
    - Implement cache reader for stored JSON responses
    - Create formatter that works from cached data only
    - Add validation for cache integrity and completeness
    - _Requirements: 6.4, 6.5_

- [x] 7. Create CLI interface and orchestration
  - [x] 7.1 Build Click-based command line interface
    - Implement main CLI with all required options (service, mode, format, etc.)
    - Add argument validation and help text
    - Create service selection logic (AssemblyAI/Deepgram)
    - _Requirements: 1.1, 6.2_

  - [x] 7.2 Implement progress tracking and reporting
    - Create progress indicators for file processing
    - Add real-time status updates during transcription
    - Generate summary reports of successful/failed transcriptions
    - _Requirements: 5.2, 5.3_

  - [x] 7.3 Add comprehensive error handling
    - Implement fail-fast error handling for all failure modes
    - Create clear error messages for service unavailability
    - Add logging for debugging and audit trails
    - _Requirements: 5.1, 5.4_

- [ ] 8. Integration and workflow orchestration
  - [x] 8.1 Wire together transcription workflow
    - Connect file processing, transcription, and formatting components
    - Implement main processing loop with error handling
    - Add resume capability integration
    - _Requirements: 1.2, 1.4, 1.5, 5.6_

  - [x] 8.2 Implement format-only workflow
    - Create separate workflow for cache-based formatting
    - Connect cache reader with formatters
    - Add validation for format-only mode requirements
    - _Requirements: 6.4, 6.5_

- [ ]* 9. Testing and validation
  - [ ]* 9.1 Create unit tests for core components
    - Test file processing and validation logic
    - Test glossary management and term limiting
    - Test formatter output quality and structure
    - _Requirements: All core functionality_

  - [ ]* 9.2 Add integration tests for transcription services
    - Test AssemblyAI client with mock responses
    - Test Deepgram client with mock responses
    - Test end-to-end workflow with sample audio files
    - _Requirements: Service integration reliability_