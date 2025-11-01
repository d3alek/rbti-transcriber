#!/usr/bin/env python3
"""
Generate self-contained HTML bundles for each transcription.

Each bundle includes:
- The compressed MP3 file
- The transcript JSON file
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
            
            // Media URL (relative to this HTML file)
            const mediaUrl = './{audio_filename}';
            
            // Render the transcript editor
            function App() {{
                return React.createElement(TranscriptEditor, {{
                    transcriptData: transcriptData,
                    mediaUrl: mediaUrl,
                    isEditable: false,
                    spellCheck: false,
                    sttJsonType: 'deepgram',
                    title: '{title}',
                    fileName: '{audio_filename}',
                    mediaType: 'audio'
                }});
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
    """Find compressed audio file corresponding to transcription."""
    # Get the base filename without extension
    base_name = transcription_path.stem
    
    # Look in compressed/ directory at same level as transcriptions/
    compressed_dir = transcription_path.parent.parent / "compressed"
    if compressed_dir.exists():
        mp3_path = compressed_dir / f"{base_name}.mp3"
        if mp3_path.exists():
            return mp3_path
    
    # Fallback: look for any .mp3 with same base name
    for mp3_file in transcription_path.parent.parent.rglob(f"{base_name}.mp3"):
        if "compressed" in mp3_file.parts or mp3_file.parent.name == "compressed":
            return mp3_file
    
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
    """Load and transform transcript JSON for react-transcript-editor."""
    with open(transcription_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Handle two possible formats:
    # 1. CorrectedDeepgramResponse format: raw_response at root
    # 2. Transcription cache format: raw_response nested under result
    raw_response = data.get('raw_response') or data.get('result', {}).get('raw_response', {})
    
    if not raw_response or 'results' not in raw_response:
        # Try to get raw_response from result.raw_response if it exists
        if 'result' in data and isinstance(data['result'], dict):
            raw_response = data['result'].get('raw_response', {})
        
        if not raw_response or 'results' not in raw_response:
            raise ValueError(f"Invalid transcript format in {transcription_path}. Expected raw_response with results.")
    
    channel = raw_response['results']['channels'][0]
    alternative = channel['alternatives'][0]
    words = alternative.get('words', [])
    
    # Transform words to format expected by react-transcript-editor
    transformed_words = []
    for idx, word in enumerate(words):
        transformed_words.append({
            'start': word.get('start', 0),
            'end': word.get('end', 0),
            'word': word.get('word', ''),
            'confidence': word.get('confidence', 0.9),
            'punct': word.get('punctuated_word', word.get('word', '')),
            'index': idx,
            'speaker': word.get('speaker', 0)
        })
    
    # Get speakers list - handle both formats
    speakers_list = data.get('speakers', []) or data.get('result', {}).get('speakers', [])
    unique_speakers = sorted(set(w.get('speaker', 0) for w in words))
    
    # Create a mapping from speaker identifiers to numbers for consistency
    speaker_id_to_num = {}
    next_speaker_num = 0
    for speaker_id in unique_speakers:
        if speaker_id not in speaker_id_to_num:
            speaker_id_to_num[speaker_id] = next_speaker_num
            next_speaker_num += 1
    
    # Also map all speaker identifiers from speakers_list
    for seg in speakers_list:
        speaker_id = seg.get('speaker', 'Speaker 0')
        if speaker_id not in speaker_id_to_num:
            speaker_id_to_num[speaker_id] = next_speaker_num
            next_speaker_num += 1
    
    segmentation = {
        'metadata': {'version': '0.0.10'},
        '@type': 'AudioFile',
        'speakers': [{'@id': f'S{sp}', 'gender': 'U'} for sp in range(len(speaker_id_to_num))],
        'segments': []
    }
    
    # Build segments from speaker segments
    for speaker_seg in speakers_list:
        speaker_id = speaker_seg.get('speaker', 'Speaker 0')
        speaker_num = speaker_id_to_num.get(speaker_id, extract_speaker_number(speaker_id))
        segmentation['segments'].append({
            '@type': 'Segment',
            'start': speaker_seg.get('start_time', 0),
            'duration': speaker_seg.get('end_time', 0) - speaker_seg.get('start_time', 0),
            'bandwidth': 'S',
            'speaker': {'@id': f'S{speaker_num}', 'gender': 'U'}
        })
    
    # Transform speaker segments
    transformed_speakers = []
    for seg in speakers_list:
        speaker_str = seg.get('speaker', 'Speaker 0')
        # Use the mapping to get consistent speaker numbers
        speaker_num = speaker_id_to_num.get(speaker_str, extract_speaker_number(speaker_str))
        
        transformed_speakers.append({
            'speaker': speaker_str,
            'start_time': seg.get('start_time', 0),
            'end_time': seg.get('end_time', 0),
            'text': seg.get('text', ''),
            'confidence': seg.get('confidence', 0.9)
        })
    
    # Build transcript text - handle both formats
    transcript_text = alternative.get('transcript', '') or data.get('text', '') or data.get('result', {}).get('text', '')
    
    # Get metadata - handle both formats
    audio_duration = (
        raw_response.get('metadata', {}).get('duration') or 
        data.get('audio_duration') or 
        data.get('result', {}).get('audio_duration', 0)
    )
    confidence = data.get('confidence') or data.get('result', {}).get('confidence', 0.9)
    
    result = {
        'words': transformed_words,
        'speakers': transformed_speakers,
        'segmentation': segmentation,
        'transcript': transcript_text,
        'metadata': {
            'duration': audio_duration,
            'confidence': confidence,
            'service': 'deepgram'
        }
    }
    
    # Add speaker names if available - handle both formats
    corrections = data.get('corrections') or data.get('result', {}).get('corrections', {})
    if corrections and 'speaker_names' in corrections:
        result['speaker_names'] = corrections['speaker_names']
    
    return result


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

