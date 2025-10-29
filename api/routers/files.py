"""File management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from typing import List, Optional
from pathlib import Path
import hashlib
from datetime import datetime
import sys

# Import audio processor for compression
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.audio_processor import AudioProcessor

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
    compressed: bool = Query(default=True, description="Serve compressed audio for better web performance"),
    file_manager: AudioFileManager = Depends(get_file_manager)
):
    """Serve the audio file for playback, with optional compression for web performance."""
    try:
        file_info = await file_manager.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")
        
        original_audio_path = Path(file_info.path)
        if not original_audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found on disk")
        
        audio_path_to_serve = original_audio_path
        
        # ALWAYS serve compressed audio for web performance
        if compressed:
            try:
                # Initialize audio processor with aggressive compression settings
                compressed_dir = original_audio_path.parent / "compressed"
                audio_processor = AudioProcessor(compressed_dir)
                
                # Get the compressed file path
                compressed_path = audio_processor._get_compressed_cache_path(original_audio_path)
                
                if compressed_path.exists():
                    # Use existing compressed file
                    audio_path_to_serve = compressed_path
                    print(f"🎵 Serving cached compressed audio: {compressed_path.name}")
                else:
                    # Always compress for web, regardless of original bitrate
                    print(f"🗜️ Compressing audio for web playback (target: 32kbps)...")
                    compressed_path = audio_processor.compress_audio(
                        original_audio_path, 
                        force=True,  # Force compression even if already low bitrate
                        target_size_mb=5.0  # Aggressive size limit for web
                    )
                    audio_path_to_serve = compressed_path
                    
                    # Log compression stats
                    original_size = original_audio_path.stat().st_size / (1024 * 1024)
                    compressed_size = compressed_path.stat().st_size / (1024 * 1024)
                    reduction = ((original_size - compressed_size) / original_size) * 100
                    print(f"✅ Compressed: {original_size:.1f}MB → {compressed_size:.1f}MB ({reduction:.1f}% reduction)")
                    
            except Exception as compression_error:
                print(f"⚠️ Compression failed, serving original: {compression_error}")
                # Fall back to original file if compression fails
                audio_path_to_serve = original_audio_path
        
        return FileResponse(
            path=audio_path_to_serve,
            media_type="audio/mpeg",
            filename=audio_path_to_serve.name,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Accept-Ranges": "bytes"  # Enable range requests for better streaming
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve audio file: {str(e)}")


@router.post("/compress-all", response_model=APIResponse)
async def compress_all_audio_files(
    file_manager: AudioFileManager = Depends(get_file_manager)
) -> APIResponse:
    """Pre-compress all audio files for better web performance."""
    try:
        files = await file_manager.list_files()
        compressed_count = 0
        
        for file_info in files:
            try:
                original_path = Path(file_info.path)
                if not original_path.exists():
                    continue
                
                # Initialize audio processor
                compressed_dir = original_path.parent / "compressed"
                audio_processor = AudioProcessor(compressed_dir)
                
                # Check if compressed version already exists
                compressed_path = audio_processor._get_compressed_cache_path(original_path)
                
                if not compressed_path.exists():
                    print(f"🗜️ Pre-compressing {original_path.name}...")
                    audio_processor.compress_audio(
                        original_path, 
                        force=True,
                        target_size_mb=5.0
                    )
                    compressed_count += 1
                    
            except Exception as e:
                print(f"⚠️ Failed to compress {file_info.name}: {e}")
                continue
        
        return APIResponse(
            success=True,
            message=f"Pre-compressed {compressed_count} audio files for web performance",
            data={"compressed_count": compressed_count, "total_files": len(files)}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compress audio files: {str(e)}")


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