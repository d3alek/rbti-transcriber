"""Abstract base class for transcription formatters."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any

from ..services.transcription_client import TranscriptionResult


class BaseFormatter(ABC):
    """Abstract base class for transcription output formatters."""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
    
    @abstractmethod
    def format(self, result: TranscriptionResult, output_path: Path) -> None:
        """Format transcription result and save to output path."""
        pass
    
    @abstractmethod
    def get_file_extension(self) -> str:
        """Return the file extension for this formatter."""
        pass
    
    def _format_timestamp(self, seconds: float) -> str:
        """Convert seconds to MM:SS format."""
        minutes = int(seconds // 60)
        seconds = int(seconds % 60)
        return f"{minutes:02d}:{seconds:02d}"
    
    def _get_speaker_color(self, speaker_index: int) -> str:
        """Get color for speaker based on index."""
        colors = self.config.get('speaker_colors', [
            "#2E86AB", "#A23B72", "#F18F01", "#6A994E", "#BC4749"
        ])
        return colors[speaker_index % len(colors)]