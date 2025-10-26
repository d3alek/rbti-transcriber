# Audio Transcription System

An automated transcription system that processes directories of MP3 audio files containing seminars on Reams Biological Theory of Ionization (RBTI), producing rich-text transcriptions with speaker identification and specialized terminology recognition.

## Project Structure

```
├── src/
│   ├── cli/                    # Command-line interface
│   │   ├── __init__.py
│   │   └── main.py            # Main CLI entry point
│   ├── services/              # Transcription service clients
│   │   ├── __init__.py
│   │   └── transcription_client.py  # Abstract base class
│   ├── formatters/            # Output formatters
│   │   ├── __init__.py
│   │   └── base_formatter.py  # Abstract base class
│   └── utils/                 # Utilities and configuration
│       ├── __init__.py
│       ├── config.py          # Configuration management
│       └── exceptions.py      # Custom exceptions
├── config.yaml               # Default configuration
├── requirements.txt          # Python dependencies
├── setup.py                 # Package setup
└── README.md               # This file
```

## Installation

```bash
pip install -r requirements.txt
```

## Configuration

The system uses YAML configuration files. See `config.yaml` for the default configuration structure.

## Usage

```bash
python -m src.cli.main /path/to/audio/directory --service assemblyai --output-format both
```

## Environment Variables

- `ASSEMBLYAI_API_KEY`: API key for AssemblyAI service
- `DEEPGRAM_API_KEY`: API key for Deepgram service