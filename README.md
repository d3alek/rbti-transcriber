# Audio Transcription System

An automated transcription system that processes directories of MP3 audio files containing seminars on Reams Biological Theory of Ionization (RBTI), producing rich-text transcriptions with speaker identification and specialized terminology recognition.

## Features

- **Multi-Service Support**: AssemblyAI and Deepgram transcription services
- **Speaker Diarization**: Automatic speaker identification and labeling
- **Custom Glossary**: RBTI-specific terminology recognition (up to 1000 terms)
- **Multiple Output Formats**: HTML and Markdown with rich styling
- **Audio Compression**: Optional FFmpeg-based compression to reduce upload times
- **Resume Capability**: Skip already processed files automatically
- **Format-Only Mode**: Re-format cached transcriptions without re-transcribing
- **Progress Tracking**: Real-time progress with detailed reporting
- **Error Handling**: Comprehensive error handling with fail-fast options

## Installation

### Prerequisites

- Python 3.8+
- FFmpeg (optional, for audio compression)

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Install FFmpeg (Optional)

For audio compression support:

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html

## Configuration

### API Keys

Set your transcription service API keys as environment variables:

```bash
export ASSEMBLYAI_API_KEY="your_assemblyai_key_here"
export DEEPGRAM_API_KEY="your_deepgram_key_here"
```

Or create a `.env` file:
```
ASSEMBLYAI_API_KEY=your_assemblyai_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here
```

### Configuration File

The system uses `config.yaml` for settings. Key configurations:

```yaml
transcription:
  default_service: assemblyai
  speaker_diarization: true
  max_speakers: 3

output:
  formats: [html, markdown]
  timestamp_interval: 30
  cache_responses: true

glossary:
  max_terms: 1000
  warn_on_truncation: true
```

## Usage

### Basic Transcription

```bash
python -m src.cli.main /path/to/audio/files
```

### Advanced Options

```bash
python -m src.cli.main /path/to/audio/files \
  --service deepgram \
  --output-format html \
  --compress-audio \
  --glossary /path/to/custom/glossary.txt \
  --verbose
```

### Format-Only Mode

Re-format previously transcribed files:

```bash
python -m src.cli.main /path/to/audio/files \
  --mode format-only \
  --output-format both
```

### Create Default RBTI Glossary

```bash
python -m src.cli.main /path/to/audio/files \
  --create-default-glossary rbti_glossary.txt
```

## Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--service` | Transcription service (assemblyai/deepgram) | From config |
| `--mode` | Operation mode (transcribe/format-only) | transcribe |
| `--output-format` | Output format (html/markdown/both) | both |
| `--compress-audio` | Enable audio compression | False |
| `--glossary` | Custom glossary file(s) | None |
| `--output-dir` | Output directory | audio_dir/transcriptions |
| `--fail-fast` | Stop on first error | True |
| `--verbose` | Enable verbose output | False |

## Output Structure

The system creates organized output directories:

```
transcriptions/
├── html/                 # HTML transcriptions
│   ├── file1.html
│   └── file2.html
├── markdown/             # Markdown transcriptions
│   ├── file1.md
│   └── file2.md
├── cache/                # Cached API responses
│   ├── response1.json
│   └── response2.json
├── metadata/             # Processing metadata
├── compressed/           # Compressed audio files
├── transcription.log     # Processing log
└── progress.json         # Progress tracking
```

## Custom Glossary

Create custom glossary files with one term per line:

```
# RBTI Glossary
RBTI
Reams Biological Theory of Ionization
Carey Reams
biological ionization
urine pH
saliva pH
conductivity
```

The system includes a default RBTI glossary with common terms.

## Output Formats

### HTML Format
- Rich styling with embedded CSS
- Speaker identification with color coding
- Timestamp markers every 30 seconds
- Confidence indicators
- Responsive design

### Markdown Format
- Speaker headers and sections
- Timestamp blockquotes
- Confidence emoji indicators
- Compatible with standard markdown parsers

## Error Handling

The system provides comprehensive error handling:

- **Fail-fast mode**: Stop on first critical error
- **Graceful degradation**: Continue processing other files on non-critical errors
- **Detailed logging**: Full error logs with context
- **User-friendly messages**: Clear error descriptions and solutions

## Performance Features

- **Resume capability**: Automatically skip processed files
- **Caching**: Store API responses to avoid re-transcription
- **Audio compression**: Reduce upload times with FFmpeg
- **Batch processing**: Efficient handling of multiple files
- **Progress tracking**: Real-time progress with ETA

## API Service Comparison

| Feature | AssemblyAI | Deepgram |
|---------|------------|----------|
| Speaker Diarization | ✅ | ✅ |
| Custom Vocabulary | ✅ | ✅ |
| Async Processing | ✅ | ❌ (Sync) |
| Language Support | 🌍 Wide | 🌍 Wide |
| Pricing | Pay-per-minute | Pay-per-minute |

## Troubleshooting

### Common Issues

**"No API key found"**
- Set the appropriate environment variable
- Check `.env` file exists and is properly formatted

**"FFmpeg not found"**
- Install FFmpeg or disable audio compression
- Ensure FFmpeg is in your system PATH

**"No MP3 files found"**
- Check directory path is correct
- Ensure files have `.mp3` extension
- Verify file permissions

**"Invalid audio file"**
- Check MP3 file integrity
- Ensure files are not corrupted
- Verify minimum file size requirements

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
python -m src.cli.main /path/to/audio/files --verbose
```

## Development

### Project Structure

```
src/
├── cli/                    # Command-line interface
├── core/                   # Main orchestration
├── services/               # Transcription service clients
├── formatters/             # Output formatters
└── utils/                  # Utilities and helpers
```

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/
```

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review error logs in the output directory
- Create an issue on GitHub with detailed error information