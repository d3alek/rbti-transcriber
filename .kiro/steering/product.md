# Product Overview

This is an Audio Transcription System designed for processing MP3 audio files containing seminars on Reams Biological Theory of Ionization (RBTI). The system provides automated transcription with speaker identification and specialized terminology recognition.

## Core Features

- Multi-service transcription support (AssemblyAI, Deepgram, OpenAI)
- Speaker diarization and identification
- Custom glossary support for RBTI-specific terminology (up to 1000 terms)
- Multiple output formats (HTML, Markdown) with rich styling
- Audio compression to reduce upload times
- Resume capability and caching
- Web UI for interactive transcription management
- Real-time progress tracking via WebSocket

## Target Use Case

The system is specifically designed for educational content transcription, particularly RBTI seminars, with emphasis on:
- Accurate technical terminology recognition
- Speaker identification for educational discussions
- Professional formatting for documentation and study materials
- Batch processing of lecture series

## Architecture

The system consists of three main components:
1. **CLI Tool** (`src/`) - Core transcription engine and command-line interface
2. **Web API** (`api/`) - FastAPI backend for web interface
3. **Web UI** (`web-ui/`) - React frontend for interactive transcription management