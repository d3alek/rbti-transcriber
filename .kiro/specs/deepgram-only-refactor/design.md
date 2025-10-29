# Design Document

## Overview

This design outlines the systematic removal of OpenAI and AssemblyAI transcription services from the Audio Transcription System, streamlining the codebase to use Deepgram as the sole transcription provider. The refactor will simplify configuration, reduce dependencies, and eliminate service selection complexity while maintaining all existing functionality.

## Architecture

### Current Multi-Service Architecture
The system currently supports three transcription services through a factory pattern:
- Service Factory creates appropriate client instances
- Configuration supports multiple API keys and service-specific settings
- Web API accepts service selection parameters
- Web UI provides service selection dropdowns

### Target Single-Service Architecture
The refactored system will use Deepgram exclusively:
- Simplified service factory that only creates Deepgram clients
- Streamlined configuration with only Deepgram settings
- Web API automatically uses Deepgram without service parameters
- Web UI removes service selection interface

## Components and Interfaces

### Core Service Layer Changes

#### Service Factory Simplification
**File**: `src/services/service_factory.py`
- Remove `SUPPORTED_SERVICES` list (or set to `['deepgram']`)
- Remove AssemblyAI and OpenAI client imports
- Simplify `create_client()` method to only handle Deepgram
- Remove service-specific language and feature detection
- Update error messages to reflect Deepgram-only operation

#### Client Removal
**Files to Remove**:
- `src/services/assemblyai_client.py` - Complete removal
- `src/services/openai_client.py` - Complete removal

**Dependencies to Remove**:
- `openai` package from requirements.txt
- AssemblyAI-specific HTTP client dependencies

#### Configuration System Updates
**File**: `src/utils/config.py`
- Remove `assemblyai` section from DEFAULT_CONFIG
- Remove OpenAI configuration options
- Update `default_service` to be 'deepgram'
- Simplify service validation logic
- Remove unused API key validation for removed services

#### CLI Interface Updates
**File**: `src/cli/main.py`
- Remove service choice option (or set default to 'deepgram')
- Update help text to reflect Deepgram-only operation
- Remove service validation logic
- Simplify service parameter handling

#### Core Orchestrator Updates
**File**: `src/core/transcription_orchestrator.py`
- Remove service-specific branching logic
- Simplify transcription workflow to assume Deepgram
- Update error handling to remove service-specific messages
- Clean up service parameter validation

### Utility Layer Changes

#### Glossary Manager Updates
**File**: `src/utils/glossary_manager.py`
- Remove AssemblyAI-specific term formatting
- Simplify `get_terms_for_service()` method
- Remove service-specific term limits and formatting

#### Error Handler Updates
**File**: `src/utils/error_handler.py`
- Remove AssemblyAI and OpenAI error handling branches
- Simplify API key error messages to only mention Deepgram
- Update service-specific error documentation

### Web API Layer Changes

#### API Models Updates
**File**: `api/models.py`
- Change `TranscriptionRequest.service` from `Literal['assemblyai', 'deepgram']` to `Literal['deepgram']`
- Or remove service field entirely and default to Deepgram
- Update API documentation to reflect single service

#### File Manager Updates
**File**: `api/services/file_manager.py`
- Remove AssemblyAI from service iteration loops
- Simplify cache key generation to only handle Deepgram
- Update transcription status checking logic

#### Export Manager Updates
**File**: `api/services/export_manager.py`
- Remove AssemblyAI from service cache lookup loops
- Simplify transcription loading to prioritize Deepgram only

### Web UI Layer Changes

#### TypeScript Types Updates
**File**: `web-ui/src/types/index.ts`
- Change `TranscriptionRequest.service` type to only include 'deepgram'
- Or remove service field entirely

#### File Manager Component Updates
**File**: `web-ui/src/components/FileManager.tsx`
- Remove service selection dropdown
- Remove `transcriptionService` state management
- Hardcode service to 'deepgram' in transcription requests
- Update UI text to reflect streamlined approach
- Remove service-related form controls

## Data Models

### Existing Data Preservation
- All existing Deepgram transcriptions remain compatible
- Cache files maintain current format
- Output formats (HTML, Markdown) unchanged
- Speaker segment structure preserved

### Configuration Schema Changes
```yaml
# Before (multiple services)
transcription:
  default_service: 'assemblyai'
  
services:
  assemblyai:
    api_key: 'key'
  deepgram:
    api_key: 'key'
  openai:
    api_key: 'key'

# After (Deepgram only)
transcription:
  default_service: 'deepgram'  # or remove entirely
  
services:
  deepgram:
    api_key: 'key'
```

### API Request Changes
```typescript
// Before
interface TranscriptionRequest {
  file_id: string;
  service: 'assemblyai' | 'deepgram';
  compress_audio: boolean;
  output_formats: string[];
}

// After
interface TranscriptionRequest {
  file_id: string;
  // service field removed - always Deepgram
  compress_audio: boolean;
  output_formats: string[];
}
```

## Error Handling

### Migration Strategy
- Graceful handling of existing cached transcriptions from removed services
- Clear error messages if users attempt to use removed services
- Fallback behavior for configuration files with old service settings

### Validation Updates
- Remove service validation for OpenAI and AssemblyAI
- Simplify API key validation to only check Deepgram
- Update error messages to guide users to Deepgram setup

### Backward Compatibility
- Existing Deepgram transcriptions continue to work
- Configuration files with old settings are handled gracefully
- API endpoints maintain response format compatibility

## Testing Strategy

### Unit Tests
- Update service factory tests to only test Deepgram creation
- Remove AssemblyAI and OpenAI client tests
- Update configuration tests for simplified schema
- Test error handling for removed services

### Integration Tests
- Verify end-to-end transcription workflow with Deepgram only
- Test Web API endpoints with simplified request format
- Validate Web UI functionality without service selection
- Test migration of existing cached transcriptions

### Regression Tests
- Ensure existing Deepgram functionality is preserved
- Verify output format generation remains unchanged
- Test speaker diarization and segment quality
- Validate configuration loading with legacy files

## Migration Plan

### Phase 1: Backend Cleanup
1. Remove OpenAI and AssemblyAI client files
2. Update service factory and configuration
3. Clean up CLI interface and orchestrator
4. Update utility classes

### Phase 2: API Simplification
1. Update API models and validation
2. Simplify service manager logic
3. Update file and export managers
4. Test API endpoints

### Phase 3: Frontend Updates
1. Remove service selection UI components
2. Update TypeScript types
3. Simplify transcription request logic
4. Update user interface messaging

### Phase 4: Documentation and Cleanup
1. Update configuration examples
2. Clean up requirements.txt
3. Update API documentation
4. Remove unused environment variables