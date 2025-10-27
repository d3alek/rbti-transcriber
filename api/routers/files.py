"""File management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path
import hashlib
from datetime import datetime

from ..models import AudioFileInfo, TranscriptionStatus, APIResponse, TranscriptionData
from ..config import get_settings
from ..services.file_manager import AudioFileManager

router = APIRouter()


def get_file_manager() -> AudioFileManager:
    """Dependency to get file manager instance."""
    settings = get_settings()
    return AudioFileManager(settings.audio_directory)


@router.get("/", response_model=List[AudioFileInfo])
async def list_files(
    file_manager: AudioFileManager = Depends(get_file_manager)
) -> List[AudioFileInfo]:
    """List all MP3 files in the audio directory."""
    try:
        files = await file_manager.list_files()
        return files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list files: {str(e)}")


@router.post("/scan", response_model=APIResponse)
async def scan_files(
    file_manager: AudioFileManager = Depends(get_file_manager)
) -> APIResponse:
    """Rescan the audio directory for new files."""
    try:
        count = await file_manager.rescan_directory()
        return APIResponse(
            success=True,
            message=f"Scanned directory, found {count} files",
            data={"file_count": count}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan files: {str(e)}")


@router.get("/{file_id}/info", response_model=AudioFileInfo)
async def get_file_info(
    file_id: str,
    file_manager: AudioFileManager = Depends(get_file_manager)
) -> AudioFileInfo:
    """Get detailed information about a specific file."""
    try:
        file_info = await file_manager.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        return file_info
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file info: {str(e)}")


@router.get("/{file_id}/transcription")
async def get_transcription(
    file_id: str,
    file_manager: AudioFileManager = Depends(get_file_manager)
):
    """Get transcription data for a specific file."""
    try:
        transcription = await file_manager.get_transcription_data(file_id)
        if not transcription:
            raise HTTPException(status_code=404, detail="Transcription not found")
        return transcription
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcription: {str(e)}")


@router.put("/{file_id}/transcription", response_model=APIResponse)
async def save_transcription(
    file_id: str,
    transcription_data: TranscriptionData,
    file_manager: AudioFileManager = Depends(get_file_manager)
) -> APIResponse:
    """Save transcription data for a specific file."""
    try:
        success = await file_manager.save_transcription_data(file_id, transcription_data)
        if not success:
            raise HTTPException(status_code=404, detail="File not found")
        
        return APIResponse(
            success=True,
            message="Transcription saved successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save transcription: {str(e)}")


@router.get("/{file_id}/audio")
async def get_audio_file(
    file_id: str,
    file_manager: AudioFileManager = Depends(get_file_manager)
):
    """Serve the audio file for playback."""
    try:
        file_info = await file_manager.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        audio_path = Path(file_info.path)
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found on disk")
        
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            filename=audio_path.name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve audio file: {str(e)}")


@router.delete("/{file_id}/transcription", response_model=APIResponse)
async def delete_transcription(
    file_id: str,
    file_manager: AudioFileManager = Depends(get_file_manager)
) -> APIResponse:
    """Delete transcription data for a specific file."""
    try:
        success = await file_manager.delete_transcription(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Transcription not found")
        
        return APIResponse(
            success=True,
            message="Transcription deleted successfully"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete transcription: {str(e)}")