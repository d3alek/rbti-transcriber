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

### Frontend Stack (Planned)
- **React 19** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Material-UI (MUI)** - Component library
- **react-transcript-editor** - BBC's transcript editing component for word-level editing

## External Services
- **Deepgram** - Primary transcription service (Nova-3 model)
- **FFmpeg** - Audio compression for web delivery

## Common Commands

### Development Setup
```bash
# Backend dependencies
pip install -r requirements.txt
pip install -r api/requirements.txt

# Frontend dependencies (when web-ui is created)
cd web-ui && npm install

# Initialize react-transcript-editor submodule
git submodule update --init --recursive
cd react-transcript-editor && npm install
```

### Running Services
```bash
# CLI transcription
python -m src.cli.main /path/to/audio/files

# API server
python start_api.py
# or
uvicorn api.main:app --reload --port 8000

# Frontend dev server (when web-ui is created)
cd web-ui && npm run dev

# Test react-transcript-editor demo
cd react-transcript-editor && npm start
```

### Building
```bash
# Frontend build (when web-ui is created)
cd web-ui && npm run build

# Python package
python setup.py sdist bdist_wheel

# react-transcript-editor component
cd react-transcript-editor && npm run build:component
```

### Testing
```bash
# Python tests
pytest tests/

# Frontend linting (when web-ui is created)
cd web-ui && npm run lint

# Test installation
python test_installation.py
```

## Configuration
- **config.yaml** - Main application configuration
- **.env** - API keys and environment variables (Deepgram API key)
- **web-ui/vite.config.ts** - Frontend build configuration (when created)
- **react-transcript-editor/.nvmrc** - Node version specification for transcript editor