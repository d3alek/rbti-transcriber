#!/usr/bin/env python3
"""
Generate self-contained HTML bundles for each transcription.

Each bundle includes:
- The compressed WebM/Opus audio file
- The transcript JSON file (RichWordsTranscript format)
- A standalone HTML file with react-transcript-editor preloaded
"""

import json
import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import base64

# HTML template for standalone transcript viewer
HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Transcript</title>
    <style>
        body {{
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }}
        #root {{
            height: 100vh;
            width: 100vw;
        }}
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-size: 18px;
            color: #666;
        }}
        .save-button-container {{
            position: fixed;
            top: 30px;
            right: 10px;
            z-index: 1000;
        }}
        .save-button {{
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }}
        .save-button:hover {{
            background-color: #45a049;
        }}
        .save-button:disabled {{
            background-color: #cccccc;
            cursor: not-allowed;
        }}
    </style>
</head>
<body>
    <div id="root">
        <div class="loading">Loading transcript editor...</div>
    </div>

    <!-- React and ReactDOM from CDN -->
    <script crossorigin src="https://unpkg.com/react@16/umd/react.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@16/umd/react-dom.production.min.js"></script>
    <script crossorigin src="https://unpkg.com/babel-standalone@6/babel.min.js"></script>
    
    <!-- Draft.js CSS (required for editor) -->
    <link rel="stylesheet" href="https://unpkg.com/draft-js@0.10.5/dist/Draft.css" />

    <!-- Load react-transcript-editor bundle (relative path: ../../bundles/ from seminar/lecture/) -->
    <script src="../../bundles/react-transcript-editor-bundle.js" onload="initEditor()" onerror="console.error('Failed to load react-transcript-editor bundle')"></script>
    
    <script type="text/babel">
        // Wait for ReactTranscriptEditor to be available
        function initEditor() {{
            console.log('initEditor called, checking for ReactTranscriptEditor...');
            console.log('typeof ReactTranscriptEditor:', typeof ReactTranscriptEditor);
            
            // Check if React, ReactDOM, and ReactTranscriptEditor are all available
            if (typeof React === 'undefined') {{
                console.log('Waiting for React...');
                setTimeout(initEditor, 100);
                return;
            }}
            
            if (typeof ReactDOM === 'undefined') {{
                console.log('Waiting for ReactDOM...');
                setTimeout(initEditor, 100);
                return;
            }}
            
            if (typeof ReactTranscriptEditor === 'undefined') {{
                console.log('Waiting for ReactTranscriptEditor...');
                setTimeout(initEditor, 100);
                return;
            }}
            
            console.log('ReactTranscriptEditor available:', ReactTranscriptEditor);
            console.log('ReactTranscriptEditor keys:', Object.keys(ReactTranscriptEditor || {{}}));
            
            // Try to get TranscriptEditor - handle different UMD export formats
            let TranscriptEditor;
            if (ReactTranscriptEditor.default) {{
                // Default export is most common with webpack UMD
                TranscriptEditor = ReactTranscriptEditor.default;
                console.log('Using ReactTranscriptEditor.default');
            }} else if (ReactTranscriptEditor.TranscriptEditor) {{
                // Named export
                TranscriptEditor = ReactTranscriptEditor.TranscriptEditor;
                console.log('Using ReactTranscriptEditor.TranscriptEditor');
            }} else if (typeof ReactTranscriptEditor === 'function') {{
                // Direct function
                TranscriptEditor = ReactTranscriptEditor;
                console.log('Using ReactTranscriptEditor directly as function');
            }} else {{
                console.error('Could not find TranscriptEditor in ReactTranscriptEditor:', ReactTranscriptEditor);
                console.error('Available properties:', Object.keys(ReactTranscriptEditor || {{}}));
                document.getElementById('root').innerHTML = '<div class="loading" style="color: red;">Error: Could not load TranscriptEditor component. Check console for details.</div>';
                return;
            }}
            
            console.log('TranscriptEditor found:', TranscriptEditor);
            
            // Load transcript data
            const transcriptData = {transcript_json};
            const originalTranscriptData = JSON.parse(JSON.stringify(transcriptData)); // Deep copy for comparison
            
            // Media URL (relative to this HTML file)
            const mediaUrl = './{audio_filename}';
            
            // App component with Save button
            class App extends React.Component {{
                constructor(props) {{
                    super(props);
                    this.editorRef = React.createRef();
                    this.state = {{
                        isSaving: false
                    }};
                }}
                
                handleSave = () => {{
                    if (!this.editorRef.current) {{
                        alert('Editor not ready');
                        return;
                    }}
                    
                    this.setState({{ isSaving: true }});
                    
                    try {{
                        // Get edited content from the editor
                        const editedContent = this.editorRef.current.getEditorContent('deepgram');
                        
                        if (!editedContent || !editedContent.data) {{
                            alert('Failed to get edited content');
                            this.setState({{ isSaving: false }});
                            return;
                        }}
                        
                        // Download the corrected JSON file
                        const blob = new Blob([JSON.stringify(editedContent.data, null, 2)], {{ type: 'application/json' }});
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = '{audio_filename}_corrected.json';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        window.URL.revokeObjectURL(url);
                        
                        alert('Corrections saved! File downloaded successfully.');
                    }} catch (error) {{
                        console.error('Error saving:', error);
                        alert('Failed to save corrections: ' + error.message);
                    }} finally {{
                        this.setState({{ isSaving: false }});
                    }}
                }};
                
                render() {{
                    return React.createElement('div', null,
                        React.createElement('div', {{ className: 'save-button-container' }},
                            React.createElement('button', {{
                                className: 'save-button',
                                onClick: this.handleSave,
                                disabled: this.state.isSaving
                            }}, this.state.isSaving ? 'Saving...' : '💾 Save Corrections')
                        ),
                        React.createElement(TranscriptEditor, {{
                            ref: this.editorRef,
                            transcriptData: transcriptData,
                            mediaUrl: mediaUrl,
                            isEditable: false,
                            spellCheck: false,
                            sttJsonType: 'deepgram',
                            title: '{title}',
                            fileName: '{audio_filename}',
                            mediaType: 'audio'
                        }})
                    );
                }}
            }}
            
            try {{
                ReactDOM.render(React.createElement(App), document.getElementById('root'));
                console.log('Transcript editor rendered successfully');
            }} catch (error) {{
                console.error('Error rendering transcript editor:', error);
                document.getElementById('root').innerHTML = '<div class="loading" style="color: red;">Error: ' + error.message + '</div>';
            }}
        }}
        
        // Start initialization when DOM and scripts are ready
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{
                // Wait a bit for scripts to load
                setTimeout(initEditor, 500);
            }});
        }} else {{
            // DOM already ready, but wait for scripts
            setTimeout(initEditor, 500);
        }}
    </script>
</body>
</html>
'''


def find_transcription_files(base_dir: Path) -> List[Path]:
    """Find all transcription JSON files."""
    transcriptions = []
    for json_file in base_dir.rglob("transcriptions/*.json"):
        # Skip cache and temp directories
        if "cache" not in json_file.parts and "temp" not in json_file.parts:
            transcriptions.append(json_file)
    return transcriptions


def get_seminar_group(transcription_path: Path, base_dir: Path) -> str:
    """Extract seminar group name from file path."""
    try:
        relative_path = transcription_path.relative_to(base_dir)
        # Go up from transcriptions/ directory to get seminar group
        if "transcriptions" in relative_path.parts:
            idx = relative_path.parts.index("transcriptions")
            if idx > 0:
                return relative_path.parts[idx - 1]
        # Fallback to parent directory
        return transcription_path.parent.parent.name
    except ValueError:
        return transcription_path.parent.parent.name


def find_compressed_audio(transcription_path: Path) -> Optional[Path]:
    """Find compressed WebM audio file corresponding to transcription."""
    # Get the base filename without extension
    base_name = transcription_path.stem
    
    # Look in compressed/ directory at same level as transcriptions/
    compressed_dir = transcription_path.parent.parent / "compressed"
    if compressed_dir.exists():
        # First try exact match: {base_name}.webm
        webm_path = compressed_dir / f"{base_name}.webm"
        if webm_path.exists():
            return webm_path
        
        # Fallback: look for hash-based naming pattern: {base_name}_*_compressed.webm
        for webm_file in compressed_dir.glob(f"{base_name}_*_compressed.webm"):
            if webm_file.exists():
                return webm_file
    
    # Fallback: look for any .webm with same base name in compressed directories
    for webm_file in transcription_path.parent.parent.rglob(f"{base_name}*.webm"):
        if "compressed" in webm_file.parts or webm_file.parent.name == "compressed":
            return webm_file
    
    return None


def extract_speaker_number(speaker_identifier) -> int:
    """Extract speaker number from various identifier formats.
    
    Handles:
    - "Speaker 0", "Speaker 1" -> extracts number
    - Integer values -> returns directly
    - String names (e.g., "Reams") -> maps to 0 (can be improved with mapping)
    - Other strings -> tries to convert to int, defaults to 0
    """
    if isinstance(speaker_identifier, int):
        return speaker_identifier
    
    if isinstance(speaker_identifier, str):
        # Try "Speaker N" format
        if speaker_identifier.startswith('Speaker '):
            try:
                return int(speaker_identifier.replace('Speaker ', ''))
            except ValueError:
                pass
        
        # Try to convert string directly to int
        try:
            return int(speaker_identifier)
        except ValueError:
            # If it's a name or other non-numeric string, default to 0
            # In the future, we could maintain a mapping of names to numbers
            return 0
    
    # Default fallback
    return 0


def load_transcript_json(transcription_path: Path) -> Dict:
    """
    Load transcript JSON file as-is.
    The bundled UI will handle normalization (RichWordsTranscript or raw Deepgram format).
    """
    with open(transcription_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Return the data as-is - let the UI handle format detection and conversion
    return data


def generate_bundle(transcription_path: Path, output_dir: Path, base_dir: Path) -> Tuple[str, str]:
    """
    Generate a bundle for a single transcription.
    
    Returns:
        (seminar_group, lecture_name) tuple
    """
    # Load transcript data
    transcript_data = load_transcript_json(transcription_path)
    
    # Find compressed audio
    audio_path = find_compressed_audio(transcription_path)
    if not audio_path:
        print(f"⚠️  Warning: No compressed audio found for {transcription_path}")
        return None, None
    
    # Get seminar group and lecture name
    seminar_group = get_seminar_group(transcription_path, base_dir)
    lecture_name = transcription_path.stem
    
    # Create output directory structure
    bundle_dir = output_dir / seminar_group / lecture_name
    bundle_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy audio file
    audio_filename = audio_path.name
    shutil.copy2(audio_path, bundle_dir / audio_filename)
    
    # Copy transcript JSON (for reference)
    shutil.copy2(transcription_path, bundle_dir / "transcript.json")
    
    # Generate HTML file
    html_content = HTML_TEMPLATE.format(
        title=lecture_name,
        transcript_json=json.dumps(transcript_data, indent=2),
        audio_filename=audio_filename
    )
    
    with open(bundle_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✅ Generated bundle: {seminar_group}/{lecture_name}")
    return seminar_group, lecture_name


def main():
    """Main entry point."""
    # Determine base directory (repository root)
    script_dir = Path(__file__).parent
    base_dir = script_dir.parent
    
    # Output directory for GitHub Pages
    output_dir = base_dir / "gh-pages-output"
    output_dir.mkdir(exist_ok=True)
    
    # Find all transcription files
    transcriptions = find_transcription_files(base_dir)
    
    if not transcriptions:
        print("⚠️  No transcription files found")
        return
    
    print(f"📝 Found {len(transcriptions)} transcription file(s)")
    
    # Generate bundles
    bundles = {}
    for transcription_path in transcriptions:
        try:
            seminar_group, lecture_name = generate_bundle(transcription_path, output_dir, base_dir)
            if seminar_group and lecture_name:
                if seminar_group not in bundles:
                    bundles[seminar_group] = []
                bundles[seminar_group].append({
                    'name': lecture_name,
                    'path': f"{seminar_group}/{lecture_name}/index.html"
                })
        except Exception as e:
            print(f"❌ Error processing {transcription_path}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save bundle manifest for index page generation
    manifest_path = output_dir / "bundles-manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(bundles, f, indent=2)
    
    print(f"\n✅ Generated {sum(len(lectures) for lectures in bundles.values())} bundle(s)")
    print(f"📦 Manifest saved to {manifest_path}")


if __name__ == "__main__":
    main()

