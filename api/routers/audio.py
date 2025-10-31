"""Audio file serving endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from pathlib import Path

from ..config import get_settings

router = APIRouter()


def get_audio_directory() -> Path:
    """Dependency to get audio directory path."""
    settings = get_settings()
    return Path(settings.audio_directory)


@router.get("/{audio_file_path:path}")
async def get_audio_file(
    audio_file_path: str,
    audio_dir: Path = Depends(get_audio_directory)
):
    """Serve the original audio file."""
    try:
        # Construct the full audio file path
        audio_path = audio_dir / audio_file_path
        
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail="Audio file not found")
        
        return FileResponse(
            path=audio_path,
            media_type="audio/mpeg",
            filename=audio_path.name,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Accept-Ranges": "bytes"  # Enable range requests for better streaming
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve audio file: {str(e)}")


@router.get("/compressed/{audio_file_path:path}")
async def get_compressed_audio_file(
    audio_file_path: str,
    audio_dir: Path = Depends(get_audio_directory)
):
    """Serve the compressed audio file for web playback."""
    try:
        # Construct the compressed audio file path
        # Remove .mp3 extension from path and add it back to ensure consistency
        base_path = audio_file_path
        if base_path.endswith('.mp3'):
            base_path = base_path[:-4]
        
        compressed_path = audio_dir / "compressed" / f"{base_path}.mp3"
        
        if not compressed_path.exists():
            # Fall back to original file if compressed version doesn't exist
            original_path = audio_dir / f"{base_path}.mp3"
            if not original_path.exists():
                raise HTTPException(status_code=404, detail="Audio file not found")
            compressed_path = original_path
        
        return FileResponse(
            path=compressed_path,
            media_type="audio/mpeg",
            filename=compressed_path.name,
            headers={
                "Cache-Control": "public, max-age=3600",  # Cache for 1 hour
                "Accept-Ranges": "bytes"  # Enable range requests for better streaming
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to serve compressed audio file: {str(e)}")