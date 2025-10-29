"""
Transcript Version Management API Routes

Handles API endpoints for managing transcript versions, including
loading, saving, and switching between different versions.
"""

from fastapi import APIRouter, HTTPException, Depends, Path, Query
from typing import List, Optional
import logging

from ..models import (
    DeepgramVersion, DeepgramResponse, VersionSaveRequest,
    VersionListResponse, TranscriptLoadResponse, ParagraphData,
    ParagraphUpdateRequest, APIResponse, ErrorResponse, ValidationResult
)
from ..services import DeepgramVersionManager, TranscriptProcessor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/transcripts", tags=["transcript-versions"])

# Dependency to get version manager
def get_version_manager() -> DeepgramVersionManager:
    """Get version manager instance."""
    return DeepgramVersionManager()

# Dependency to get transcript processor
def get_transcript_processor() -> TranscriptProcessor:
    """Get transcript processor instance."""
    return TranscriptProcessor()


@router.get("/{audio_hash}/versions", response_model=VersionListResponse)
async def list_versions(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager)
):
    """
    List all available versions for a transcript.
    
    Args:
        audio_hash: Hash identifier for the audio file
        version_manager: Version manager service
        
    Returns:
        List of available versions with metadata
    """
    try:
        # Reconstruct audio file path from hash (simplified)
        audio_file = f"audio_{audio_hash}"
        
        # Load versions
        versions = version_manager.load_versions(audio_file)
        
        # Convert to version info
        version_infos = []
        for version in versions:
            version_infos.append({
                "version": version.version,
                "filename": version.filename,
                "timestamp": version.timestamp,
                "changes": version.changes,
                "file_size": 0  # TODO: Calculate actual file size
            })
        
        # Determine current version (latest)
        current_version = max([v.version for v in versions]) if versions else 0
        
        return VersionListResponse(
            versions=version_infos,
            current_version=current_version
        )
        
    except Exception as e:
        logger.error(f"Error listing versions for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list versions: {str(e)}")


@router.post("/{audio_hash}/versions", response_model=APIResponse)
async def save_version(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    request: VersionSaveRequest = ...,
    version_manager: DeepgramVersionManager = Depends(get_version_manager)
):
    """
    Save a new version of a transcript.
    
    Args:
        audio_hash: Hash identifier for the audio file
        request: Version save request with changes and response data
        version_manager: Version manager service
        
    Returns:
        Success response with version filename
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Validate the Deepgram response structure
        processor = TranscriptProcessor()
        if not processor.validate_response_structure(request.response.dict()):
            raise HTTPException(
                status_code=400, 
                detail="Invalid Deepgram response structure"
            )
        
        # Save the version
        filename = version_manager.save_version(
            audio_file=audio_file,
            response=request.response,
            changes=request.changes
        )
        
        return APIResponse(
            success=True,
            message=f"Version saved successfully as {filename}",
            data={"filename": filename}
        )
        
    except ValueError as e:
        logger.error(f"Validation error saving version for {audio_hash}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error saving version for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save version: {str(e)}")


@router.get("/{audio_hash}/versions/{version_id}", response_model=TranscriptLoadResponse)
async def load_version(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    version_id: int = Path(..., description="Version number to load"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager),
    processor: TranscriptProcessor = Depends(get_transcript_processor)
):
    """
    Load a specific version of a transcript.
    
    Args:
        audio_hash: Hash identifier for the audio file
        version_id: Version number to load
        version_manager: Version manager service
        processor: Transcript processor service
        
    Returns:
        Transcript data with paragraphs and metadata
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Load the specific version
        response = version_manager.get_version(audio_file, version_id)
        
        if response is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Version {version_id} not found"
            )
        
        # Extract paragraphs from the response
        paragraphs = processor.extract_paragraphs(response)
        
        # Calculate overall confidence
        total_confidence = 0.0
        confidence_count = 0
        audio_duration = 0.0
        
        for paragraph in paragraphs:
            total_confidence += paragraph.confidence
            confidence_count += 1
            audio_duration = max(audio_duration, paragraph.end_time)
        
        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        return TranscriptLoadResponse(
            version=version_id,
            paragraphs=paragraphs,
            audio_duration=audio_duration,
            confidence=avg_confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading version {version_id} for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load version: {str(e)}")


@router.delete("/{audio_hash}/versions/{version_id}", response_model=APIResponse)
async def delete_version(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    version_id: int = Path(..., description="Version number to delete"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager)
):
    """
    Delete a specific version of a transcript.
    
    Args:
        audio_hash: Hash identifier for the audio file
        version_id: Version number to delete
        version_manager: Version manager service
        
    Returns:
        Success response
    """
    try:
        # Prevent deletion of version 0 (original)
        if version_id == 0:
            raise HTTPException(
                status_code=400, 
                detail="Cannot delete original version (version 0)"
            )
        
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Delete the version
        success = version_manager.delete_version(audio_file, version_id)
        
        if not success:
            raise HTTPException(
                status_code=404, 
                detail=f"Version {version_id} not found or could not be deleted"
            )
        
        return APIResponse(
            success=True,
            message=f"Version {version_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting version {version_id} for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete version: {str(e)}")


@router.get("/{audio_hash}/versions/latest", response_model=TranscriptLoadResponse)
async def load_latest_version(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager),
    processor: TranscriptProcessor = Depends(get_transcript_processor)
):
    """
    Load the latest version of a transcript.
    
    Args:
        audio_hash: Hash identifier for the audio file
        version_manager: Version manager service
        processor: Transcript processor service
        
    Returns:
        Latest transcript data with paragraphs and metadata
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Load the latest version
        response = version_manager.get_latest_version(audio_file)
        
        if response is None:
            raise HTTPException(
                status_code=404, 
                detail="No versions found for this transcript"
            )
        
        # Extract paragraphs from the response
        paragraphs = processor.extract_paragraphs(response)
        
        # Calculate overall confidence and duration
        total_confidence = 0.0
        confidence_count = 0
        audio_duration = 0.0
        
        for paragraph in paragraphs:
            total_confidence += paragraph.confidence
            confidence_count += 1
            audio_duration = max(audio_duration, paragraph.end_time)
        
        avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
        
        # Get version number
        versions = version_manager.load_versions(audio_file)
        latest_version = max([v.version for v in versions]) if versions else 0
        
        return TranscriptLoadResponse(
            version=latest_version,
            paragraphs=paragraphs,
            audio_duration=audio_duration,
            confidence=avg_confidence
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error loading latest version for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to load latest version: {str(e)}")


@router.post("/{audio_hash}/initialize", response_model=APIResponse)
async def initialize_from_cache(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager)
):
    """
    Initialize version 0 from existing cache file.
    
    Args:
        audio_hash: Hash identifier for the audio file
        version_manager: Version manager service
        
    Returns:
        Success response if initialized
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Try to initialize from cache
        filename = version_manager.initialize_from_cache(audio_file)
        
        if filename is None:
            raise HTTPException(
                status_code=404, 
                detail="No cache file found or version 0 already exists"
            )
        
        return APIResponse(
            success=True,
            message=f"Initialized version 0 from cache as {filename}",
            data={"filename": filename}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error initializing from cache for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to initialize from cache: {str(e)}")


@router.get("/{audio_hash}/storage-info")
async def get_storage_info(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager)
):
    """
    Get storage information for a transcript's versions.
    
    Args:
        audio_hash: Hash identifier for the audio file
        version_manager: Version manager service
        
    Returns:
        Storage information including file count and sizes
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Get storage info
        storage_info = version_manager.get_storage_info(audio_file)
        
        return APIResponse(
            success=True,
            message="Storage information retrieved successfully",
            data=storage_info
        )
        
    except Exception as e:
        logger.error(f"Error getting storage info for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get storage info: {str(e)}")


# Paragraph Editing Endpoints

@router.put("/{audio_hash}/paragraphs/{paragraph_id}", response_model=APIResponse)
async def update_paragraph(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    paragraph_id: str = Path(..., description="Paragraph ID to update"),
    request: ParagraphUpdateRequest = ...,
    version_manager: DeepgramVersionManager = Depends(get_version_manager),
    processor: TranscriptProcessor = Depends(get_transcript_processor)
):
    """
    Update paragraph text in the current working version.
    
    Note: This updates the in-memory version. Use save_version to persist changes.
    
    Args:
        audio_hash: Hash identifier for the audio file
        paragraph_id: ID of paragraph to update
        request: Update request with new text
        version_manager: Version manager service
        processor: Transcript processor service
        
    Returns:
        Success response with updated paragraph data
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Load the latest version as working copy
        response = version_manager.get_latest_version(audio_file)
        
        if response is None:
            raise HTTPException(
                status_code=404, 
                detail="No versions found for this transcript"
            )
        
        # Update the paragraph text
        updated_response = processor.update_paragraph_text(
            response=response,
            paragraph_id=paragraph_id,
            new_text=request.new_text
        )
        
        # Extract updated paragraphs
        paragraphs = processor.extract_paragraphs(updated_response)
        
        # Find the updated paragraph
        updated_paragraph = None
        for paragraph in paragraphs:
            if paragraph.id == paragraph_id:
                updated_paragraph = paragraph
                break
        
        if updated_paragraph is None:
            raise HTTPException(
                status_code=404,
                detail=f"Paragraph {paragraph_id} not found after update"
            )
        
        return APIResponse(
            success=True,
            message=f"Paragraph {paragraph_id} updated successfully",
            data={
                "paragraph": updated_paragraph.dict(),
                "updated_response": updated_response.dict()
            }
        )
        
    except ValueError as e:
        logger.error(f"Validation error updating paragraph {paragraph_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating paragraph {paragraph_id} for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update paragraph: {str(e)}")


@router.get("/{audio_hash}/paragraphs/{paragraph_id}", response_model=APIResponse)
async def get_paragraph(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    paragraph_id: str = Path(..., description="Paragraph ID to retrieve"),
    version_id: Optional[int] = Query(None, description="Version to load (latest if not specified)"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager),
    processor: TranscriptProcessor = Depends(get_transcript_processor)
):
    """
    Get a specific paragraph from a transcript version.
    
    Args:
        audio_hash: Hash identifier for the audio file
        paragraph_id: ID of paragraph to retrieve
        version_id: Optional version number (uses latest if not specified)
        version_manager: Version manager service
        processor: Transcript processor service
        
    Returns:
        Paragraph data
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Load the specified or latest version
        if version_id is not None:
            response = version_manager.get_version(audio_file, version_id)
        else:
            response = version_manager.get_latest_version(audio_file)
        
        if response is None:
            raise HTTPException(
                status_code=404, 
                detail="Version not found"
            )
        
        # Extract paragraphs
        paragraphs = processor.extract_paragraphs(response)
        
        # Find the requested paragraph
        target_paragraph = None
        for paragraph in paragraphs:
            if paragraph.id == paragraph_id:
                target_paragraph = paragraph
                break
        
        if target_paragraph is None:
            raise HTTPException(
                status_code=404,
                detail=f"Paragraph {paragraph_id} not found"
            )
        
        return APIResponse(
            success=True,
            message=f"Paragraph {paragraph_id} retrieved successfully",
            data={"paragraph": target_paragraph.dict()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting paragraph {paragraph_id} for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get paragraph: {str(e)}")


@router.get("/{audio_hash}/words/at-time/{time}", response_model=APIResponse)
async def get_word_at_time(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    time: float = Path(..., description="Time in seconds"),
    version_id: Optional[int] = Query(None, description="Version to use (latest if not specified)"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager),
    processor: TranscriptProcessor = Depends(get_transcript_processor)
):
    """
    Get the word being spoken at a specific time.
    
    Args:
        audio_hash: Hash identifier for the audio file
        time: Time in seconds
        version_id: Optional version number (uses latest if not specified)
        version_manager: Version manager service
        processor: Transcript processor service
        
    Returns:
        Word data at the specified time
    """
    try:
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Load the specified or latest version
        if version_id is not None:
            response = version_manager.get_version(audio_file, version_id)
        else:
            response = version_manager.get_latest_version(audio_file)
        
        if response is None:
            raise HTTPException(
                status_code=404, 
                detail="Version not found"
            )
        
        # Find word at time
        word = processor.find_word_at_time(response, time)
        
        if word is None:
            return APIResponse(
                success=True,
                message=f"No word found at time {time}",
                data={"word": None}
            )
        
        return APIResponse(
            success=True,
            message=f"Word found at time {time}",
            data={"word": word.dict()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting word at time {time} for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get word at time: {str(e)}")


@router.get("/{audio_hash}/words/in-range", response_model=APIResponse)
async def get_words_in_range(
    audio_hash: str = Path(..., description="Audio file hash identifier"),
    start_time: float = Query(..., description="Start time in seconds"),
    end_time: float = Query(..., description="End time in seconds"),
    version_id: Optional[int] = Query(None, description="Version to use (latest if not specified)"),
    version_manager: DeepgramVersionManager = Depends(get_version_manager),
    processor: TranscriptProcessor = Depends(get_transcript_processor)
):
    """
    Get all words within a specific time range.
    
    Args:
        audio_hash: Hash identifier for the audio file
        start_time: Start time in seconds
        end_time: End time in seconds
        version_id: Optional version number (uses latest if not specified)
        version_manager: Version manager service
        processor: Transcript processor service
        
    Returns:
        List of words in the time range
    """
    try:
        if start_time >= end_time:
            raise HTTPException(
                status_code=400,
                detail="Start time must be less than end time"
            )
        
        # Reconstruct audio file path from hash
        audio_file = f"audio_{audio_hash}"
        
        # Load the specified or latest version
        if version_id is not None:
            response = version_manager.get_version(audio_file, version_id)
        else:
            response = version_manager.get_latest_version(audio_file)
        
        if response is None:
            raise HTTPException(
                status_code=404, 
                detail="Version not found"
            )
        
        # Get words in range
        words = processor.get_words_in_time_range(response, start_time, end_time)
        
        return APIResponse(
            success=True,
            message=f"Found {len(words)} words in time range {start_time}-{end_time}",
            data={
                "words": [word.dict() for word in words],
                "count": len(words)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting words in range for {audio_hash}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get words in range: {str(e)}")