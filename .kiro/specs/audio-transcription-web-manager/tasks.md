# Implementatio Plan

Convert the audio transcription web manager design into a series of prompts for a code-generation LLM that will implement each step with incremental progress. Each task builds on previous tasks and focuses on writing, modifying, or testing code components.

- [x] 1. Set up core data structures and TypeScript interfaces
  - Create TypeScript interfaces for CorrectedDeepgramResponse, ReactTranscriptEditorData, and AudioFileInfo
  - Define PublishBundle, TranscriptionResult, and API response types
  - Set up error handling types and validation schemas
  - _Requirements: 1.1, 1.4, 1.5_

- [x] 2. Implement backend file system scanner
  - [x] 2.1 Create FileSystemScanner service
    - Write functions to scan directories for MP3 audio files
    - Implement transcription status checking by looking for corresponding .json files
    - Add audio metadata extraction (duration, file size)
    - _Requirements: 1.1, 1.2, 1.3_

  - [x] 2.2 Build directory scanning API endpoint
    - Create FastAPI endpoint for directory selection and scanning
    - Implement seminar group organization based on directory names
    - Add compressed audio file detection and size reporting
    - _Requirements: 1.1, 1.2, 1.4, 1.5_

  - [ ]* 2.3 Add file system validation and error handling
    - Implement directory access permission checking
    - Add file corruption detection for existing transcription files
    - Create error handling for invalid audio formats
    - _Requirements: 1.1, 1.2_

- [x] 3. Create transcription service integration
  - [x] 3.1 Implement TranscriptionService class
    - Write function to call existing Deepgram transcription system
    - Create initial CorrectedDeepgramResponse from raw Deepgram response
    - Add compressed audio generation during transcription process
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 3.2 Build transcription API endpoints
    - Create POST /api/transcribe/{audioFile} endpoint to trigger transcription
    - Implement GET /api/transcription-status/{audioFile} for status checking
    - Add error handling and retry mechanisms for failed transcriptions
    - _Requirements: 2.1, 2.2, 2.4, 2.5_

  - [ ]* 3.3 Add transcription job validation
    - Implement audio file format validation before transcription
    - Add file size limits and processing time estimates
    - Create comprehensive error logging for transcription failures
    - _Requirements: 2.1, 2.2_

- [x] 4. Implement Deepgram data transformer
  - [x] 4.1 Create DeepgramTransformer service
    - Write transformToReactTranscriptEditor function to convert CorrectedDeepgramResponse to ReactTranscriptEditorData
    - Implement word-level correction detection and original word preservation
    - Add speaker name mapping from corrections metadata to display format
    - _Requirements: 3.1, 3.2, 3.3, 9.2, 9.3_

  - [x] 4.2 Build correction merging functionality
    - Create mergeCorrectionsIntoDeepgramResponse function
    - Implement word-level correction embedding in Deepgram response structure
    - Add speaker name mapping storage in corrections metadata
    - _Requirements: 4.1, 4.2, 4.3, 9.1, 9.4_

  - [x] 4.3 Create round-trip transformation test
    - Write test that converts raw Deepgram response to ReactTranscriptEditorData format
    - Transform the ReactTranscriptEditorData back to CorrectedDeepgramResponse format
    - Verify that original Deepgram response and final CorrectedDeepgramResponse are equivalent
    - Ensure no data loss occurs during the transformation cycle
    - _Requirements: 3.1, 3.2, 4.1, 4.2_

  - [ ]* 4.4 Add data validation and integrity checks
    - Implement validation for ReactTranscriptEditorData structure
    - Add consistency checks between word corrections and timing data
    - Create error handling for malformed correction data
    - _Requirements: 4.1, 4.2, 4.3_

- [x] 5. Build React frontend file manager
  - [x] 5.1 Create DirectorySelector component
    - Build interface for selecting local audio directories
    - Implement directory browsing with file system API integration
    - Add loading states and error handling for directory access
    - _Requirements: 1.1, 1.2_

  - [x] 5.2 Implement AudioFileList component
    - Create file list display with transcription status indicators
    - Add seminar group organization and filtering
    - Implement "Start Transcription" buttons for files without transcriptions
    - _Requirements: 1.2, 1.3, 1.4, 2.1, 2.2_

  - [x] 5.3 Add file status management
    - Create status indicators for transcription completion, failure, and missing states
    - Implement page refresh to update file statuses after transcription jobs
    - Add file size display for original and compressed audio files
    - _Requirements: 1.3, 1.4, 2.4, 7.2, 8.1, 8.2_

- [x] 6. Create transcript editor integration
  - [x] 6.1 Build TranscriptEditorWrapper component
    - Create wrapper component that loads CorrectedDeepgramResponse data
    - Implement data transformation to ReactTranscriptEditorData format
    - Add integration with existing react-transcript-editor component
    - _Requirements: 3.1, 3.2, 3.4_

  - [x] 6.2 Implement audio player integration
    - Ensure compressed audio file usage for all playback operations
    - Add file size display in transcript editor interface
    - Implement word-level highlighting during audio playback
    - _Requirements: 3.3, 3.4, 3.5, 8.1, 8.2, 8.4_

  - [ ] 6.3 Add manual correction functionality
    - Create interface for editing individual words in transcript
    - Implement visual indicators for corrected words with original word tooltips
    - Add speaker name editing interface with custom name assignment
    - _Requirements: 4.1, 4.4, 4.5, 9.1, 9.2, 9.3_

- [ ] 7. Implement save and correction management
  - [ ] 7.1 Create correction save functionality
    - Build "Save Edits" button and save operation
    - Implement merging of ReactTranscriptEditorData changes back to CorrectedDeepgramResponse
    - Add file system writing of updated transcription files
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ] 7.2 Add correction persistence API
    - Create PUT /api/transcripts/{audioFile}/corrections endpoint
    - Implement atomic file writing to prevent corruption during saves
    - Add backup creation before overwriting existing transcription files
    - _Requirements: 4.1, 4.2, 9.4, 9.5_

  - [ ]* 7.3 Add correction history and versioning
    - Implement simple backup system for transcription file versions
    - Add timestamp tracking for correction saves
    - Create rollback functionality for undoing corrections
    - _Requirements: 4.1, 4.2_

- [ ] 8. Build local static site publisher
  - [ ] 8.1 Create LocalSitePublisher service
    - Write function to generate HTML pages for individual transcripts
    - Implement seminar group index page generation
    - Create main site index with all seminar groups
    - _Requirements: 5.1, 5.2, 5.3, 6.1, 6.2_

  - [ ] 8.2 Implement local gh-pages directory structure
    - Create organized directory structure for static site files in local gh-pages folder
    - Copy compressed audio files to appropriate locations
    - Write CorrectedDeepgramResponse files alongside HTML pages
    - _Requirements: 5.2, 5.3, 5.4, 6.3_

  - [ ] 8.3 Add publishing UI components
    - Create "Publish to Local Site" buttons in file list and transcript editor
    - Implement publishing status display and progress indicators
    - Add success/error feedback for publishing operations
    - _Requirements: 5.1, 5.2_

- [ ] 9. Create static site templates and navigation
  - [ ] 9.1 Build HTML templates for transcript pages
    - Create responsive HTML template for individual transcript display
    - Implement embedded audio player with transcript synchronization
    - Add speaker name display using custom names from corrections metadata
    - _Requirements: 6.1, 6.2, 6.3, 9.5_

  - [ ] 9.2 Implement navigation and index pages
    - Create main index page template listing all seminar groups
    - Build seminar group pages showing all transcripts in each group
    - Add breadcrumb navigation between main index, groups, and individual transcripts
    - _Requirements: 6.1, 6.2, 6.3, 6.5_

  - [ ]* 9.3 Add advanced static site features
    - Implement search functionality across all transcripts
    - Add CSS styling for professional appearance
    - Create responsive design for mobile and desktop viewing
    - _Requirements: 6.1, 6.2, 6.3_

- [ ] 10. Integrate all components and add error handling
  - [ ] 10.1 Wire up frontend routing and navigation
    - Create React Router setup for file manager and transcript editor views
    - Implement navigation between file list and individual transcript editing
    - Add back button functionality and breadcrumb navigation
    - _Requirements: 1.1, 3.1, 5.1_

  - [ ] 10.2 Add comprehensive error handling
    - Implement error boundaries for React components
    - Add user-friendly error messages for common failure scenarios
    - Create retry mechanisms for failed API calls
    - _Requirements: 1.1, 2.5, 7.1, 7.2_

  - [ ]* 10.3 Add performance optimizations
    - Implement lazy loading for large file lists
    - Add memoization for expensive data transformations
    - Optimize re-rendering with React.memo and useMemo
    - _Requirements: 1.1, 3.1, 8.1_

- [ ] 11. Add API client and communication layer
  - [ ] 11.1 Create APIClient service
    - Build centralized HTTP client for all backend communication
    - Implement request/response handling with proper error management
    - Add timeout and retry logic for network operations
    - _Requirements: 1.1, 2.1, 7.1_

  - [ ] 11.2 Add API integration throughout frontend
    - Connect file manager components to directory scanning APIs
    - Integrate transcription triggering with backend transcription service
    - Wire up correction saving to transcription update endpoints
    - _Requirements: 1.2, 2.1, 4.1, 5.1_

  - [ ]* 11.3 Add API caching and optimization
    - Implement response caching for frequently accessed data
    - Add request deduplication to prevent duplicate API calls
    - Create background refresh for file status updates
    - _Requirements: 1.1, 2.1, 7.1_

- [ ] 12. Final integration and testing
  - [ ]* 12.1 Create unit tests for core services
    - Test DeepgramTransformer data conversion functions
    - Test FileSystemScanner directory scanning and status checking
    - Test LocalSitePublisher HTML generation and file writing
    - _Requirements: 1.1, 2.1, 5.1_

  - [ ]* 12.2 Add integration tests for API endpoints
    - Test directory scanning and transcription status endpoints
    - Test transcription triggering and correction saving endpoints
    - Test publishing workflow from transcript to local static site generation
    - _Requirements: 2.1, 4.1, 5.1_

  - [ ] 12.3 Create end-to-end workflow validation
    - Test complete workflow: directory scan → transcription → editing → publishing
    - Validate data integrity throughout the correction and publishing process
    - Ensure proper error handling and recovery in all failure scenarios
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1_