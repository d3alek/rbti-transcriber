"""Publication API endpoints for GitHub Pages integration."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any

from ..models import PublicationRequest, PublicationStatus, APIResponse
from ..config import get_settings
from ..services.github_publisher import GitHubPublisher

router = APIRouter()


def get_github_publisher() -> GitHubPublisher:
    """Dependency to get GitHub publisher instance."""
    settings = get_settings()
    return GitHubPublisher(settings)


@router.post("/{file_id}", response_model=APIResponse)
async def publish_transcription(
    file_id: str,
    request: PublicationRequest,
    publisher: GitHubPublisher = Depends(get_github_publisher)
) -> APIResponse:
    """Publish a transcription to GitHub Pages."""
    try:
        publication_status = await publisher.publish_transcription(file_id, request)
        
        return APIResponse(
            success=True,
            message="Transcription published successfully",
            data=publication_status.dict()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to publish transcription: {str(e)}")


@router.delete("/{file_id}", response_model=APIResponse)
async def unpublish_transcription(
    file_id: str,
    publisher: GitHubPublisher = Depends(get_github_publisher)
) -> APIResponse:
    """Remove a transcription from GitHub Pages."""
    try:
        success = await publisher.unpublish_transcription(file_id)
        if not success:
            raise HTTPException(status_code=404, detail="Published transcription not found")
        
        return APIResponse(
            success=True,
            message="Transcription unpublished successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to unpublish transcription: {str(e)}")


@router.get("/status", response_model=Dict[str, Any])
async def get_publication_status(
    publisher: GitHubPublisher = Depends(get_github_publisher)
) -> Dict[str, Any]:
    """Get overall publication system status."""
    try:
        return await publisher.get_system_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get publication status: {str(e)}")


@router.get("/{file_id}/status", response_model=PublicationStatus)
async def get_file_publication_status(
    file_id: str,
    publisher: GitHubPublisher = Depends(get_github_publisher)
) -> PublicationStatus:
    """Get publication status for a specific file."""
    try:
        status = await publisher.get_file_publication_status(file_id)
        if not status:
            # Return default unpublished status
            return PublicationStatus(is_published=False)
        
        return status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get file publication status: {str(e)}")


@router.get("/list", response_model=List[Dict[str, Any]])
async def list_published_transcriptions(
    publisher: GitHubPublisher = Depends(get_github_publisher)
) -> List[Dict[str, Any]]:
    """List all published transcriptions."""
    try:
        return await publisher.list_published_transcriptions()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list published transcriptions: {str(e)}")


@router.post("/rebuild-index", response_model=APIResponse)
async def rebuild_index(
    publisher: GitHubPublisher = Depends(get_github_publisher)
) -> APIResponse:
    """Rebuild the GitHub Pages index."""
    try:
        await publisher.rebuild_index()
        
        return APIResponse(
            success=True,
            message="Index rebuilt successfully"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to rebuild index: {str(e)}")