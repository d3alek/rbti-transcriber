# Technology Stack

## Backend Technologies

### Core Python Stack
- **Python 3.8+** - Main runtime
- **Click** - CLI framework for command-line interface
- **PyYAML** - Configuration file handling
- **aiohttp/aiofiles** - Async HTTP client and file operations
- **python-dotenv** - Environment variable management

### Web API Stack
- **FastAPI** - Modern async web framework
- **Uvicorn** - ASGI server with WebSocket support
- **Pydantic** - Data validation and settings management
- **WebSockets** - Real-time communication
- **python-multipart** - File upload handling
- **GitPython** - Git integration for publishing
- **httpx** - Async HTTP client

### Frontend Stack
- **React 19** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Material-UI (MUI)** - Component library
- **Custom Transcript Editor** - Specialized transcript editing component optimized for Deepgram responses

## External Services
- **AssemblyAI** - Primary transcription service
- **Deepgram** - Alternative transcription service  
- **OpenAI** - Additional transcription option
- **FFmpeg** - Audio compression (optional)

## Common Commands

### Development Setup
```bash
# Backend dependencies
pip install -r requirements.txt
pip install -r api/requirements.txt

# Frontend dependencies
cd web-ui && npm install
```

### Running Services
```bash
# CLI transcription
python -m src.cli.main /path/to/audio/files

# API server
python start_api.py
# or
uvicorn api.main:app --reload --port 8000

# Frontend dev server
cd web-ui && npm run dev
```

### Building
```bash
# Frontend build
cd web-ui && npm run build

# Python package
python setup.py sdist bdist_wheel
```

### Testing
```bash
# Python tests
pytest tests/

# Frontend linting
cd web-ui && npm run lint
```

## Configuration
- **config.yaml** - Main application configuration
- **.env** - API keys and environment variables
- **web-ui/vite.config.ts** - Frontend build configuration