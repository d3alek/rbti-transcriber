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
HTML_TEMPLATE = r'''<!DOCTYPE html>
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

    <!-- React and ReactDOM from CDN (development versions for debugging) -->
    <script crossorigin src="https://unpkg.com/react@16/umd/react.development.js"></script>
    <script crossorigin src="https://unpkg.com/react-dom@16/umd/react-dom.development.js"></script>
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
            let transcriptData = {transcript_json};
            
            // Normalize raw Deepgram format to RichWordsTranscript format
            // Check if it's raw Deepgram format (not already RichWordsTranscript)
            if (!transcriptData.words || !Array.isArray(transcriptData.words)) {{
                console.log('🔄 Detected raw Deepgram format, converting to RichWordsTranscript...');
                
                // Find raw Deepgram response and preserve corrections
                let rawResponse = null;
                let preservedCorrections = null;
                
                if (transcriptData.raw_response && transcriptData.raw_response.results) {{
                    rawResponse = transcriptData.raw_response;
                    // Corrections might be at top level
                    preservedCorrections = transcriptData.corrections || null;
                }} else if (transcriptData.result && transcriptData.result.raw_response && transcriptData.result.raw_response.results) {{
                    rawResponse = transcriptData.result.raw_response;
                    // Preserve corrections from result or top level
                    preservedCorrections = transcriptData.result.corrections || transcriptData.corrections || null;
                }} else if (transcriptData.results && transcriptData.results.channels) {{
                    rawResponse = transcriptData;
                    // Corrections might be at top level
                    preservedCorrections = transcriptData.corrections || null;
                }}
                
                if (rawResponse) {{
                    // Extract words from raw Deepgram response
                    const results = rawResponse.results;
                    const channels = (results && results.channels) || [];
                    
                    if (channels.length > 0) {{
                        const channel = channels[0];
                        const alternatives = channel.alternatives || [];
                        
                        if (alternatives.length > 0) {{
                            const alternative = alternatives[0];
                            const words = alternative.words || [];
                            const paragraphs = (alternative.paragraphs && alternative.paragraphs.paragraphs) || [];
                            
                            if (words.length > 0) {{
                                // Initialize paragraph markers
                                const enrichedWords = words.map(word => ({{
                                    ...word,
                                    paragraph_start: false,
                                    paragraph_end: false
                                }}));
                                
                                // Mark paragraph boundaries (simplified version)
                                if (paragraphs && paragraphs.length > 0) {{
                                    for (let paraIdx = 0; paraIdx < paragraphs.length; paraIdx++) {{
                                        const paragraph = paragraphs[paraIdx];
                                        const sentences = paragraph.sentences || [];
                                        
                                        if (sentences.length > 0) {{
                                            // Mark paragraph start: first word of first sentence
                                            const firstSentence = sentences[0];
                                            const paraStartTime = firstSentence.start;
                                            
                                            if (paraStartTime !== undefined && paraStartTime !== null) {{
                                                // Find word closest to paragraph start time
                                                let bestMatch = null;
                                                let bestTimeDiff = Infinity;
                                                
                                                for (const word of enrichedWords) {{
                                                    const timeDiff = Math.abs((word.start || 0) - paraStartTime);
                                                    if (timeDiff < 0.1 && timeDiff < bestTimeDiff) {{
                                                        bestMatch = word;
                                                        bestTimeDiff = timeDiff;
                                                    }}
                                                }}
                                                
                                                if (bestMatch) {{
                                                    bestMatch.paragraph_start = true;
                                                    bestMatch.paragraph_end = false;
                                                }}
                                            }}
                                            
                                            // Mark paragraph end: last word of last sentence (only for last paragraph)
                                            if (paraIdx === paragraphs.length - 1) {{
                                                const lastSentence = sentences[sentences.length - 1];
                                                const paraEndTime = lastSentence.end;
                                                
                                                if (paraEndTime !== undefined && paraEndTime !== null) {{
                                                    let bestMatch = null;
                                                    let bestTimeDiff = Infinity;
                                                    
                                                    for (const word of enrichedWords) {{
                                                        if (word.paragraph_start) continue; // Skip paragraph starts
                                                        const timeDiff = Math.abs((word.end || 0) - paraEndTime);
                                                        if (timeDiff < 0.1 && timeDiff < bestTimeDiff) {{
                                                            bestMatch = word;
                                                            bestTimeDiff = timeDiff;
                                                        }}
                                                    }}
                                                    
                                                    if (bestMatch) {{
                                                        bestMatch.paragraph_end = true;
                                                    }}
                                                }}
                                            }}
                                        }}
                                    }}
                                }}
                                
                                // Convert to RichWordsTranscript format
                                transcriptData = {{
                                    words: enrichedWords,
                                    corrections: preservedCorrections || {{
                                        version: 1,
                                        timestamp: new Date().toISOString(),
                                        speaker_names: {{}}
                                    }}
                                }};
                                
                                console.log('✅ Converted raw Deepgram format to RichWordsTranscript');
                            }}
                        }}
                    }}
                }}
            }}
            
            // Ensure words have 'punct' field (required by Deepgram adapter)
            // The adapter expects 'punct' but transcript may have 'punctuated_word'
            if (transcriptData.words && Array.isArray(transcriptData.words)) {{
                transcriptData.words = transcriptData.words.map(word => {{
                    // Add 'punct' field if missing, using 'punctuated_word' or 'word' as fallback
                    if (!word.punct) {{
                        word.punct = word.punctuated_word || word.word || '';
                    }}
                    return word;
                }});
            }}
            
            // Extract speaker_names from corrections and add to top level
            // The Deepgram adapter expects speaker_names at the top level
            // corrections.speaker_names has string keys like "1", convert to numeric keys
            if (transcriptData.corrections && transcriptData.corrections.speaker_names) {{
                const correctionsSpeakerNames = transcriptData.corrections.speaker_names;
                
                // Initialize speaker_names if it doesn't exist, or use existing
                if (!transcriptData.speaker_names) {{
                    transcriptData.speaker_names = {{}};
                }}
                
                // Convert string keys to numbers and copy speaker names
                for (const [key, value] of Object.entries(correctionsSpeakerNames)) {{
                    const speakerIndex = parseInt(key, 10);
                    if (!isNaN(speakerIndex)) {{
                        transcriptData.speaker_names[speakerIndex] = value;
                    }}
                }}
            }}
            
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
                        // Get edited content from the editor in DraftJS format
                        const draftJsContent = this.editorRef.current.getEditorContent('draftjs');
                        
                        console.log('DraftJS content:', draftJsContent);
                        
                        if (!draftJsContent || !draftJsContent.data) {{
                            alert('Failed to get edited content - editor returned null/undefined');
                            this.setState({{ isSaving: false }});
                            return;
                        }}
                        
                        // Extract words from DraftJS format and convert to RichWordsTranscript
                        // Following the same logic as web-ui/src/components/TranscriptEditor/TranscriptEditor.tsx
                        const blocks = draftJsContent.data.blocks || [];
                        const allWords = [];
                        
                        // First pass: collect all unique speaker names in order they first appear
                        const uniqueSpeakers = [];
                        for (let blockIdx = 0; blockIdx < blocks.length; blockIdx++) {{
                            const block = blocks[blockIdx];
                            const blockData = block.data || {{}};
                            const blockSpeakerName = blockData.speaker;
                            if (blockSpeakerName && uniqueSpeakers.indexOf(blockSpeakerName) === -1) {{
                                uniqueSpeakers.push(blockSpeakerName);
                            }}
                        }}
                        
                        // Build mapping from original transcriptData - same as originalSpeakerMappingRef in web UI
                        // This maps ALL speaker names (default and custom) to their indices
                        const originalSpeakerNameToIndex = {{}};
                        
                        // Find all unique speaker indices from original words
                        const originalSpeakerIndices = new Set();
                        if (transcriptData.words && Array.isArray(transcriptData.words)) {{
                            transcriptData.words.forEach(word => {{
                                if (word.speaker !== undefined) {{
                                    originalSpeakerIndices.add(word.speaker);
                                    // Create default mapping for all speakers
                                    const defaultName = 'Speaker ' + word.speaker;
                                    if (originalSpeakerNameToIndex[defaultName] === undefined) {{
                                        originalSpeakerNameToIndex[defaultName] = word.speaker;
                                    }}
                                }}
                            }});
                        }}
                        
                        // Add custom speaker name mappings from transcriptData.speaker_names
                        // These override the default "Speaker X" mappings
                        if (transcriptData.speaker_names) {{
                            for (const [indexStr, name] of Object.entries(transcriptData.speaker_names)) {{
                                const speakerIndex = parseInt(indexStr);
                                originalSpeakerNameToIndex[name] = speakerIndex;
                            }}
                        }}
                        
                        // Build array of original speakers sorted by index (like originalSpeakersArray in web UI)
                        const originalSpeakersArray = [];
                        const sortedIndices = Array.from(originalSpeakerIndices).sort((a, b) => a - b);
                        sortedIndices.forEach(speakerIndex => {{
                            // Find the name for this index (custom name if exists, otherwise default)
                            let name = null;
                            if (transcriptData.speaker_names && transcriptData.speaker_names[speakerIndex] !== undefined) {{
                                name = transcriptData.speaker_names[speakerIndex];
                            }} else {{
                                name = 'Speaker ' + speakerIndex;
                            }}
                            originalSpeakersArray.push([name, speakerIndex]);
                        }});
                        
                        console.log('Original speaker name to index mapping:', originalSpeakerNameToIndex);
                        console.log('Original speakers array:', originalSpeakersArray);
                        
                        // Build reverse mapping: speaker name -> speaker index
                        // Following the same logic as web UI
                        const speakerNameToIndexMap = {{}};
                        const speakerNamesMap = {{}};
                        
                        // Single pass: map all speaker names
                        for (let blockIdx = 0; blockIdx < blocks.length; blockIdx++) {{
                            const block = blocks[blockIdx];
                            const blockData = block.data || {{}};
                            const blockSpeakerName = blockData.speaker;
                            
                            if (blockSpeakerName) {{
                                speakerNamesMap[blockSpeakerName] = blockSpeakerName;
                                
                                // Check if it's "Speaker X" format
                                const speakerMatch = blockSpeakerName.match(/^Speaker (\d+)$/);
                                if (speakerMatch) {{
                                    // It's a default "Speaker X" format
                                    speakerNameToIndexMap[blockSpeakerName] = parseInt(speakerMatch[1]);
                                }} else {{
                                    // It's a custom name - find its position in the unique list
                                    const positionInUniqueList = uniqueSpeakers.indexOf(blockSpeakerName);
                                    
                                    if (positionInUniqueList !== -1 && positionInUniqueList < originalSpeakersArray.length) {{
                                        // Map to the original speaker at the same position
                                        const speakerIndex = originalSpeakersArray[positionInUniqueList][1]; // Get the numeric index
                                        speakerNameToIndexMap[blockSpeakerName] = speakerIndex;
                                        console.log('Mapped custom name by position:', blockSpeakerName, '->', speakerIndex, '(position', positionInUniqueList, ')');
                                    }} else if (originalSpeakerNameToIndex[blockSpeakerName] !== undefined) {{
                                        // Fallback: look it up in original mapping (for existing custom names)
                                        speakerNameToIndexMap[blockSpeakerName] = originalSpeakerNameToIndex[blockSpeakerName];
                                        console.log('Mapped custom name from original:', blockSpeakerName, '->', originalSpeakerNameToIndex[blockSpeakerName]);
                                    }}
                                }}
                            }}
                        }}
                        
                        // Extract words from blocks
                        for (let blockIdx = 0; blockIdx < blocks.length; blockIdx++) {{
                            const block = blocks[blockIdx];
                            const blockData = block.data || {{}};
                            const blockWords = blockData.words || [];
                            const blockSpeakerName = blockData.speaker || 'Speaker 0';
                            
                            // Map speaker name to speaker index using the pre-built mapping
                            let speakerIndex = speakerNameToIndexMap[blockSpeakerName];
                            
                            // Fallback: if not in pre-built mapping, try other sources
                            if (speakerIndex === undefined) {{
                                // Check if it's "Speaker X" format
                                const speakerMatch = blockSpeakerName.match(/^Speaker (\d+)$/);
                                if (speakerMatch) {{
                                    speakerIndex = parseInt(speakerMatch[1]);
                                }} else {{
                                    // Look it up in current speaker_names mapping
                                    if (transcriptData.speaker_names) {{
                                        for (const [indexStr, name] of Object.entries(transcriptData.speaker_names)) {{
                                            if (name === blockSpeakerName) {{
                                                speakerIndex = parseInt(indexStr);
                                                break;
                                            }}
                                        }}
                                    }}
                                    
                                    // If still not found, try to get from word
                                    if (speakerIndex === undefined && blockWords.length > 0 && blockWords[0].speaker !== undefined) {{
                                        speakerIndex = blockWords[0].speaker;
                                    }}
                                    
                                    // Final fallback
                                    if (speakerIndex === undefined) {{
                                        speakerIndex = 0;
                                    }}
                                }}
                            }}
                            
                            // Convert words to RichWordsTranscript format
                            for (let wordIdx = 0; wordIdx < blockWords.length; wordIdx++) {{
                                const word = blockWords[wordIdx];
                                const isFirst = wordIdx === 0;
                                const isLast = wordIdx === blockWords.length - 1;
                                
                                allWords.push({{
                                    word: word.word || word.text || '',
                                    start: word.start,
                                    end: word.end,
                                    confidence: word.confidence || 0.9,
                                    speaker: speakerIndex,
                                    speaker_confidence: word.confidence || 0.9,
                                    punctuated_word: word.punct || word.word || word.text || '',
                                    paragraph_start: isFirst,
                                    paragraph_end: isLast,
                                    // Preserve correction metadata if present
                                    corrected: word.corrected,
                                    original_word: word.original_word,
                                    original_punct: word.original_punct
                                }});
                            }}
                        }}
                        
                        // Build customSpeakerNames using the pre-built mapping
                        // Only save custom names (not "Speaker X" format)
                        const customSpeakerNames = {{}};
                        console.log('Speaker names map:', speakerNamesMap);
                        console.log('Speaker name to index map:', speakerNameToIndexMap);
                        
                        for (const speakerName in speakerNamesMap) {{
                            if (speakerNamesMap.hasOwnProperty(speakerName)) {{
                                const speakerIndex = speakerNameToIndexMap[speakerName];
                                
                                // Only save if it's a custom name (not "Speaker X" format) and we found an index
                                if (speakerIndex !== undefined && !speakerName.match(/^Speaker \d+$/)) {{
                                    customSpeakerNames[speakerIndex] = speakerName;
                                    console.log('Added custom speaker name:', speakerIndex, '->', speakerName);
                                }} else {{
                                    console.log('Skipped speaker name:', speakerName, 'index:', speakerIndex, 'isSpeakerX:', !!speakerName.match(/^Speaker \d+$/));
                                }}
                            }}
                        }}
                        
                        console.log('Custom speaker names:', customSpeakerNames);
                        
                        // Merge with existing speaker_names from transcriptData
                        const mergedSpeakerNames = {{}};
                        if (transcriptData.speaker_names) {{
                            for (const [indexStr, name] of Object.entries(transcriptData.speaker_names)) {{
                                const idx = parseInt(indexStr);
                                mergedSpeakerNames[idx] = name;
                                console.log('Merged existing speaker name:', idx, '->', name);
                            }}
                        }}
                        // Add custom names from blocks (overwrites existing if same index)
                        for (const [indexStr, name] of Object.entries(customSpeakerNames)) {{
                            const idx = typeof indexStr === 'number' ? indexStr : parseInt(indexStr);
                            mergedSpeakerNames[idx] = name;
                            console.log('Merged custom speaker name:', idx, '->', name);
                        }}
                        
                        console.log('Final merged speaker names:', mergedSpeakerNames);
                        
                        // Get original corrections version (if available) and increment
                        const originalCorrections = originalTranscriptData.corrections || {{}};
                        const version = (originalCorrections.version || 0) + 1;
                        
                        // Build RichWordsTranscript format
                        const richWordsTranscript = {{
                            words: allWords,
                            corrections: {{
                                version: version,
                                timestamp: new Date().toISOString(),
                                speaker_names: Object.keys(mergedSpeakerNames).length > 0 ? mergedSpeakerNames : undefined
                            }}
                        }};
                        
                        // Remove undefined speaker_names if empty
                        if (!richWordsTranscript.corrections.speaker_names) {{
                            delete richWordsTranscript.corrections.speaker_names;
                        }}
                        
                        console.log('RichWordsTranscript:', richWordsTranscript);
                        
                        // Convert to JSON string and download
                        const jsonString = JSON.stringify(richWordsTranscript, null, 2);
                        const blob = new Blob([jsonString], {{ type: 'application/json;charset=utf-8' }});
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = '{audio_filename}_corrected.json';
                        
                        // Append to body, click, and remove
                        document.body.appendChild(a);
                        
                        // Use setTimeout to ensure the click happens after append
                        setTimeout(() => {{
                            a.click();
                            
                            // Clean up after a short delay
                            setTimeout(() => {{
                                document.body.removeChild(a);
                                window.URL.revokeObjectURL(url);
                            }}, 100);
                        }}, 0);
                        
                        alert('Corrections saved! File download started.');
                    }} catch (error) {{
                        console.error('Error saving:', error);
                        console.error('Error stack:', error.stack);
                        alert('Failed to save corrections: ' + (error.message || String(error)));
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
    # First format the template with safe fields (title, audio_filename)
    # Then replace transcript_json separately to avoid issues with curly braces in JSON
    transcript_json_str = json.dumps(transcript_data, indent=2)
    html_content = HTML_TEMPLATE.format(
        title=lecture_name,
        transcript_json='__TRANSCRIPT_JSON_PLACEHOLDER__',
        audio_filename=audio_filename
    )
    # Now replace the placeholder with the actual JSON (safe from format() parsing)
    html_content = html_content.replace('__TRANSCRIPT_JSON_PLACEHOLDER__', transcript_json_str)
    
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

