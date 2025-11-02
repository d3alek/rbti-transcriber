"""Transcription API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Request, Query
from typing import Dict, Optional
from pathlib import Path
import uuid
import asyncio

from ..models import TranscriptionRequest, TranscriptionProgress, APIResponse, TranscriptionStatus, TranscriptionResult
from ..config import get_settings
from ..services.transcription_manager import WebTranscriptionManager
from ..services.transcription_service import TranscriptionService


router = APIRouter()

# Global transcription manager instance
transcription_manager: Optional[WebTranscriptionManager] = None


def get_transcription_manager(request: Request) -> WebTranscriptionManager:
    """Dependency to get transcription manager instance."""
    global transcription_manager
    if transcription_manager is None:
        settings = get_settings()
        transcription_manager = WebTranscriptionManager(settings)
    return transcription_manager


def get_transcription_service() -> TranscriptionService:
    """Dependency to get TranscriptionService instance."""
    settings = get_settings()
    return TranscriptionService(settings)


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


@router.post("/{filename:path}", response_model=TranscriptionResult)
async def transcribe_by_filename(
    filename: str,
    compress_audio: bool = Query(True, description="Whether to compress audio during transcription"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> TranscriptionResult:
    """
    Transcribe an audio file by filename.
    Accepts filename (e.g., 'RBTI-Animal-Husbandry-T01.mp3') and searches for it in the audio directory.
    This endpoint must come after the root POST / endpoint to avoid route conflicts.
    """
    try:
        settings = get_settings()
        audio_dir = Path(settings.audio_directory)
        
        # Search for the file in the audio directory
        audio_file = None
        for file_path in audio_dir.rglob(filename):
            if file_path.is_file() and file_path.suffix.lower() in ['.mp3', '.wav', '.m4a', '.ogg', '.flac']:
                audio_file = file_path
                break
        
        # Also try exact match in root directory
        if not audio_file:
            candidate = audio_dir / filename
            if candidate.exists() and candidate.is_file():
                audio_file = candidate
        
        if not audio_file:
            raise HTTPException(
                status_code=404,
                detail=f"Audio file '{filename}' not found in {audio_dir}"
            )
        
        # Check if transcription already exists
        status_info = service.get_transcription_status(audio_file)
        if status_info['status'] == 'completed':
            # Return existing transcription info
            return TranscriptionResult(
                success=True,
                audio_file=str(audio_file),
                processing_time=status_info.get('processing_time', 0.0),
                cache_file=status_info.get('transcription_file'),
                compressed_audio=status_info.get('compressed_audio')
            )
        
        # Perform transcription
        result = await service.transcribe_audio(audio_file, compress_audio)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to transcribe audio file: {str(e)}"
        )


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