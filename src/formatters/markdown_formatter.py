"""Markdown formatter for transcription results."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base_formatter import BaseFormatter
from ..services.transcription_client import TranscriptionResult


class MarkdownFormatter(BaseFormatter):
    """Markdown formatter with speaker headers and timestamp markers."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.speaker_headers = config.get('speaker_headers', True) if config else True
        self.timestamp_blockquotes = config.get('timestamp_blockquotes', True) if config else True
        self.preserve_paragraphs = config.get('preserve_paragraphs', True) if config else True
        self.timestamp_interval = config.get('timestamp_interval', 30) if config else 30
    
    def get_file_extension(self) -> str:
        """Return the file extension for Markdown files."""
        return ".md"
    
    def _format_duration(self, seconds: float) -> str:
        """Format duration in HH:MM:SS format."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _should_add_timestamp_marker(self, current_time: float, last_marker_time: float) -> bool:
        """Check if a timestamp marker should be added."""
        return current_time - last_marker_time >= self.timestamp_interval
    
    def _format_speaker_name(self, speaker: str) -> str:
        """Format speaker name for markdown headers."""
        # Clean up speaker name for markdown
        return speaker.replace("Speaker ", "Speaker ")
    
    def _format_confidence_indicator(self, confidence: float) -> str:
        """Format confidence as emoji indicator."""
        if confidence >= 0.9:
            return "🟢"  # High confidence
        elif confidence >= 0.7:
            return "🟡"  # Medium confidence
        else:
            return "🔴"  # Low confidence
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs based on sentence structure."""
        if not self.preserve_paragraphs:
            return [text]
        
        # Simple paragraph splitting based on sentence endings and length
        sentences = text.split('. ')
        paragraphs = []
        current_paragraph = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            # Add period back if it was removed by split
            if not sentence.endswith('.') and sentence != sentences[-1]:
                sentence += '.'
            
            current_paragraph.append(sentence)
            current_length += len(sentence)
            
            # Start new paragraph if current one is getting long
            if current_length > 200 and len(current_paragraph) > 1:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
                current_length = 0
        
        # Add remaining sentences
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return paragraphs if paragraphs else [text]
    
    def format(self, result: TranscriptionResult, output_path: Path) -> None:
        """Format transcription result as Markdown and save to output path."""
        markdown_content = self._build_markdown_document(result, output_path.stem)
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
        except IOError as e:
            raise IOError(f"Cannot write Markdown file {output_path}: {e}")
    
    def _build_markdown_document(self, result: TranscriptionResult, title: str) -> str:
        """Build complete Markdown document."""
        markdown_parts = []
        
        # Document header
        markdown_parts.extend(self._build_header(title, result))
        markdown_parts.append("")  # Empty line
        
        # Metadata section
        markdown_parts.extend(self._build_metadata_section(result))
        markdown_parts.append("")
        
        # Speaker transcript section
        markdown_parts.extend(self._build_speaker_transcript_section(result))
        markdown_parts.append("")
        
        # Full transcript section
        markdown_parts.extend(self._build_full_transcript_section(result))
        
        return "\n".join(markdown_parts)
    
    def _build_header(self, title: str, result: TranscriptionResult) -> List[str]:
        """Build document header."""
        return [
            f"# Audio Transcription: {title}",
            "",
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**Duration:** {self._format_duration(result.audio_duration)}  ",
            f"**Speakers:** {len(set(s.speaker for s in result.speakers))}  ",
            f"**Overall Confidence:** {result.confidence:.1%}  "
        ]
    
    def _build_metadata_section(self, result: TranscriptionResult) -> List[str]:
        """Build metadata section."""
        processing_time = self._format_duration(result.processing_time)
        
        return [
            "## Transcription Details",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Audio Duration | {self._format_duration(result.audio_duration)} |",
            f"| Processing Time | {processing_time} |",
            f"| Number of Speakers | {len(set(s.speaker for s in result.speakers))} |",
            f"| Total Segments | {len(result.speakers)} |",
            f"| Average Confidence | {result.confidence:.1%} |"
        ]
    
    def _build_speaker_transcript_section(self, result: TranscriptionResult) -> List[str]:
        """Build speaker transcript section with paragraph-based formatting."""
        markdown_parts = ["## Speaker Transcript", ""]
        
        # Group segments by speaker into paragraphs with timestamps
        current_speaker = None
        current_paragraph = []
        current_paragraph_start_time = None
        last_timestamp_marker = -1.0  # Start with -1 so first paragraph always gets timestamp
        
        for segment in result.speakers:
            # If speaker changed, finish current paragraph and start new one
            if segment.speaker != current_speaker:
                if current_paragraph and current_paragraph_start_time is not None:
                    # Check if we need a timestamp marker for this paragraph
                    needs_timestamp = (self.timestamp_blockquotes and 
                                     self._should_add_timestamp_marker(current_paragraph_start_time, last_timestamp_marker, interval=120))
                    if needs_timestamp:
                        last_timestamp_marker = current_paragraph_start_time
                    
                    # Finish previous speaker's paragraph
                    self._add_speaker_paragraph_md(markdown_parts, current_speaker, current_paragraph,
                                                  current_paragraph_start_time if needs_timestamp else None)
                    current_paragraph = []
                
                current_speaker = segment.speaker
                current_paragraph_start_time = segment.start_time
            
            # Add segment text to current paragraph
            current_paragraph.append(segment.text.strip())
        
        # Add final paragraph
        if current_paragraph and current_paragraph_start_time is not None:
            needs_timestamp = (self.timestamp_blockquotes and 
                             self._should_add_timestamp_marker(current_paragraph_start_time, last_timestamp_marker, interval=120))
            self._add_speaker_paragraph_md(markdown_parts, current_speaker, current_paragraph,
                                          current_paragraph_start_time if needs_timestamp else None)
        
        return markdown_parts
    
    def _add_speaker_paragraph_md(self, markdown_parts: List[str], speaker: str, texts: List[str], timestamp: Optional[float] = None):
        """Add a speaker paragraph with combined text in Markdown."""
        if not texts:
            return
        
        # Add speaker header with optional timestamp
        if self.speaker_headers:
            speaker_name = self._format_speaker_name(speaker)
            if timestamp is not None:
                timestamp_marker = self._format_timestamp(timestamp)
                markdown_parts.append(f"### {speaker_name} ⏰ {timestamp_marker}")
            else:
                markdown_parts.append(f"### {speaker_name}")
            markdown_parts.append("")
        
        # Combine and split into natural paragraphs
        combined_text = ' '.join(texts)
        paragraphs = self._split_into_paragraphs(combined_text)
        
        for paragraph in paragraphs:
            if paragraph.strip():
                markdown_parts.append(paragraph.strip())
                markdown_parts.append("")  # Empty line between paragraphs
    
    def _should_add_timestamp_marker(self, current_time: float, last_marker_time: float, interval: int = 120) -> bool:
        """Check if a timestamp marker should be added (default every 2 minutes)."""
        return current_time - last_marker_time >= interval
    
    def _build_full_transcript_section(self, result: TranscriptionResult) -> List[str]:
        """Build full transcript section without speaker labels."""
        markdown_parts = [
            "## Full Transcript",
            "",
            "*Complete transcription without speaker identification:*",
            ""
        ]
        
        # Split full transcript into paragraphs
        paragraphs = self._split_into_paragraphs(result.text)
        for paragraph in paragraphs:
            markdown_parts.append(paragraph)
            markdown_parts.append("")  # Empty line between paragraphs
        
        # Add footer
        markdown_parts.extend([
            "---",
            "",
            "*Generated by Audio Transcription System*"
        ])
        
        return markdown_parts