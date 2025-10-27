"""WebSocket connection manager for real-time updates."""

from fastapi import WebSocket
from typing import Dict, List
import json
import asyncio


class WebSocketManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        # Connections for transcription progress updates
        self.transcription_connections: Dict[str, List[WebSocket]] = {}
        # Connections for file list updates
        self.file_connections: List[WebSocket] = []
    
    async def connect_transcription(self, websocket: WebSocket, job_id: str):
        """Connect a WebSocket for transcription updates."""
        await websocket.accept()
        if job_id not in self.transcription_connections:
            self.transcription_connections[job_id] = []
        self.transcription_connections[job_id].append(websocket)
        print(f"📡 WebSocket connected for transcription job: {job_id}")
    
    def disconnect_transcription(self, websocket: WebSocket, job_id: str):
        """Disconnect a WebSocket from transcription updates."""
        if job_id in self.transcription_connections:
            if websocket in self.transcription_connections[job_id]:
                self.transcription_connections[job_id].remove(websocket)
            if not self.transcription_connections[job_id]:
                del self.transcription_connections[job_id]
        print(f"📡 WebSocket disconnected from transcription job: {job_id}")
    
    async def connect_files(self, websocket: WebSocket):
        """Connect a WebSocket for file updates."""
        await websocket.accept()
        self.file_connections.append(websocket)
        print(f"📡 WebSocket connected for file updates")
    
    def disconnect_files(self, websocket: WebSocket):
        """Disconnect a WebSocket from file updates."""
        if websocket in self.file_connections:
            self.file_connections.remove(websocket)
        print(f"📡 WebSocket disconnected from file updates")
    
    async def broadcast_transcription_progress(self, job_id: str, progress_data: dict):
        """Broadcast transcription progress to connected clients."""
        if job_id in self.transcription_connections:
            message = json.dumps(progress_data)
            disconnected = []
            
            for websocket in self.transcription_connections[job_id]:
                try:
                    await websocket.send_text(message)
                except Exception as e:
                    print(f"❌ Error sending WebSocket message: {e}")
                    disconnected.append(websocket)
            
            # Remove disconnected websockets
            for websocket in disconnected:
                self.disconnect_transcription(websocket, job_id)
    
    async def broadcast_file_update(self, update_data: dict):
        """Broadcast file list updates to connected clients."""
        message = json.dumps(update_data)
        disconnected = []
        
        for websocket in self.file_connections:
            try:
                await websocket.send_text(message)
            except Exception as e:
                print(f"❌ Error sending WebSocket message: {e}")
                disconnected.append(websocket)
        
        # Remove disconnected websockets
        for websocket in disconnected:
            self.disconnect_files(websocket)
    
    def get_connection_stats(self) -> dict:
        """Get WebSocket connection statistics."""
        return {
            "transcription_jobs": len(self.transcription_connections),
            "total_transcription_connections": sum(len(conns) for conns in self.transcription_connections.values()),
            "file_connections": len(self.file_connections)
        }