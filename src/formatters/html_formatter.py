"""HTML formatter for transcription results with rich styling."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import html
from datetime import datetime

from .base_formatter import BaseFormatter
from ..services.transcription_client import TranscriptionResult


class HTMLFormatter(BaseFormatter):
    """HTML formatter with embedded CSS and rich styling."""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        self.embed_css = config.get('embed_css', True) if config else True
        self.speaker_styling = config.get('speaker_styling', True) if config else True
        self.timestamp_links = config.get('timestamp_links', True) if config else True
        self.timestamp_interval = config.get('timestamp_interval', 30) if config else 30
    
    def get_file_extension(self) -> str:
        """Return the file extension for HTML files."""
        return ".html"
    
    def _get_embedded_css(self) -> str:
        """Get embedded CSS styles for the HTML output."""
        return """
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                line-height: 1.6;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
                color: #333;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            }
            
            .header h1 {
                margin: 0 0 10px 0;
                font-size: 2.5em;
                font-weight: 300;
            }
            
            .metadata {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-bottom: 30px;
            }
            
            .metadata-item {
                background: white;
                padding: 15px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                border-left: 4px solid #667eea;
            }
            
            .metadata-label {
                font-weight: 600;
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .metadata-value {
                font-size: 1.2em;
                color: #333;
                margin-top: 5px;
            }
            
            .transcript-container {
                background: white;
                border-radius: 10px;
                padding: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                margin-bottom: 30px;
            }
            
            .speaker-paragraph {
                margin-bottom: 30px;
                padding: 25px;
                border-radius: 8px;
                border-left: 5px solid;
                background: #fafafa;
                transition: all 0.3s ease;
            }
            
            .speaker-paragraph:hover {
                background: #f0f0f0;
                transform: translateX(5px);
            }
            
            .speaker-header {
                display: flex;
                align-items: center;
                margin-bottom: 10px;
                font-weight: 600;
            }
            
            .speaker-name {
                font-size: 1.1em;
                margin-right: 15px;
            }
            
            .timestamp {
                background: rgba(0,0,0,0.1);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-family: 'Courier New', monospace;
                color: #666;
            }
            
            .timestamp-link {
                text-decoration: none;
                color: inherit;
                cursor: pointer;
            }
            
            .timestamp-link:hover {
                background: rgba(0,0,0,0.2);
            }
            
            .paragraph-timestamp {
                background: rgba(0,0,0,0.1);
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-family: 'Courier New', monospace;
                color: #666;
                margin-left: 15px;
            }
            
            .speaker-text {
                font-size: 1.05em;
                line-height: 1.7;
                color: #444;
            }
            
            .confidence-indicator {
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                margin-left: 10px;
            }
            
            .confidence-high { background-color: #28a745; }
            .confidence-medium { background-color: #ffc107; }
            .confidence-low { background-color: #dc3545; }
            
            .full-transcript {
                margin-top: 40px;
                padding: 30px;
                background: #f8f9fa;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }
            
            .full-transcript h3 {
                margin-top: 0;
                color: #495057;
                border-bottom: 2px solid #dee2e6;
                padding-bottom: 10px;
            }
            
            .full-transcript-text {
                font-size: 1.1em;
                line-height: 1.8;
                color: #495057;
            }
            
            .footer {
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 0.9em;
                border-top: 1px solid #e9ecef;
                margin-top: 40px;
            }
            
            @media (max-width: 768px) {
                body { padding: 10px; }
                .header { padding: 20px; }
                .header h1 { font-size: 2em; }
                .metadata { grid-template-columns: 1fr; }
                .speaker-segment { padding: 15px; }
            }
        </style>
        """
    
    def _get_speaker_style(self, speaker_index: int) -> str:
        """Get CSS border color for speaker based on index."""
        colors = self.config.get('speaker_colors', [
            "#2E86AB", "#A23B72", "#F18F01", "#6A994E", "#BC4749"
        ])
        return colors[speaker_index % len(colors)]
    
    def _get_confidence_class(self, confidence: float) -> str:
        """Get CSS class for confidence indicator."""
        if confidence >= 0.8:
            return "confidence-high"
        elif confidence >= 0.6:
            return "confidence-medium"
        else:
            return "confidence-low"
    
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
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp as MM:SS or HH:MM:SS."""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        else:
            return f"{minutes:02d}:{secs:02d}"
    
    def format(self, result: TranscriptionResult, output_path: Path) -> None:
        """Format transcription result as HTML and save to output path."""
        # Group speakers and assign colors
        speaker_names = list(set(segment.speaker for segment in result.speakers))
        speaker_colors = {name: self._get_speaker_style(i) for i, name in enumerate(speaker_names)}
        
        # Build HTML content
        html_content = self._build_html_document(result, speaker_colors, output_path.stem)
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
        except IOError as e:
            raise IOError(f"Cannot write HTML file {output_path}: {e}")
    
    def _build_html_document(self, result: TranscriptionResult, speaker_colors: Dict[str, str], title: str) -> str:
        """Build complete HTML document."""
        # HTML document structure
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "    <meta charset='UTF-8'>",
            "    <meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            f"    <title>Transcription: {html.escape(title)}</title>",
        ]
        
        # Add embedded CSS if enabled
        if self.embed_css:
            html_parts.append(self._get_embedded_css())
        
        html_parts.extend([
            "</head>",
            "<body>",
            self._build_header(title, result),
            self._build_metadata_section(result),
            self._build_transcript_section(result, speaker_colors),
            self._build_full_transcript_section(result),
            self._build_footer(),
            "</body>",
            "</html>"
        ])
        
        return "\n".join(html_parts)
    
    def _build_header(self, title: str, result: TranscriptionResult) -> str:
        """Build header section."""
        return f"""
        <div class="header">
            <h1>Audio Transcription</h1>
            <p><strong>File:</strong> {html.escape(title)}</p>
            <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        """
    
    def _build_metadata_section(self, result: TranscriptionResult) -> str:
        """Build metadata section with transcription statistics."""
        duration_formatted = self._format_duration(result.audio_duration)
        processing_formatted = self._format_duration(result.processing_time)
        
        return f"""
        <div class="metadata">
            <div class="metadata-item">
                <div class="metadata-label">Duration</div>
                <div class="metadata-value">{duration_formatted}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Speakers</div>
                <div class="metadata-value">{len(set(s.speaker for s in result.speakers))}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Confidence</div>
                <div class="metadata-value">{result.confidence:.1%}</div>
            </div>
            <div class="metadata-item">
                <div class="metadata-label">Processing Time</div>
                <div class="metadata-value">{processing_formatted}</div>
            </div>
        </div>
        """
    
    def _build_transcript_section(self, result: TranscriptionResult, speaker_colors: Dict[str, str]) -> str:
        """Build main transcript section with speaker paragraphs."""
        html_parts = ['<div class="transcript-container">']
        html_parts.append('<h2>Speaker Transcript</h2>')
        
        # Group segments by speaker into paragraphs with timestamps
        current_speaker = None
        current_paragraph = []
        current_paragraph_start_time = None
        
        for segment in result.speakers:
            # If speaker changed, finish current paragraph and start new one
            if segment.speaker != current_speaker:
                if current_paragraph and current_paragraph_start_time is not None:
                    # Add timestamp to every paragraph
                    self._add_speaker_paragraph(html_parts, current_speaker, current_paragraph, speaker_colors, 
                                              current_paragraph_start_time)
                    current_paragraph = []
                
                current_speaker = segment.speaker
                current_paragraph_start_time = segment.start_time
            
            # Add segment text to current paragraph
            current_paragraph.append(segment.text.strip())
        
        # Add final paragraph
        if current_paragraph and current_paragraph_start_time is not None:
            self._add_speaker_paragraph(html_parts, current_speaker, current_paragraph, speaker_colors,
                                      current_paragraph_start_time)
        
        html_parts.append('</div>')
        return "\n".join(html_parts)
    
    def _add_speaker_paragraph(self, html_parts: List[str], speaker: str, texts: List[str], speaker_colors: Dict[str, str], timestamp: Optional[float] = None):
        """Add a speaker paragraph with combined text and optional timestamp."""
        if not texts:
            return
        
        speaker_color = speaker_colors.get(speaker, "#666666")
        combined_text = ' '.join(texts)
        
        # Split into natural paragraphs (on sentence boundaries)
        paragraphs = self._split_into_paragraphs(combined_text)
        
        for i, paragraph in enumerate(paragraphs):
            if paragraph.strip():
                # Add timestamp only to the first paragraph of this speaker section
                timestamp_html = ""
                if timestamp is not None and i == 0:
                    marker_time = self._format_timestamp(timestamp)
                    timestamp_html = f'<span class="paragraph-timestamp">🕐 {marker_time}</span>'
                
                paragraph_html = f"""
                <div class="speaker-paragraph" style="border-left-color: {speaker_color};">
                    <div class="speaker-header">
                        <span class="speaker-name" style="color: {speaker_color};">
                            {html.escape(speaker)}
                        </span>
                        {timestamp_html}
                    </div>
                    <div class="speaker-text">
                        {html.escape(paragraph.strip())}
                    </div>
                </div>
                """
                html_parts.append(paragraph_html)
    
    def _split_into_paragraphs(self, text: str) -> List[str]:
        """Split text into natural paragraphs."""
        # Split on sentence endings followed by multiple spaces or new topics
        import re
        
        # Simple paragraph splitting - every 3-4 sentences or on topic changes
        sentences = re.split(r'(?<=[.!?])\s+', text)
        paragraphs = []
        current_paragraph = []
        
        for i, sentence in enumerate(sentences):
            current_paragraph.append(sentence)
            
            # Start new paragraph every 3-4 sentences or if sentence is very long
            if (len(current_paragraph) >= 3 and len(' '.join(current_paragraph)) > 200) or len(' '.join(current_paragraph)) > 400:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []
        
        # Add remaining sentences
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))
        
        return paragraphs if paragraphs else [text]
    

    
    def _build_full_transcript_section(self, result: TranscriptionResult) -> str:
        """Build full transcript section without speaker labels."""
        return f"""
        <div class="full-transcript">
            <h3>Full Transcript</h3>
            <div class="full-transcript-text">
                {html.escape(result.text)}
            </div>
        </div>
        """
    
    def _build_footer(self) -> str:
        """Build footer section."""
        return """
        <div class="footer">
            <p>Generated by Audio Transcription System</p>
        </div>
        """