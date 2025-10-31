"""
Directory scanning API endpoints for the Audio Transcription Web Manager.
Implements requirements 1.1, 1.2, 1.4, 1.5 for directory-based file management.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from pathlib import Path
import sys

# Import the FileSystemScanner service
sys.path.append(str(Path(__file__).parent.parent.parent))

from ..models import (
    DirectoryScanRequest, 
    DirectoryScanResult, 
    AudioFileDetail,
    AudioMetadataResponse,
    TranscriptionStatusDetail,
    APIResponse,
    DirectoryPermissions,
    AudioFormatValidation,
    TranscriptionFileIntegrity
)
from ..services.filesystem_scanner import FileSystemScanner, FileSystemValidator
from ..config import get_settings

router = APIRouter()


def get_filesystem_scanner() -> FileSystemScanner:
    """Dependency to get FileSystemScanner instance."""
    settings = get_settings()
    return FileSystemScanner(settings.audio_directory)


@router.post("/scan", response_model=DirectoryScanResult)
async def scan_directory(
    request: DirectoryScanRequest,
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> DirectoryScanResult:
    """
    Scan a directory for MP3 audio files and organize by seminar groups.
    
    This endpoint implements requirements:
    - 1.1: Directory selection and scanning
    - 1.2: Transcription status checking
    - 1.4: Seminar group organization
    - 1.5: Compressed audio detection
    """
    try:
        # Validate directory path
        directory_path = Path(request.directory_path)
        if not directory_path.exists():
            raise HTTPException(status_code=404, detail=f"Directory not found: {request.directory_path}")
        
        if not directory_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.directory_path}")
        
        # Perform directory scan
        scan_result = await scanner.scan_directory(request.directory_path)
        
        # Convert to API response format
        audio_files = []
        for file_info in scan_result['audio_files']:
            audio_files.append(AudioFileDetail(**file_info))
        
        return DirectoryScanResult(
            directory=scan_result['directory'],
            total_files=scan_result['total_files'],
            transcribed_files=scan_result['transcribed_files'],
            audio_files=audio_files,
            seminar_groups=scan_result['seminar_groups'],
            groups_detail=scan_result['groups_detail'],
            scan_timestamp=scan_result['scan_timestamp']
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to scan directory: {str(e)}")


@router.get("/metadata")
async def get_audio_metadata(
    file_path: str = Query(..., description="Path to the audio file"),
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> AudioMetadataResponse:
    """
    Get detailed metadata for a specific audio file.
    
    Implements requirement 1.3: Audio metadata extraction.
    """
    try:
        # Validate file path
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"Audio file not found: {file_path}")
        
        # Get metadata
        metadata = await scanner.get_audio_metadata(file_path)
        
        return AudioMetadataResponse(**metadata)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get audio metadata: {str(e)}")


@router.get("/transcription-status")
async def get_transcription_status(
    file_path: str = Query(..., description="Path to the audio file"),
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> TranscriptionStatusDetail:
    """
    Check transcription status for a specific audio file.
    
    Implements requirement 1.2: Transcription status checking.
    """
    try:
        # Validate file path
        if not Path(file_path).exists():
            raise HTTPException(status_code=404, detail=f"Audio file not found: {file_path}")
        
        # Check transcription status
        status_info = await scanner.check_transcription_status(file_path)
        
        return TranscriptionStatusDetail(**status_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check transcription status: {str(e)}")


@router.post("/clear-cache", response_model=APIResponse)
async def clear_scanner_cache(
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> APIResponse:
    """
    Clear the directory scanner cache to force fresh scans.
    """
    try:
        scanner.clear_cache()
        return APIResponse(
            success=True,
            message="Scanner cache cleared successfully"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")


# Optional endpoints for task 2.3 (File system validation and error handling)

@router.get("/validate/directory-permissions")
async def check_directory_permissions(
    directory_path: str = Query(..., description="Path to the directory to check")
) -> DirectoryPermissions:
    """
    Check directory access permissions.
    
    This is part of optional task 2.3: File system validation.
    """
    try:
        permissions = FileSystemValidator.check_directory_permissions(directory_path)
        return DirectoryPermissions(**permissions)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check directory permissions: {str(e)}")


@router.get("/validate/audio-format")
async def validate_audio_format(
    file_path: str = Query(..., description="Path to the audio file to validate")
) -> AudioFormatValidation:
    """
    Validate audio file format.
    
    This is part of optional task 2.3: File system validation.
    """
    try:
        validation = FileSystemValidator.validate_audio_format(file_path)
        return AudioFormatValidation(**validation)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate audio format: {str(e)}")


@router.get("/validate/transcription-integrity")
async def check_transcription_file_integrity(
    file_path: str = Query(..., description="Path to the transcription cache file to check")
) -> TranscriptionFileIntegrity:
    """
    Check integrity of transcription cache files.
    
    This is part of optional task 2.3: File system validation.
    """
    try:
        integrity = FileSystemValidator.check_transcription_file_integrity(file_path)
        return TranscriptionFileIntegrity(**integrity)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check transcription file integrity: {str(e)}")


# Utility endpoints for seminar group management

@router.get("/seminar-groups")
async def list_seminar_groups(
    directory_path: str = Query(..., description="Base directory to scan for seminar groups"),
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> List[str]:
    """
    List all seminar groups found in a directory.
    
    Implements requirement 1.4: Seminar group organization.
    """
    try:
        # Perform a quick scan to get seminar groups
        scan_result = await scanner.scan_directory(directory_path)
        return scan_result['seminar_groups']
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list seminar groups: {str(e)}")


@router.get("/seminar-groups/{group_name}/files")
async def get_seminar_group_files(
    group_name: str,
    directory_path: str = Query(..., description="Base directory to scan"),
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> List[AudioFileDetail]:
    """
    Get all audio files for a specific seminar group.
    
    Implements requirement 1.4: Seminar group organization.
    """
    try:
        # Perform directory scan
        scan_result = await scanner.scan_directory(directory_path)
        
        # Filter files for the specific group
        if group_name not in scan_result['groups_detail']:
            raise HTTPException(status_code=404, detail=f"Seminar group not found: {group_name}")
        
        group_files = scan_result['groups_detail'][group_name]
        return [AudioFileDetail(**file_info) for file_info in group_files]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get seminar group files: {str(e)}")


@router.get("/compressed-audio/status")
async def get_compressed_audio_status(
    directory_path: str = Query(..., description="Directory to check for compressed audio"),
    scanner: FileSystemScanner = Depends(get_filesystem_scanner)
) -> dict:
    """
    Get status of compressed audio files in a directory.
    
    Implements requirement 1.5: Compressed audio detection and size reporting.
    """
    try:
        # Scan directory
        scan_result = await scanner.scan_directory(directory_path)
        
        # Analyze compressed audio status
        total_files = len(scan_result['audio_files'])
        compressed_files = len([f for f in scan_result['audio_files'] if f.get('has_compressed_version')])
        
        total_original_size = sum(f.get('size', 0) for f in scan_result['audio_files'])
        total_compressed_size = sum(f.get('compressed_size', 0) for f in scan_result['audio_files'] if f.get('has_compressed_version'))
        
        compression_savings = 0
        if total_original_size > 0 and total_compressed_size > 0:
            compression_savings = round((1 - total_compressed_size / total_original_size) * 100, 1)
        
        return {
            'directory': directory_path,
            'total_files': total_files,
            'compressed_files': compressed_files,
            'compression_percentage': round((compressed_files / total_files) * 100, 1) if total_files > 0 else 0,
            'total_original_size_mb': round(total_original_size / (1024 * 1024), 1),
            'total_compressed_size_mb': round(total_compressed_size / (1024 * 1024), 1),
            'compression_savings_percentage': compression_savings,
            'scan_timestamp': scan_result['scan_timestamp']
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get compressed audio status: {str(e)}")