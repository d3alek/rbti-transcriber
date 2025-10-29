"""Export manager service for transcription files."""

import uuid
import tempfile
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import shutil

# Import from existing transcription system
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.formatters.formatter_factory import FormatterFactory
from src.utils.config import ConfigManager
from src.utils.cache_manager import CacheManager

from ..config import Settings


class ExportManager:
    """Manages export operations for transcription files."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.config_manager = ConfigManager(settings.config_file)
        self.cache_manager = CacheManager(settings.audio_directory / "transcriptions" / "cache")
        self.formatter_factory = FormatterFactory(self.config_manager, self.cache_manager)
        
        # Temporary directory for exports
        self.export_dir = Path(tempfile.gettempdir()) / "transcription_exports"
        self.export_dir.mkdir(exist_ok=True)
        
        # Track active exports
        self.active_exports: Dict[str, Dict[str, Any]] = {}
    
    async def create_export(self, file_id: str, format_type: str) -> str:
        """Create an export for a transcription file."""
        export_id = str(uuid.uuid4())
        
        try:
            # Find the audio file
            audio_file = self._find_audio_file(file_id)
            if not audio_file:
                raise Exception(f"Audio file not found for ID: {file_id}")
            
            # Load transcription from cache
            transcription_result = self._load_transcription(audio_file)
            if not transcription_result:
                raise Exception("No transcription found for this file")
            
            # Generate export file
            export_path = self.export_dir / f"{export_id}.{self._get_file_extension(format_type)}"
            
            # Use existing formatter
            if format_type == 'html':
                from src.formatters.html_formatter import HTMLFormatter
                formatter = HTMLFormatter(self.config_manager.get('formatting.html', {}))
                formatter.format(transcription_result, export_path)
            elif format_type == 'markdown':
                from src.formatters.markdown_formatter import MarkdownFormatter
                formatter = MarkdownFormatter(self.config_manager.get('formatting.markdown', {}))
                formatter.format(transcription_result, export_path)
            elif format_type == 'txt':
                # Simple text export
                with open(export_path, 'w', encoding='utf-8') as f:
                    f.write(transcription_result.text)
            else:
                raise Exception(f"Unsupported export format: {format_type}")
            
            # Store export info
            self.active_exports[export_id] = {
                'file_id': file_id,
                'format': format_type,
                'path': export_path,
                'filename': f"{audio_file.stem}.{self._get_file_extension(format_type)}",
                'created_at': Path(export_path).stat().st_mtime
            }
            
            return export_id
            
        except Exception as e:
            raise Exception(f"Failed to create export: {str(e)}")
    
    async def get_export_file(self, export_id: str) -> Tuple[Optional[Path], Optional[str], Optional[str]]:
        """Get export file information."""
        if export_id not in self.active_exports:
            return None, None, None
        
        export_info = self.active_exports[export_id]
        file_path = Path(export_info['path'])
        
        if not file_path.exists():
            return None, None, None
        
        return (
            file_path,
            export_info['filename'],
            self._get_media_type(export_info['format'])
        )
    
    async def delete_export(self, export_id: str) -> bool:
        """Delete an export file."""
        if export_id not in self.active_exports:
            return False
        
        try:
            export_info = self.active_exports[export_id]
            file_path = Path(export_info['path'])
            
            if file_path.exists():
                file_path.unlink()
            
            del self.active_exports[export_id]
            return True
            
        except Exception:
            return False
    
    def _find_audio_file(self, file_id: str) -> Optional[Path]:
        """Find audio file by ID."""
        for file_path in Path(self.settings.audio_directory).glob("*.mp3"):
            if self._generate_file_id(file_path) == file_id:
                return file_path
        return None
    
    def _load_transcription(self, audio_file: Path):
        """Load transcription from cache."""
        # Try to find cached transcription for any service
        for service in ['deepgram']:
            cache_key = self._get_cache_key(audio_file, service)
            cached_result = self.cache_manager.get_result(cache_key)
            if cached_result:
                return cached_result
        return None
    
    def _generate_file_id(self, file_path: Path) -> str:
        """Generate file ID matching the file manager."""
        import hashlib
        file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
        return hashlib.md5(file_info.encode()).hexdigest()[:12]
    
    def _get_cache_key(self, file_path: Path, service: str) -> str:
        """Generate cache key for a file and service."""
        import hashlib
        file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
        return hashlib.md5(f"{file_info}_{service}".encode()).hexdigest()[:16]
    
    def _get_file_extension(self, format_type: str) -> str:
        """Get file extension for format type."""
        extensions = {
            'html': 'html',
            'markdown': 'md',
            'txt': 'txt'
        }
        return extensions.get(format_type, 'txt')
    
    def _get_media_type(self, format_type: str) -> str:
        """Get media type for format type."""
        media_types = {
            'html': 'text/html',
            'markdown': 'text/markdown',
            'txt': 'text/plain'
        }
        return media_types.get(format_type, 'text/plain')