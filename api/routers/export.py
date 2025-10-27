"""Export API endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from typing import Optional
import tempfile
from pathlib import Path

from ..models import ExportRequest, APIResponse
from ..config import get_settings
from ..services.export_manager import ExportManager

router = APIRouter()


def get_export_manager() -> ExportManager:
    """Dependency to get export manager instance."""
    settings = get_settings()
    return ExportManager(settings)


@router.post("/{file_id}", response_model=APIResponse)
async def export_transcription(
    file_id: str,
    request: ExportRequest,
    export_manager: ExportManager = Depends(get_export_manager)
) -> APIResponse:
    """Export a transcription in the specified format."""
    try:
        export_id = await export_manager.create_export(file_id, request.format)
        
        return APIResponse(
            success=True,
            message="Export created successfully",
            data={"export_id": export_id}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create export: {str(e)}")


@router.get("/{export_id}/download")
async def download_export(
    export_id: str,
    export_manager: ExportManager = Depends(get_export_manager)
):
    """Download an exported transcription file."""
    try:
        file_path, filename, media_type = await export_manager.get_export_file(export_id)
        
        if not file_path or not file_path.exists():
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type=media_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to download export: {str(e)}")


@router.delete("/{export_id}", response_model=APIResponse)
async def delete_export(
    export_id: str,
    export_manager: ExportManager = Depends(get_export_manager)
) -> APIResponse:
    """Delete an export file."""
    try:
        success = await export_manager.delete_export(export_id)
        if not success:
            raise HTTPException(status_code=404, detail="Export not found")
        
        return APIResponse(
            success=True,
            message="Export deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete export: {str(e)}")


@router.get("/formats")
async def get_supported_formats():
    """Get list of supported export formats."""
    return {
        "formats": [
            {
                "id": "html",
                "name": "HTML",
                "description": "Rich HTML format with styling and speaker labels",
                "extension": ".html",
                "mime_type": "text/html"
            },
            {
                "id": "markdown",
                "name": "Markdown",
                "description": "Markdown format with speaker headers",
                "extension": ".md",
                "mime_type": "text/markdown"
            },
            {
                "id": "txt",
                "name": "Plain Text",
                "description": "Simple text format without formatting",
                "extension": ".txt",
                "mime_type": "text/plain"
            }
        ]
    }