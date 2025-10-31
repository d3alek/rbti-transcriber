"""File scanner and validator for MP3 audio files."""

import os
from pathlib import Path
from typing import List, Dict, Optional
import struct

from .exceptions import AudioValidationError, FileSystemError


class MP3FileScanner:
    """Scanner and validator for MP3 audio files."""
    
    # MP3 file header signatures
    MP3_HEADERS = [
        b'\xff\xfb',  # MPEG-1 Layer 3
        b'\xff\xf3',  # MPEG-2 Layer 3
        b'\xff\xf2',  # MPEG-2.5 Layer 3
        b'ID3',       # ID3 tag
    ]
    
    def __init__(self, base_directory: Path):
        self.base_directory = Path(base_directory)
        if not self.base_directory.exists():
            raise FileSystemError(f"Directory does not exist: {base_directory}")
        if not self.base_directory.is_dir():
            raise FileSystemError(f"Path is not a directory: {base_directory}")
    
    def scan_mp3_files(self) -> List[Path]:
        """Scan directory for MP3 files and return list of valid files."""
        mp3_files = []
        
        # Directories to exclude from scanning
        exclude_dirs = {
            'transcriptions',  # Output directory
            'compressed',      # Compressed files directory
            'cache',          # Cache directory
            'metadata'        # Metadata directory
        }
        
        # Find all .mp3 files recursively, excluding output directories
        for file_path in self.base_directory.rglob("*.mp3"):
            if file_path.is_file():
                # Check if file is in an excluded directory
                if any(excluded_dir in file_path.parts for excluded_dir in exclude_dirs):
                    continue
                
                # Check if file is a compressed file (ends with _compressed.mp3)
                if file_path.name.endswith('_compressed.mp3'):
                    continue
                
                try:
                    if self.validate_mp3_file(file_path):
                        mp3_files.append(file_path)
                except AudioValidationError as e:
                    print(f"Warning: Skipping invalid MP3 file {file_path}: {e}")
                    continue
        
        return sorted(mp3_files)
    
    def validate_mp3_file(self, file_path: Path) -> bool:
        """Validate MP3 file format using file headers."""
        if not file_path.exists():
            raise AudioValidationError(f"File does not exist: {file_path}")
        
        if file_path.stat().st_size == 0:
            raise AudioValidationError(f"File is empty: {file_path}")
        
        # Check file header
        try:
            with open(file_path, 'rb') as f:
                header = f.read(10)
                
                if len(header) < 3:
                    raise AudioValidationError(f"File too small to be valid MP3: {file_path}")
                
                # Check for MP3 signatures
                is_valid = False
                for signature in self.MP3_HEADERS:
                    if header.startswith(signature):
                        is_valid = True
                        break
                
                if not is_valid:
                    raise AudioValidationError(f"Invalid MP3 header: {file_path}")
                
                return True
                
        except IOError as e:
            raise AudioValidationError(f"Cannot read file {file_path}: {e}")
    
    def get_file_info(self, file_path: Path) -> Dict[str, any]:
        """Get basic information about an MP3 file."""
        if not self.validate_mp3_file(file_path):
            raise AudioValidationError(f"Invalid MP3 file: {file_path}")
        
        stat = file_path.stat()
        return {
            'path': file_path,
            'name': file_path.name,
            'size_bytes': stat.st_size,
            'size_mb': round(stat.st_size / (1024 * 1024), 2),
            'modified_time': stat.st_mtime,
            'relative_path': file_path.relative_to(self.base_directory)
        }


class OutputDirectoryManager:
    """
    Manages output directory structure for transcription results.
    Updated to match design.md structure: seminar_group/transcriptions/ and seminar_group/compressed/
    """
    
    def __init__(self, audio_file_path: Path):
        """Initialize with the audio file path to determine seminar group structure."""
        self.audio_file = Path(audio_file_path)
        self.seminar_group_dir = self.audio_file.parent
        self.transcriptions_dir = self.seminar_group_dir / "transcriptions"
        self.compressed_dir = self.seminar_group_dir / "compressed"
    
    def create_output_structure(self) -> None:
        """Create the output directory structure for this seminar group."""
        directories = [
            self.transcriptions_dir,
            self.compressed_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise FileSystemError(f"Cannot create directory {directory}: {e}")
    
    def get_transcription_path(self, service: str = "deepgram") -> Path:
        """Get path for the raw transcription JSON file."""
        stem = self.audio_file.stem
        return self.transcriptions_dir / f"{stem}.json"
    
    def get_compressed_audio_path(self) -> Path:
        """Get path for the compressed audio file."""
        return self.compressed_dir / self.audio_file.name
    
    def transcription_exists(self) -> bool:
        """Check if transcription JSON file exists."""
        transcription_path = self.get_transcription_path()
        return transcription_path.exists() and transcription_path.stat().st_size > 0
    
    def compressed_audio_exists(self) -> bool:
        """Check if compressed audio file exists."""
        compressed_path = self.get_compressed_audio_path()
        return compressed_path.exists() and compressed_path.stat().st_size > 0
    
    def get_existing_files(self) -> Dict[str, bool]:
        """Get status of output files for this audio file."""
        return {
            'transcription': self.transcription_exists(),
            'compressed_audio': self.compressed_audio_exists()
        }