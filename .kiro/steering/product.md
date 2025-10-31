# Product Overview

This is an Audio Transcription System designed for processing MP3 audio files containing seminars on Reams Biological Theory of Ionization (RBTI). The system provides automated transcription with speaker identification and specialized terminology recognition.

## Core Features

### Existing CLI System
- Deepgram transcription service integration (primary)
- Speaker diarization and identification
- Custom glossary support for RBTI-specific terminology (up to 1000 terms)
- Multiple output formats (HTML, Markdown) with rich styling
- Audio compression to reduce upload times
- Resume capability and caching
- Comprehensive error handling and progress tracking

### Web Manager (In Development)
- Directory-based audio file management
- Web-based transcription job orchestration
- Interactive transcript editing with react-transcript-editor component
- Manual edit management with speaker name customization
- Local static site publishing for bundled transcript sharing
- Manual refresh-based status checking (no real-time WebSocket)

## Target Use Case

The system is specifically designed for educational content transcription, particularly RBTI seminars, with emphasis on:
- Accurate technical terminology recognition
- Speaker identification for educational discussions
- Professional formatting for documentation and study materials
- Batch processing of lecture series
- Easy sharing through static site generation

## Architecture

The system consists of three main components:
1. **CLI Tool** (`src/`) - Core transcription engine and command-line interface (existing)
2. **Web API** (`api/`) - FastAPI backend for web interface (existing, being extended)
3. **Web Manager** (`web-ui/`) - React frontend for interactive transcription management (planned)