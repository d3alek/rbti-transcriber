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
        
        # Decode the audio file path - it may include seminar group structure
        audio_path = Path(audio_file_path)
        print(f"🔍 API: Parsed audio_path: {audio_path}")
        print(f"🔍 API: Audio path stem: {audio_path.stem}")
        print(f"🔍 API: Audio directory: {audio_dir}")
        
        # Construct transcript file path preserving seminar group structure
        # Paths from frontend are already relative to project root (e.g., "seminars/ANIMAL HUSBANDRY/file.mp3")
        # Transcripts are stored at: {seminar_group}/transcriptions/{filename}.json
        # So if audio is at: seminars/ANIMAL HUSBANDRY/file.mp3
        # Transcript is at: seminars/ANIMAL HUSBANDRY/transcriptions/file.json
        
        # If path starts with directory structure (not just a filename), resolve from current working directory
        # Otherwise resolve relative to audio_directory
        if len(audio_path.parts) > 1 or audio_path.is_absolute():
            # Path contains directory structure - resolve from current working directory (project root)
            if audio_path.is_absolute():
                transcript_file = audio_path.parent / "transcriptions" / f"{audio_path.stem}.json"
            else:
                # Relative path with directory structure - resolve from current working directory
                transcript_file = Path.cwd() / audio_path.parent / "transcriptions" / f"{audio_path.stem}.json"
        else:
            # Just a filename - resolve relative to audio_directory (legacy behavior)
            transcript_file = audio_dir / "transcriptions" / f"{audio_path.stem}.json"
        
        print(f"🔍 API: Looking for transcript file: {transcript_file}")
        print(f"🔍 API: Transcript file exists: {transcript_file.exists()}")
        
        if not transcript_file.exists():
            print(f"❌ API: Transcript file not found: {transcript_file}")
            # List available files in the seminar group transcriptions directory for debugging
            seminar_transcriptions_dir = transcript_file.parent
            if seminar_transcriptions_dir.exists():
                available_files = list(seminar_transcriptions_dir.glob("*.json"))
                print(f"🔍 API: Available transcript files in directory: {available_files}")
            else:
                print(f"❌ API: Transcriptions directory doesn't exist: {seminar_transcriptions_dir}")
            raise HTTPException(status_code=404, detail="Transcript not found")
        
        # Load the transcript data
        print(f"📖 API: Loading transcript file...")
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        print(f"✅ API: Transcript loaded successfully, keys: {list(transcript_data.keys())}")
        print(f"✅ API: Transcript data size: {len(json.dumps(transcript_data))} chars")
        
        # Support multiple formats - frontend will detect and convert:
        # 1. RichWordsTranscript format (has 'words' at top-level) - return as-is
        # 2. Transcription orchestrator format (has 'result.raw_response') - return full structure for frontend to convert
        # 3. Raw Deepgram format - return as-is for frontend to convert
        if 'words' in transcript_data and isinstance(transcript_data.get('words'), list):
            # RichWordsTranscript format - return directly
            print(f"✅ API: Returning RichWordsTranscript format, words count: {len(transcript_data['words'])}")
            return transcript_data
        elif 'result' in transcript_data and 'raw_response' in transcript_data.get('result', {}):
            # Transcription orchestrator format with nested raw_response - return full structure
            # Frontend will detect result.raw_response and convert it
            print(f"✅ API: Returning transcription orchestrator format with raw_response")
            return transcript_data
        elif 'raw_response' in transcript_data and transcript_data['raw_response'].get('results'):
            # Direct raw Deepgram format - return as-is for frontend conversion
            print(f"✅ API: Returning raw Deepgram format for frontend conversion")
            return transcript_data
        elif 'result' in transcript_data:
            # Old cache format - return result portion
            print(f"✅ API: Returning result portion from old cache format")
            return transcript_data['result']
        else:
            print(f"❌ API: Invalid transcript format - expected RichWordsTranscript or raw Deepgram format")
            raise HTTPException(status_code=500, detail="Invalid transcript format")
        
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
    """
    Save RichWordsTranscript format transcript.
    Frontend always sends RichWordsTranscript format - backend just saves it to disk.
    """
    try:
        # Decode the audio file path - it may include seminar group structure
        audio_path = Path(audio_file_path)
        
        # Construct transcript file path preserving seminar group structure
        # Paths from frontend are already relative to project root
        if len(audio_path.parts) > 1 or audio_path.is_absolute():
            # Path contains directory structure - resolve from current working directory
            if audio_path.is_absolute():
                transcript_file = audio_path.parent / "transcriptions" / f"{audio_path.stem}.json"
            else:
                transcript_file = Path.cwd() / audio_path.parent / "transcriptions" / f"{audio_path.stem}.json"
        else:
            # Just a filename - resolve relative to audio_directory
            transcript_file = audio_dir / "transcriptions" / f"{audio_path.stem}.json"
        
        # Validate that we're receiving RichWordsTranscript format
        if 'words' not in corrections or not isinstance(corrections.get('words'), list):
            raise HTTPException(
                status_code=400, 
                detail="Invalid format: Expected RichWordsTranscript with 'words' array"
            )
        
        # Create backup of original if this is the first save (no corrections yet)
        # Check if original file exists and has no corrections
        if transcript_file.exists():
            backup_file = transcript_file.with_suffix('.backup.json')
            if not backup_file.exists():
                try:
                    with open(transcript_file, 'r', encoding='utf-8') as f:
                        original_data = json.load(f)
                    # Only backup if original doesn't have corrections yet
                    if not original_data.get('corrections') or original_data.get('corrections', {}).get('version', 0) == 1:
                        with open(backup_file, 'w', encoding='utf-8') as f:
                            json.dump(original_data, f, indent=2, ensure_ascii=False)
                        print(f"📦 Created backup: {backup_file}")
                except Exception as e:
                    print(f"⚠️  Warning: Could not create backup: {e}")
        else:
            # If transcript file doesn't exist, create parent directory
            transcript_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save the RichWordsTranscript directly to disk
        with open(transcript_file, 'w', encoding='utf-8') as f:
            json.dump(corrections, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved RichWordsTranscript: {transcript_file} ({len(corrections.get('words', []))} words)")
        
        return APIResponse(
            success=True,
            message="Transcript saved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save transcript: {str(e)}")


@router.get("/{audio_file_path:path}/status")
async def get_transcript_status(
    audio_file_path: str,
    audio_dir: Path = Depends(get_audio_directory)
):
    """Get transcript status for a specific audio file."""
    try:
        # Decode the audio file path - preserve seminar group structure
        audio_path = Path(audio_file_path)
        
        # Paths from frontend are already relative to project root
        if len(audio_path.parts) > 1 or audio_path.is_absolute():
            # Path contains directory structure - resolve from current working directory
            if audio_path.is_absolute():
                transcript_file = audio_path.parent / "transcriptions" / f"{audio_path.stem}.json"
            else:
                transcript_file = Path.cwd() / audio_path.parent / "transcriptions" / f"{audio_path.stem}.json"
        else:
            # Just a filename - resolve relative to audio_directory
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