# Implementation Plan

- [x] 1. Remove OpenAI and AssemblyAI client files and dependencies
  - Delete `src/services/openai_client.py` file completely
  - Delete `src/services/assemblyai_client.py` file completely
  - Remove `openai` package from `requirements.txt`
  - Remove any AssemblyAI-specific dependencies from `requirements.txt`
  - _Requirements: 1.2, 1.3_

- [x] 2. Update service factory to only support Deepgram
  - Modify `src/services/service_factory.py` to remove OpenAI and AssemblyAI imports
  - Update `SUPPORTED_SERVICES` to only include 'deepgram'
  - Simplify `create_client()` method to only handle Deepgram cases
  - Remove service-specific language and feature detection for removed services
  - Update error messages to reflect Deepgram-only operation
  - _Requirements: 1.1, 1.4_

- [x] 3. Simplify configuration system for Deepgram-only operation
  - Update `src/utils/config.py` DEFAULT_CONFIG to remove AssemblyAI and OpenAI sections
  - Set default service to 'deepgram' or remove service selection entirely
  - Remove unused API key validation for OpenAI and AssemblyAI
  - Update configuration validation logic
  - _Requirements: 4.1, 4.2, 4.4_

- [x] 4. Update CLI interface to remove service selection
  - Modify `src/cli/main.py` to remove service choice option or default to 'deepgram'
  - Update help text and documentation to reflect Deepgram-only operation
  - Remove service validation logic in CLI argument processing
  - Simplify service parameter handling throughout CLI workflow
  - _Requirements: 1.1, 4.4_

- [x] 5. Clean up core orchestrator and utility classes
  - Update `src/core/transcription_orchestrator.py` to remove service branching logic
  - Modify `src/utils/glossary_manager.py` to remove AssemblyAI-specific formatting
  - Update `src/utils/error_handler.py` to remove service-specific error handling
  - Simplify transcription workflow to assume Deepgram throughout
  - _Requirements: 1.1, 5.4_

- [x] 6. Update Web API models and validation
  - Modify `api/models.py` TranscriptionRequest to only accept 'deepgram' or remove service field
  - Update API validation logic to handle Deepgram-only requests
  - Simplify transcription request processing in API endpoints
  - Update API documentation and response schemas
  - _Requirements: 2.1, 2.2, 2.4_

- [x] 7. Simplify API service managers for single service operation
  - Update `api/services/file_manager.py` to remove AssemblyAI from service loops
  - Modify `api/services/export_manager.py` to only handle Deepgram cache lookups
  - Simplify cache key generation and transcription loading logic
  - Update transcription status checking to focus on Deepgram results
  - _Requirements: 2.4, 5.2_

- [x] 8. Update Web UI to remove service selection interface
  - Modify `web-ui/src/types/index.ts` to update TranscriptionRequest service type
  - Remove service selection dropdown from `web-ui/src/components/FileManager.tsx`
  - Remove transcriptionService state management and related UI controls
  - Hardcode service to 'deepgram' in all transcription requests
  - _Requirements: 3.1, 3.2, 3.4_

- [x] 9. Update Web UI messaging and user experience
  - Update user interface text to reflect streamlined Deepgram approach
  - Remove service-related form controls and validation messages
  - Simplify transcription request workflow in the frontend
  - Update component documentation and comments
  - _Requirements: 3.3, 3.5_

- [x] 10. Test and validate the refactored system
  - Verify all existing Deepgram transcription functionality works correctly
  - Test that removed services are no longer accessible through any interface
  - Validate configuration loading with both new and legacy config files
  - Ensure backward compatibility with existing Deepgram transcriptions
  - _Requirements: 5.1, 5.2, 5.3, 5.5_

- [ ]* 11. Update documentation and configuration examples
  - Update configuration file examples to show Deepgram-only setup
  - Clean up environment variable documentation
  - Update API documentation to reflect single service operation
  - Create migration guide for users with existing multi-service setups
  - _Requirements: 4.3, 4.4_