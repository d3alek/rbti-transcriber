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
        
        # Find all .mp3 files recursively
        for file_path in self.base_directory.rglob("*.mp3"):
            if file_path.is_file():
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
    """Manages output directory structure for transcription results."""
    
    def __init__(self, base_directory: Path):
        self.base_directory = Path(base_directory)
        self.html_dir = self.base_directory / "html"
        self.markdown_dir = self.base_directory / "markdown"
        self.cache_dir = self.base_directory / "cache"
        self.metadata_dir = self.base_directory / "metadata"
    
    def create_output_structure(self) -> None:
        """Create the complete output directory structure."""
        directories = [
            self.base_directory,
            self.html_dir,
            self.markdown_dir,
            self.cache_dir,
            self.metadata_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except OSError as e:
                raise FileSystemError(f"Cannot create directory {directory}: {e}")
    
    def get_output_path(self, input_file: Path, format_type: str) -> Path:
        """Get output path for a given input file and format type."""
        stem = input_file.stem
        
        if format_type == "html":
            return self.html_dir / f"{stem}.html"
        elif format_type == "markdown":
            return self.markdown_dir / f"{stem}.md"
        elif format_type == "cache":
            return self.cache_dir / f"{stem}.json"
        elif format_type == "metadata":
            return self.metadata_dir / f"{stem}_metadata.json"
        else:
            raise ValueError(f"Unknown format type: {format_type}")
    
    def file_exists(self, input_file: Path, format_type: str) -> bool:
        """Check if output file already exists for given input and format."""
        output_path = self.get_output_path(input_file, format_type)
        return output_path.exists() and output_path.stat().st_size > 0
    
    def get_existing_files(self, input_file: Path) -> Dict[str, bool]:
        """Get status of all output files for a given input file."""
        return {
            'html': self.file_exists(input_file, 'html'),
            'markdown': self.file_exists(input_file, 'markdown'),
            'cache': self.file_exists(input_file, 'cache'),
            'metadata': self.file_exists(input_file, 'metadata')
        }