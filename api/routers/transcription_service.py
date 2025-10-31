"""
Enhanced transcription API endpoints for the Audio Transcription Web Manager.
Implements requirements 2.1, 2.2, 2.4, 2.5 for transcription service integration.
"""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query
from typing import Dict, Any, Optional
from pathlib import Path
import hashlib
import sys

# Import the TranscriptionService
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..models import (
    TranscriptionResult,
    TranscriptionStatus,
    APIResponse,
    TranscriptionRequest
)
from ..services.transcription_service import TranscriptionService
from ..config import get_settings

router = APIRouter()


def get_transcription_service() -> TranscriptionService:
    """Dependency to get TranscriptionService instance."""
    settings = get_settings()
    return TranscriptionService(settings)


def _generate_file_id(file_path: Path) -> str:
    """Generate consistent file ID from file path and metadata."""
    file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
    return hashlib.md5(file_info.encode()).hexdigest()[:12]


def _find_audio_file_by_id(file_id: str, base_directory: Path) -> Optional[Path]:
    """Find audio file by ID in the base directory."""
    for file_path in base_directory.rglob("*.mp3"):
        if _generate_file_id(file_path) == file_id:
            return file_path
    return None


@router.post("/{audio_file_id}", response_model=TranscriptionResult)
async def transcribe_audio_file(
    audio_file_id: str,
    compress_audio: bool = Query(True, description="Whether to compress audio during transcription"),
    background_tasks: BackgroundTasks = None,
    service: TranscriptionService = Depends(get_transcription_service)
) -> TranscriptionResult:
    """
    Trigger transcription for a specific audio file.
    
    This endpoint implements requirements:
    - 2.1: Call existing Deepgram transcription system
    - 2.2: Create initial CorrectedDeepgramResponse from raw Deepgram response
    - 2.3: Add compressed audio generation during transcription process
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
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


@router.get("/{audio_file_id}/status")
async def get_transcription_status(
    audio_file_id: str,
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """
    Get transcription status for a specific audio file.
    
    This endpoint implements requirements:
    - 2.4: Status checking for transcription completion
    - 2.5: Error handling for failed transcriptions
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
            )
        
        # Get transcription status
        status_info = service.get_transcription_status(audio_file)
        
        # Add file information to response
        status_info.update({
            'audio_file_id': audio_file_id,
            'audio_file_path': str(audio_file),
            'audio_file_name': audio_file.name,
            'audio_file_size': audio_file.stat().st_size
        })
        
        return status_info
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get transcription status: {str(e)}"
        )


@router.post("/{audio_file_id}/retry", response_model=TranscriptionResult)
async def retry_transcription(
    audio_file_id: str,
    compress_audio: bool = Query(True, description="Whether to compress audio during transcription"),
    service: TranscriptionService = Depends(get_transcription_service)
) -> TranscriptionResult:
    """
    Retry transcription for a failed audio file.
    
    This endpoint implements requirements:
    - 2.5: Retry mechanisms for failed transcriptions
    - 2.1: Call existing Deepgram transcription system
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
            )
        
        # Retry transcription
        result = await service.retry_transcription(audio_file, compress_audio)
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to retry transcription: {str(e)}"
        )


@router.get("/{audio_file_id}/data")
async def get_transcription_data(
    audio_file_id: str,
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """
    Get the complete transcription data (CorrectedDeepgramResponse) for an audio file.
    
    This endpoint provides access to the full transcription data structure
    including raw Deepgram response and any corrections.
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
            )
        
        # Load transcription data
        transcription_data = service.load_corrected_deepgram_response(audio_file)
        
        if not transcription_data:
            raise HTTPException(
                status_code=404, 
                detail=f"No transcription data found for audio file: {audio_file_id}"
            )
        
        return transcription_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get transcription data: {str(e)}"
        )


@router.put("/{audio_file_id}/data", response_model=APIResponse)
async def save_transcription_data(
    audio_file_id: str,
    corrected_response: Dict[str, Any],
    service: TranscriptionService = Depends(get_transcription_service)
) -> APIResponse:
    """
    Save corrected transcription data (CorrectedDeepgramResponse) for an audio file.
    
    This endpoint allows saving manual corrections made to the transcript.
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
            )
        
        # Save corrected transcription data
        success = service.save_corrected_deepgram_response(audio_file, corrected_response)
        
        if not success:
            raise HTTPException(
                status_code=500, 
                detail="Failed to save corrected transcription data"
            )
        
        return APIResponse(
            success=True,
            message="Transcription data saved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to save transcription data: {str(e)}"
        )


@router.get("/{audio_file_id}/compressed-audio")
async def get_compressed_audio_info(
    audio_file_id: str,
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """
    Get information about compressed audio file for an audio file.
    
    This endpoint provides access to compressed audio file paths and metadata.
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
            )
        
        # Get compressed audio path
        compressed_path = service.get_compressed_audio_path(audio_file)
        
        if not compressed_path:
            return {
                'audio_file_id': audio_file_id,
                'has_compressed_version': False,
                'compressed_path': None,
                'compressed_size': None,
                'compression_ratio': None
            }
        
        # Calculate compression info
        original_size = audio_file.stat().st_size
        compressed_size = compressed_path.stat().st_size
        compression_ratio = round((1 - compressed_size / original_size) * 100, 1)
        
        return {
            'audio_file_id': audio_file_id,
            'has_compressed_version': True,
            'compressed_path': str(compressed_path),
            'compressed_size': compressed_size,
            'original_size': original_size,
            'compression_ratio': compression_ratio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get compressed audio info: {str(e)}"
        )


@router.delete("/{audio_file_id}/transcription", response_model=APIResponse)
async def delete_transcription(
    audio_file_id: str,
    service: TranscriptionService = Depends(get_transcription_service)
) -> APIResponse:
    """
    Delete transcription data for an audio file.
    
    This endpoint allows removing transcription files to force re-transcription.
    """
    try:
        # Find the audio file by ID
        settings = get_settings()
        audio_file = _find_audio_file_by_id(audio_file_id, settings.audio_directory)
        
        if not audio_file:
            raise HTTPException(
                status_code=404, 
                detail=f"Audio file not found for ID: {audio_file_id}"
            )
        
        # Get transcription file path
        transcription_path = service.get_transcription_file_path(audio_file)
        
        if transcription_path.exists():
            transcription_path.unlink()
            
            return APIResponse(
                success=True,
                message="Transcription deleted successfully"
            )
        else:
            return APIResponse(
                success=True,
                message="No transcription found to delete"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to delete transcription: {str(e)}"
        )


# Batch operations for multiple files

@router.post("/batch/status")
async def get_batch_transcription_status(
    audio_file_ids: list[str],
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Dict[str, Any]]:
    """
    Get transcription status for multiple audio files.
    
    This endpoint allows checking status of multiple files at once.
    """
    try:
        settings = get_settings()
        results = {}
        
        for file_id in audio_file_ids:
            try:
                audio_file = _find_audio_file_by_id(file_id, settings.audio_directory)
                
                if audio_file:
                    status_info = service.get_transcription_status(audio_file)
                    status_info.update({
                        'audio_file_id': file_id,
                        'audio_file_path': str(audio_file),
                        'audio_file_name': audio_file.name
                    })
                    results[file_id] = status_info
                else:
                    results[file_id] = {
                        'audio_file_id': file_id,
                        'status': 'not_found',
                        'error': f'Audio file not found for ID: {file_id}'
                    }
                    
            except Exception as e:
                results[file_id] = {
                    'audio_file_id': file_id,
                    'status': 'error',
                    'error': str(e)
                }
        
        return results
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get batch transcription status: {str(e)}"
        )


@router.get("/health")
async def transcription_service_health(
    service: TranscriptionService = Depends(get_transcription_service)
) -> Dict[str, Any]:
    """
    Health check endpoint for transcription service.
    
    This endpoint provides information about the transcription service status.
    """
    try:
        settings = get_settings()
        
        return {
            'status': 'healthy',
            'service': 'transcription_service',
            'audio_directory': str(settings.audio_directory),
            'config_file': str(settings.config_file),
            'timestamp': str(Path(__file__).stat().st_mtime)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Transcription service health check failed: {str(e)}"
        )