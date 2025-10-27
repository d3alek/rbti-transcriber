# Design Document

## Overview

This design adds OpenAI's speech-to-text transcription service as a third option alongside AssemblyAI and Deepgram. The implementation uses OpenAI's gpt-4o-transcribe-diarize model with built-in speaker diarization capabilities, following the existing architecture patterns.

## Architecture

The OpenAI integration follows the established service architecture:
- **OpenAI Client**: Implements TranscriptionClient interface
- **Service Factory**: Extended to create OpenAI client instances
- **CLI Integration**: Added as a third service option
- **Configuration**: Uses environment variables and config files

## Components and Interfaces

### OpenAI Client Implementation
```python
class OpenAIClient(TranscriptionClient):
    """OpenAI transcription service client using gpt-4o-transcribe-diarize model."""
    
    BASE_URL = "https://api.openai.com/v1"
    TRANSCRIPTIONS_URL = f"{BASE_URL}/audio/transcriptions"
    
    async def transcribe_file(self, file_path: Path, config: TranscriptionConfig) -> TranscriptionResult
    async def upload_audio(self, file_path: Path) -> str
```

### API Integration Details
- **Model**: gpt-4o-transcribe-diarize (specialized transcription model with diarization)
- **File Upload**: Direct file upload (max 25MB)
- **Response Format**: diarized_json with speaker segments and timestamps
- **Authentication**: Bearer token using OPENAI_API_KEY

### Service Factory Extension
```python
def create_openai_client(self, api_key: str) -> OpenAIClient:
    """Create and configure OpenAI transcription client."""
    client = OpenAIClient(api_key)
    return client
```

## Data Models

### OpenAI API Request Format
```json
{
  "file": "<audio_file>",
  "model": "gpt-4o-transcribe-diarize",
  "response_format": "diarized_json",
  "language": "en"
}
```

### OpenAI API Response Structure (diarized_json)
```json
{
  "task": "transcribe",
  "language": "english",
  "duration": 3669.0,
  "text": "Full transcript text...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 10.0,
      "text": "Hello, how are you today?",
      "speaker": "SPEAKER_00"
    },
    {
      "id": 1,
      "start": 10.5,
      "end": 15.0,
      "text": "I'm doing well, thank you.",
      "speaker": "SPEAKER_01"
    }
  ]
}
```

### Speaker Diarization Handling
OpenAI's gpt-4o-transcribe-diarize model with diarized_json format provides speaker identification in segments. The client will:
1. Parse speaker labels (SPEAKER_00, SPEAKER_01, etc.) from segments
2. Convert OpenAI speaker labels to consistent format (Speaker 0, Speaker 1, etc.)
3. Create SpeakerSegment objects with start/end times and speaker labels
4. Handle speaker transitions and maintain chronological order

## Error Handling

### OpenAI-Specific Errors
- **File Size Limit**: 25MB maximum file size
- **Rate Limiting**: Handle 429 responses with exponential backoff
- **Authentication**: Clear error messages for invalid API keys
- **Model Availability**: Handle model deprecation gracefully

### Error Mapping
```python
class OpenAITranscriptionError(TranscriptionServiceError):
    """OpenAI-specific transcription errors."""
    pass

class OpenAIFileSizeError(AudioUploadError):
    """File too large for OpenAI API."""
    pass

class OpenAIRateLimitError(TranscriptionServiceError):
    """OpenAI API rate limit exceeded."""
    pass
```

## Testing Strategy

### Unit Tests
- Test OpenAI client initialization and configuration
- Test API request formatting and response parsing
- Test error handling for various failure scenarios
- Test custom vocabulary integration

### Integration Tests
- Test end-to-end transcription workflow with OpenAI
- Test speaker diarization accuracy and formatting
- Test file size limits and error handling
- Test caching and format-only mode compatibility

### Comparison Testing
- Compare transcription quality across all three services
- Test consistency of speaker segment formatting
- Validate timestamp accuracy and precision

## Configuration

### Environment Variables
```bash
OPENAI_API_KEY=sk-...  # Required for OpenAI service
```

### Config File Updates
```yaml
services:
  openai:
    api_base_url: 'https://api.openai.com/v1'
    model: 'gpt-4o-transcribe-diarize'
    supports_custom_vocabulary: false
    supports_speaker_diarization: true
    max_file_size_mb: 25
```

### CLI Integration
```bash
# Use OpenAI service
python -m src.cli.main audio_dir --service openai

# All services comparison
python -m src.cli.main audio_dir --service openai --output-format both
```

## Performance Considerations

### File Size Optimization
- Leverage existing audio compression for files approaching 25MB limit
- Provide clear guidance when files exceed OpenAI limits
- Consider chunking for very large files (future enhancement)

### API Efficiency
- Use diarized_json format for speaker-segmented transcription
- Leverage built-in speaker diarization capabilities
- Implement proper retry logic for rate limits

### Cost Management
- Log API usage and estimated costs
- Provide cost estimates before processing large batches
- Support cost-aware processing modes