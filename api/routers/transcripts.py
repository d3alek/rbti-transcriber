"""Transcript management API endpoints."""

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import FileResponse
from typing import Optional
from pathlib import Path
import json

from ..models import APIResponse
from ..config import get_settings

router = APIRouter()


def get_audio_directory() -> Path:
    """Dependency to get audio directory path."""
    settings = get_settings()
    return Path(settings.audio_directory)


@router.get("/{audio_file_path:path}")
async def get_transcript(
    audio_file_path: str,
    audio_dir: Path = Depends(get_audio_directory)
):
    """Get transcript data for a specific audio file."""
    try:
        print(f"🔍 API: get_transcript called with path: {audio_file_path}")
        
        # Decode the audio file path and construct transcript file path
        audio_path = Path(audio_file_path)
        print(f"🔍 API: Parsed audio_path: {audio_path}")
        print(f"🔍 API: Audio path stem: {audio_path.stem}")
        print(f"🔍 API: Audio directory: {audio_dir}")
        
        # The transcript JSON file is in the transcriptions directory with the same name but .json extension
        transcript_file = audio_dir / "transcriptions" / f"{audio_path.stem}.json"
        print(f"🔍 API: Looking for transcript file: {transcript_file}")
        print(f"🔍 API: Transcript file exists: {transcript_file.exists()}")
        
        if not transcript_file.exists():
            print(f"❌ API: Transcript file not found: {transcript_file}")
            # List available files for debugging
            transcriptions_dir = audio_dir / "transcriptions"
            if transcriptions_dir.exists():
                available_files = list(transcriptions_dir.glob("*.json"))
                print(f"🔍 API: Available transcript files: {available_files}")
            else:
                print(f"❌ API: Transcriptions directory doesn't exist: {transcriptions_dir}")
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Load the transcript data
        print(f"📖 API: Loading transcript file...")
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        print(f"✅ API: Transcript loaded successfully, keys: {list(transcript_data.keys())}")
        print(f"✅ API: Transcript data size: {len(json.dumps(transcript_data))} chars")
        
        # Return just the result portion which contains the CorrectedDeepgramResponse
        if 'result' in transcript_data:
            print(f"✅ API: Returning result portion, keys: {list(transcript_data['result'].keys())}")
            return transcript_data['result']
        else:
            print(f"❌ API: No 'result' key found in transcript data")
            raise HTTPException(status_code=500, detail="Invalid transcript format - missing 'result' key")
        
        return transcript_data
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"💥 API: Exception in get_transcript: {e}")
        print(f"💥 API: Exception type: {type(e)}")
        import traceback
        print(f"💥 API: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to get transcript: {str(e)}")


@router.put("/{audio_file_path:path}/corrections", response_model=APIResponse)
async def save_transcript_corrections(
    audio_file_path: str,
    corrections: dict,
    audio_dir: Path = Depends(get_audio_directory)
) -> APIResponse:
    """Save transcript corrections for a specific audio file."""
    try:
        # Decode the audio file path and construct transcript file path
        audio_path = Path(audio_file_path)
        transcript_file = audio_dir / "transcriptions" / f"{audio_path.stem}.json"
        
        if not transcript_file.exists():
            raise HTTPException(status_code=404, detail="Original transcript not found")
        
        # Create backup of original if this is the first correction
        if not corrections.get('corrections'):
            backup_file = transcript_file.with_suffix('.backup.json')
            if not backup_file.exists():
                # Load original and save as backup
                with open(transcript_file, 'r', encoding='utf-8') as f:
                    original_data = json.load(f)
                with open(backup_file, 'w', encoding='utf-8') as f:
                    json.dump(original_data, f, indent=2, ensure_ascii=False)
        
        # Save the corrected transcript data
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(corrections, f, indent=2, ensure_ascii=False)
        
        return APIResponse(
            success=True,
            message="Transcript corrections saved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save corrections: {str(e)}")


@router.get("/{audio_file_path:path}/status")
async def get_transcript_status(
    audio_file_path: str,
    audio_dir: Path = Depends(get_audio_directory)
):
    """Get transcript status for a specific audio file."""
    try:
        # Decode the audio file path and construct transcript file path
        audio_path = Path(audio_file_path)
        transcript_file = audio_dir / "transcriptions" / f"{audio_path.stem}.json"
        
        if not transcript_file.exists():
            return {
                "exists": False,
                "status": "none",
                "message": "No transcript found"
            }
        
        # Load the transcript data to check for corrections
        try:
            with open(transcript_file, 'r', encoding='utf-8') as f:
                transcript_data = json.load(f)
            
            corrections = transcript_data.get('corrections')
            
            return {
                "exists": True,
                "status": "completed",
                "has_corrections": corrections is not None,
                "correction_version": corrections.get('version', 0) if corrections else 0,
                "last_modified": transcript_file.stat().st_mtime,
                "file_size": transcript_file.stat().st_size
            }
            
        except json.JSONDecodeError:
            return {
                "exists": True,
                "status": "corrupted",
                "message": "Transcript file is corrupted"
            }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get transcript status: {str(e)}")


@router.delete("/{audio_file_path:path}", response_model=APIResponse)
async def delete_transcript(
    audio_file_path: str,
    audio_dir: Path = Depends(get_audio_directory)
) -> APIResponse:
    """Delete transcript data for a specific audio file."""
    try:
        # Decode the audio file path and construct transcript file path
        audio_path = Path(audio_file_path)
        transcript_file = audio_dir / "transcriptions" / f"{audio_path.stem}.json"
        
        if not transcript_file.exists():
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Delete the transcript file
        transcript_file.unlink()
        
        # Also delete backup if it exists
        backup_file = transcript_file.with_suffix('.backup.json')
        if backup_file.exists():
            backup_file.unlink()
        
        return APIResponse(
            success=True,
            message="Transcript deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete transcript: {str(e)}")