"""FastAPI backend for transcription web UI."""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import uvicorn
from pathlib import Path

from .routers import files, transcription, export, publication
from .services.websocket_manager import WebSocketManager
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

# WebSocket manager for real-time updates
websocket_manager = WebSocketManager()

# Include routers
app.include_router(files.router, prefix="/api/files", tags=["files"])
app.include_router(transcription.router, prefix="/api/transcribe", tags=["transcription"])
app.include_router(export.router, prefix="/api/export", tags=["export"])
app.include_router(publication.router, prefix="/api/publish", tags=["publication"])

# Make websocket manager available to routers
app.state.websocket_manager = websocket_manager


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Transcription Web UI API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.websocket("/ws/transcription/{job_id}")
async def websocket_transcription_endpoint(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for transcription progress updates."""
    await websocket_manager.connect_transcription(websocket, job_id)
    try:
        while True:
            # Keep connection alive and handle any client messages
            data = await websocket.receive_text()
            # Echo back for now (can be used for client-side commands)
            await websocket.send_text(f"Received: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect_transcription(websocket, job_id)


@app.websocket("/ws/files")
async def websocket_files_endpoint(websocket: WebSocket):
    """WebSocket endpoint for file list updates."""
    await websocket_manager.connect_files(websocket)
    try:
        while True:
            # Keep connection alive
            data = await websocket.receive_text()
            await websocket.send_text(f"Files connection active: {data}")
    except WebSocketDisconnect:
        websocket_manager.disconnect_files(websocket)


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )