"""Transcription API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request
from typing import Dict, Optional
import uuid
import asyncio

from ..models import TranscriptionRequest, TranscriptionProgress, APIResponse, TranscriptionStatus
from ..config import get_settings
from ..services.transcription_manager import WebTranscriptionManager
from ..services.websocket_manager import WebSocketManager

router = APIRouter()

# Global transcription manager instance
transcription_manager: Optional[WebTranscriptionManager] = None


def get_transcription_manager(request: Request) -> WebTranscriptionManager:
    """Dependency to get transcription manager instance."""
    global transcription_manager
    if transcription_manager is None:
        settings = get_settings()
        websocket_manager = getattr(request.app.state, 'websocket_manager', None)
        transcription_manager = WebTranscriptionManager(settings, websocket_manager)
    return transcription_manager


@router.post("/", response_model=APIResponse)
async def start_transcription(
    request: TranscriptionRequest,
    background_tasks: BackgroundTasks,
    manager: WebTranscriptionManager = Depends(get_transcription_manager)
) -> APIResponse:
    """Start a new transcription job."""
    try:
        job_id = await manager.start_transcription(request, background_tasks)
        
        return APIResponse(
            success=True,
            message="Transcription job started",
            data={"job_id": job_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start transcription: {str(e)}")


@router.get("/{job_id}/status", response_model=TranscriptionProgress)
async def get_transcription_status(
    job_id: str,
    manager: WebTranscriptionManager = Depends(get_transcription_manager)
) -> TranscriptionProgress:
    """Get the status of a transcription job."""
    try:
        status = await manager.get_job_status(job_id)
        if not status:
            raise HTTPException(status_code=404, detail="Job not found")
        
        return status
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get job status: {str(e)}")


@router.post("/{job_id}/cancel", response_model=APIResponse)
async def cancel_transcription(
    job_id: str,
    manager: WebTranscriptionManager = Depends(get_transcription_manager)
) -> APIResponse:
    """Cancel a transcription job."""
    try:
        success = await manager.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        
        return APIResponse(
            success=True,
            message="Transcription job cancelled"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cancel job: {str(e)}")


@router.get("/jobs", response_model=Dict[str, TranscriptionProgress])
async def list_active_jobs(
    manager: WebTranscriptionManager = Depends(get_transcription_manager)
) -> Dict[str, TranscriptionProgress]:
    """List all active transcription jobs."""
    try:
        return await manager.list_active_jobs()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list jobs: {str(e)}")


@router.get("/queue/status")
async def get_queue_status(
    manager: WebTranscriptionManager = Depends(get_transcription_manager)
) -> dict:
    """Get transcription queue status."""
    try:
        return await manager.get_queue_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get queue status: {str(e)}")