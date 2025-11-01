"""FastAPI backend for transcription web UI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from .routers import files, transcription, directory_scanner, transcription_service, transcripts, audio
from .config import get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    print(f"🚀 Starting Transcription Web UI API")
    print(f"📁 Audio Directory: {settings.audio_directory}")
    print(f"🔧 Config File: {settings.config_file}")
    
    yield
    
    # Shutdown
    print("🛑 Shutting down Transcription Web UI API")


app = FastAPI(
    title="Transcription Web UI API",
    description="Backend API for the audio transcription web interface",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(transcription.router, prefix="/api/transcribe", tags=["transcription"])
app.include_router(directory_scanner.router, prefix="/api/directory", tags=["directory-scanner"])
app.include_router(transcription_service.router, prefix="/api/transcription", tags=["transcription-service"])
app.include_router(transcripts.router, prefix="/api/transcripts", tags=["transcripts"])
app.include_router(audio.router, prefix="/api/audio", tags=["audio"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Transcription Web UI API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}





if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug",  # More verbose logging
        access_log=True
    )