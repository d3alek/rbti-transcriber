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
    """Serve audio files (both original and compressed)."""
    try:
        # Construct the full audio file path
        # Paths from frontend are relative to project root (e.g., "seminars/ANIMAL HUSBANDRY/compressed/file.webm")
        # Match the logic used in transcripts endpoint for consistency
        audio_path_obj = Path(audio_file_path)
        
        if len(audio_path_obj.parts) > 1 or audio_path_obj.is_absolute():
            # Path contains directory structure - resolve from current working directory (project root)
            if audio_path_obj.is_absolute():
                audio_path = audio_path_obj
            else:
                # Relative path with directory structure - resolve from current working directory
                audio_path = Path.cwd() / audio_path_obj
        else:
            # Just a filename - resolve relative to audio_directory (legacy behavior)
            audio_path = audio_dir / audio_path_obj
        
        if not audio_path.exists():
            raise HTTPException(status_code=404, detail=f"Audio file not found: {audio_path}")
        
        # Determine MIME type based on file extension
        mime_type = "audio/webm" if audio_path.suffix == ".webm" else "audio/mpeg"
        
        return FileResponse(
            path=audio_path,
            media_type=mime_type,
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
        # Remove .mp3 extension from path and convert to .webm
        base_path = audio_file_path
        if base_path.endswith('.mp3'):
            base_path = base_path[:-4]
        
        # Path structure: compressed files are in {seminar_group}/compressed/{filename}.webm
        # If path already includes compressed/, use it directly
        # Otherwise, insert compressed/ before the filename
        path_obj = Path(base_path)
        if "compressed" in path_obj.parts:
            # Path already includes compressed/ directory - use as-is
            compressed_path = audio_dir / f"{base_path}.webm"
        else:
            # Insert compressed/ before the filename
            # e.g., "seminars/ANIMAL HUSBANDRY/file" -> "seminars/ANIMAL HUSBANDRY/compressed/file.webm"
            compressed_path = audio_dir / path_obj.parent / "compressed" / f"{path_obj.name}.webm"
        
        # If exact match not found, try to find any compressed version with matching stem
        if not compressed_path.exists():
            compressed_dir = compressed_path.parent
            if compressed_dir.exists():
                # Look for any file with matching stem and _compressed.webm pattern
                matching_files = list(compressed_dir.glob(f"{path_obj.stem}_*_compressed.webm"))
                if matching_files:
                    compressed_path = matching_files[0]
        
        # REQUIRE compressed WebM file - throw error if missing
        if not compressed_path.exists():
            raise HTTPException(
                status_code=404, 
                detail=f"Compressed WebM audio file not found: {compressed_path}. Please compress the audio first."
            )
        
        # Verify it's a WebM file
        if compressed_path.suffix != ".webm":
            raise HTTPException(
                status_code=500,
                detail=f"Invalid compressed file format: expected .webm, got {compressed_path.suffix} at {compressed_path}"
            )
        
        # Always WebM
        mime_type = "audio/webm"
        
        return FileResponse(
            path=compressed_path,
            media_type=mime_type,
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