# Project Structure

## Root Level Organization

```
├── src/                    # Core transcription engine (CLI)
├── api/                    # FastAPI web backend
├── web-ui/                 # React frontend (planned)
├── test_audio/             # Sample audio files and test outputs
├── glossary_source/        # RBTI terminology source files
├── react-transcript-editor/ # BBC's transcript editor component (submodule)
├── config.yaml             # Main application configuration
├── requirements.txt        # Core Python dependencies
├── setup.py               # Package installation script
└── start_api.py           # API server startup script
```

## Core Engine (`src/`)

```
src/
├── cli/                    # Command-line interface
│   └── main.py            # CLI entry point
├── core/                   # Main orchestration logic
│   └── transcription_orchestrator.py
├── services/               # Transcription service clients
│   ├── deepgram_client.py # Primary transcription service
│   ├── transcription_client.py # Base client interface
│   └── service_factory.py
├── formatters/             # Output format generators
│   ├── base_formatter.py
│   ├── html_formatter.py
│   ├── markdown_formatter.py
│   └── formatter_factory.py
└── utils/                  # Shared utilities
    ├── audio_processor.py
    ├── audio_validator.py
    ├── cache_manager.py
    ├── config.py
    ├── error_handler.py
    ├── exceptions.py
    ├── file_scanner.py
    ├── glossary_manager.py
    └── progress_tracker.py
```

## Web API (`api/`)

```
api/
├── main.py                 # FastAPI application entry
├── config.py              # API configuration
├── models.py              # Pydantic data models
├── requirements.txt        # API-specific dependencies
├── routers/               # API route handlers
│   ├── files.py           # File management endpoints
│   └── transcription.py   # Transcription job endpoints
└── services/              # Business logic services
    ├── file_manager.py
    └── transcription_manager.py
```

## Frontend (`web-ui/`) - Planned

```
web-ui/
├── src/
│   ├── components/        # React components
│   │   ├── FileManager/   # Directory and file management
│   │   │   ├── DirectorySelector.tsx
│   │   │   ├── AudioFileList.tsx
│   │   │   ├── TranscriptionStatus.tsx
│   │   │   └── SeminarGroupView.tsx
│   │   ├── TranscriptEditor/ # Transcript editing interface
│   │   │   ├── TranscriptEditorWrapper.tsx
│   │   │   ├── DeepgramTransformer.ts
│   │   │   ├── ManualEditManager.tsx
│   │   │   └── AudioPlayerIntegration.tsx
│   │   ├── Publisher/     # Local static site publishing
│   │   │   ├── LocalSitePublisher.tsx
│   │   │   ├── PublishingStatus.tsx
│   │   │   └── StaticSiteGenerator.tsx
│   │   └── Shared/        # Shared components
│   │       ├── APIClient.ts
│   │       └── StatusIndicators.tsx
│   ├── types/             # TypeScript definitions
│   │   ├── api.ts
│   │   ├── deepgram.ts
│   │   └── transcriptEditor.ts
│   └── App.tsx           # Main application component
├── package.json
└── vite.config.ts
```

## Architecture Patterns

### Service Layer Pattern
- **Service Factory**: Creates appropriate transcription service clients
- **Formatter Factory**: Creates output formatters based on configuration
- **Manager Classes**: Handle complex business logic (FileManager, TranscriptionManager)

### Configuration Management
- **Centralized Config**: `config.yaml` for application settings
- **Environment Variables**: API keys and sensitive data in `.env`
- **Pydantic Settings**: Type-safe configuration validation in API

### Error Handling
- **Custom Exceptions**: Domain-specific error types in `src/utils/exceptions.py`
- **Error Handler**: Centralized error handling in `src/utils/error_handler.py`
- **Graceful Degradation**: Continue processing on non-critical errors
- **Comprehensive Logging**: Detailed error context and user-friendly messages

### Async Patterns
- **AsyncIO**: Used throughout for I/O operations
- **Manual Status Checking**: Refresh-based status updates (no real-time WebSocket)
- **Concurrent Processing**: Batch file processing with proper resource management

## Output Structure
Generated transcriptions follow this structure:
```
transcriptions/
├── html/                  # Rich HTML output
├── markdown/              # Markdown format
├── cache/                 # Cached API responses
├── metadata/              # Processing metadata
├── compressed/            # Compressed audio files
└── *.json                # Progress and report files
```