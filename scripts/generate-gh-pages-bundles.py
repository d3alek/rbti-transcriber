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

# Lightweight vanilla JS viewer template (default)
VIEWER_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Transcript</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            background: #f1f1f1;
            color: #333;
        }}
        
        .container {{
            background-color: #f1f1f1;
            min-height: 100vh;
        }}
        
        .header {{
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 1.5rem;
            font-weight: 500;
        }}
        
        .edit-button {{
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            text-decoration: none;
            display: inline-block;
        }}
        
        .edit-button:hover {{
            background-color: #45a049;
        }}
        
        .main-content {{
            display: flex;
            flex-direction: column;
            padding: 1rem;
            max-width: 1400px;
            margin: 0 auto;
            gap: 1rem;
        }}
        
        .audio-player-container {{
            background: white;
            box-shadow: 0 0 10px #ccc;
            padding: 1rem;
            border-radius: 4px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .audio-player {{
            width: 100%;
            outline: none;
        }}
        
        .transcript-container {{
            background: white;
            box-shadow: 0 0 10px #ccc;
            border-radius: 4px;
            overflow: hidden;
            flex: 1;
        }}
        
        .transcript-content {{
            max-height: calc(100vh - 200px);
            overflow-y: auto;
            padding: 8px 16px;
            background-color: white;
        }}
        
        .paragraph-block {{
            margin-bottom: 1em;
            display: grid;
            grid-template-columns: minmax(200px, 18%) 1fr;
            gap: 1%;
            padding: 0.5em 0;
        }}
        
        @media (max-width: 768px) {{
            .paragraph-block {{
                grid-template-columns: 1fr;
                margin-bottom: 0.5em;
            }}
        }}
        
        .speaker-label {{
            color: #7f8c8d;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.9em;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }}
        
        .paragraph-text {{
            font-size: 1em;
            line-height: 1.6;
        }}
        
        .word {{
            cursor: pointer;
            transition: background-color 0.2s;
            padding: 2px 1px;
            border-radius: 2px;
            display: inline-block;
            margin-right: 2px;
        }}
        
        .word:hover {{
            background-color: #e8f5e9;
        }}
        
        .word.current {{
            background-color: #69e3c2;
            text-shadow: 0 0 0.01px black;
        }}
        
        .word.played {{
            color: #767676;
        }}
        
        .word.low-confidence {{
            border-bottom: 1px dotted blue;
        }}
        
        .timecode {{
            font-weight: lighter;
            cursor: pointer;
            color: #666;
            font-size: 0.85em;
            margin-right: 0.5em;
        }}
        
        .timecode:hover {{
            text-decoration: underline;
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
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <a href="light-editor.html" class="edit-button" style="background-color: #2196F3;">✏️ EDIT</a>
        </div>
        
        <div class="main-content">
            <div class="audio-player-container">
                <audio id="audioPlayer" class="audio-player" controls preload="metadata">
                    <source src="./{audio_filename}" type="audio/webm">
                    <source src="./{audio_filename}" type="audio/opus">
                    Your browser does not support the audio element.
                </audio>
            </div>
            
            <div class="transcript-container">
                <div id="transcriptContent" class="transcript-content">
                    <div class="loading">Loading transcript...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Transcript data
        const transcriptData = {transcript_json};
        const audioPlayer = document.getElementById('audioPlayer');
        const transcriptContent = document.getElementById('transcriptContent');
        
        // Normalize transcript data to RichWordsTranscript format
        function normalizeTranscript(data) {{
            // Check if it's already RichWordsTranscript format
            if (data.words && Array.isArray(data.words)) {{
                return data;
            }}
            
            // Check if it's raw Deepgram format
            let rawResponse = null;
            let preservedCorrections = null;
            
            if (data.raw_response && data.raw_response.results) {{
                rawResponse = data.raw_response;
                preservedCorrections = data.corrections || null;
            }} else if (data.result && data.result.raw_response && data.result.raw_response.results) {{
                rawResponse = data.result.raw_response;
                preservedCorrections = data.result.corrections || data.corrections || null;
            }} else if (data.results && data.results.channels) {{
                rawResponse = data;
                preservedCorrections = data.corrections || null;
            }}
            
            if (rawResponse) {{
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
                            const enrichedWords = words.map(word => ({{
                                ...word,
                                paragraph_start: false,
                                paragraph_end: false
                            }}));
                            
                            // Mark paragraph boundaries
                            if (paragraphs && paragraphs.length > 0) {{
                                for (let paraIdx = 0; paraIdx < paragraphs.length; paraIdx++) {{
                                    const paragraph = paragraphs[paraIdx];
                                    const sentences = paragraph.sentences || [];
                                    
                                    if (sentences.length > 0) {{
                                        const firstSentence = sentences[0];
                                        const paraStartTime = firstSentence.start;
                                        
                                        if (paraStartTime !== undefined && paraStartTime !== null) {{
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
                                            }}
                                        }}
                                        
                                        if (paraIdx === paragraphs.length - 1) {{
                                            const lastSentence = sentences[sentences.length - 1];
                                            const paraEndTime = lastSentence.end;
                                            
                                            if (paraEndTime !== undefined && paraEndTime !== null) {{
                                                let bestMatch = null;
                                                let bestTimeDiff = Infinity;
                                                
                                                for (const word of enrichedWords) {{
                                                    if (word.paragraph_start) continue;
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
                            
                            return {{
                                words: enrichedWords,
                                corrections: preservedCorrections || {{
                                    version: 1,
                                    timestamp: new Date().toISOString(),
                                    speaker_names: {{}}
                                }}
                            }};
                        }}
                    }}
                }}
            }}
            
            throw new Error('Could not parse transcript data');
        }}
        
        // Get speaker name
        function getSpeakerName(speakerIndex, speakerNames) {{
            if (speakerNames && speakerNames[speakerIndex] !== undefined) {{
                return speakerNames[speakerIndex];
            }}
            return 'Speaker ' + speakerIndex;
        }}
        
        // Format timecode
        function formatTimecode(seconds) {{
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            const ms = Math.floor((seconds % 1) * 100);
            
            if (h > 0) {{
                return `${{h}}:${{String(m).padStart(2, '0')}}:${{String(s).padStart(2, '0')}}.${{String(ms).padStart(2, '0')}}`;
            }}
            return `${{m}}:${{String(s).padStart(2, '0')}}.${{String(ms).padStart(2, '0')}}`;
        }}
        
        // Render transcript
        function renderTranscript() {{
            try {{
                const normalized = normalizeTranscript(transcriptData);
                const words = normalized.words || [];
                const speakerNames = normalized.corrections?.speaker_names || {{}};
                
                if (words.length === 0) {{
                    transcriptContent.innerHTML = '<div class="loading">No transcript data available</div>';
                    return;
                }}
                
                // Group words into paragraphs based on paragraph_start markers
                const paragraphs = [];
                let currentParagraph = null;
                
                words.forEach((word, index) => {{
                    // Start a new paragraph if this word marks a paragraph start
                    if (word.paragraph_start) {{
                        // Save previous paragraph if it exists
                        if (currentParagraph && currentParagraph.words.length > 0) {{
                            paragraphs.push(currentParagraph);
                        }}
                        // Start new paragraph
                        currentParagraph = {{
                            speaker: word.speaker || 0,
                            startTime: word.start || 0,
                            words: []
                        }};
                    }}
                    
                    // If no paragraph started yet, start one
                    if (!currentParagraph) {{
                        currentParagraph = {{
                            speaker: word.speaker || 0,
                            startTime: word.start || 0,
                            words: []
                        }};
                    }}
                    
                    // Add word to current paragraph
                    currentParagraph.words.push(word);
                    
                    // End paragraph if this word marks paragraph end
                    if (word.paragraph_end) {{
                        paragraphs.push(currentParagraph);
                        currentParagraph = null;
                    }}
                }});
                
                // Don't forget the last paragraph if it wasn't ended
                if (currentParagraph && currentParagraph.words.length > 0) {{
                    paragraphs.push(currentParagraph);
                }}
                
                // Render paragraphs
                let html = '';
                paragraphs.forEach((para, paraIdx) => {{
                    const speakerName = getSpeakerName(para.speaker, speakerNames);
                    const timecode = formatTimecode(para.startTime);
                    
                    html += '<div class="paragraph-block">';
                    html += `  <div class="speaker-label">${{speakerName}}</div>`;
                    html += '  <div class="paragraph-text">';
                    html += `    <span class="timecode" data-time="${{para.startTime}}">${{timecode}}</span>`;
                    
                    para.words.forEach((word, wordIdx) => {{
                        const punct = word.punctuated_word || word.punct || word.word || '';
                        const confidence = word.confidence || 0.9;
                        const isLowConfidence = confidence < 0.7;
                        const wordClasses = ['word'];
                        if (isLowConfidence) wordClasses.push('low-confidence');
                        
                        html += `<span class="${{wordClasses.join(' ')}}" data-start="${{word.start}}" data-end="${{word.end}}" data-prev-times="${{Math.floor(word.start)}} ${{Math.floor(word.end)}}">${{punct}}</span>`;
                    }});
                    
                    html += '  </div>';
                    html += '</div>';
                }});
                
                transcriptContent.innerHTML = html;
                
                // Attach word click handlers
                document.querySelectorAll('.word').forEach(wordEl => {{
                    wordEl.addEventListener('click', function() {{
                        const startTime = parseFloat(this.dataset.start);
                        if (audioPlayer && !isNaN(startTime)) {{
                            audioPlayer.currentTime = startTime;
                            audioPlayer.play();
                        }}
                    }});
                }});
                
                // Attach timecode click handlers
                document.querySelectorAll('.timecode').forEach(timecodeEl => {{
                    timecodeEl.addEventListener('click', function() {{
                        const time = parseFloat(this.dataset.time);
                        if (audioPlayer && !isNaN(time)) {{
                            audioPlayer.currentTime = time;
                            audioPlayer.play();
                        }}
                    }});
                }});
                
                // Update word highlighting based on audio playback
                let currentWordElement = null;
                
                function updateHighlighting() {{
                    const currentTime = audioPlayer.currentTime;
                    const time = Math.round(currentTime * 4.0) / 4.0;
                    
                    // Remove previous highlighting
                    if (currentWordElement) {{
                        currentWordElement.classList.remove('current');
                    }}
                    
                    // Find current word
                    document.querySelectorAll('.word').forEach(wordEl => {{
                        const start = parseFloat(wordEl.dataset.start);
                        const end = parseFloat(wordEl.dataset.end);
                        
                        if (currentTime >= start && currentTime < end) {{
                            wordEl.classList.add('current');
                            currentWordElement = wordEl;
                            
                            // Scroll into view
                            wordEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                        }} else {{
                            wordEl.classList.remove('current');
                        }}
                        
                        // Mark played words
                        if (currentTime >= end) {{
                            wordEl.classList.add('played');
                        }} else {{
                            wordEl.classList.remove('played');
                        }}
                    }});
                }}
                
                audioPlayer.addEventListener('timeupdate', updateHighlighting);
                audioPlayer.addEventListener('loadedmetadata', updateHighlighting);
                
            }} catch (error) {{
                console.error('Error rendering transcript:', error);
                transcriptContent.innerHTML = '<div class="loading" style="color: red;">Error loading transcript: ' + error.message + '</div>';
            }}
        }}
        
        // Render viewer
        renderTranscript();
    </script>
</body>
</html>
'''

# Light editor template (lightweight vanilla JS with editing capability)
LIGHT_EDITOR_TEMPLATE = r'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - Light Editor</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue',
                sans-serif;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            background: #f1f1f1;
            color: #333;
        }}
        
        .container {{
            background-color: #f1f1f1;
            min-height: 100vh;
        }}
        
        .header {{
            background: #2c3e50;
            color: white;
            padding: 1rem 2rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            font-size: 1.5rem;
            font-weight: 500;
        }}
        
        .header-buttons {{
            display: flex;
            gap: 10px;
        }}
        
        .button {{
            color: white;
            border: none;
            padding: 10px 20px;
            font-size: 16px;
            cursor: pointer;
            border-radius: 4px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            text-decoration: none;
            display: inline-block;
        }}
        
        .back-button {{
            background-color: #6c757d;
        }}
        
        .back-button:hover {{
            background-color: #5a6268;
        }}
        
        .save-button {{
            background-color: #4CAF50;
        }}
        
        .save-button:hover {{
            background-color: #45a049;
        }}
        
        .save-button:disabled {{
            background-color: #cccccc;
            cursor: not-allowed;
        }}
        
        .main-content {{
            display: flex;
            flex-direction: column;
            padding: 1rem;
            max-width: 1400px;
            margin: 0 auto;
            gap: 1rem;
        }}
        
        .audio-player-container {{
            background: white;
            box-shadow: 0 0 10px #ccc;
            padding: 1rem;
            border-radius: 4px;
            position: sticky;
            top: 0;
            z-index: 100;
        }}
        
        .audio-player {{
            width: 100%;
            outline: none;
        }}
        
        .transcript-container {{
            background: white;
            box-shadow: 0 0 10px #ccc;
            border-radius: 4px;
            overflow: hidden;
            flex: 1;
        }}
        
        .transcript-content {{
            max-height: calc(100vh - 200px);
            overflow-y: auto;
            padding: 8px 16px;
            background-color: white;
        }}
        
        .paragraph-block {{
            margin-bottom: 1em;
            display: grid;
            grid-template-columns: minmax(200px, 18%) 1fr;
            gap: 1%;
            padding: 0.5em 0;
        }}
        
        @media (max-width: 768px) {{
            .paragraph-block {{
                grid-template-columns: 1fr;
                margin-bottom: 0.5em;
            }}
        }}
        
        .speaker-label {{
            color: #7f8c8d;
            font-weight: bold;
            text-transform: uppercase;
            font-size: 0.9em;
            text-overflow: ellipsis;
            overflow: hidden;
            white-space: nowrap;
        }}
        
        .paragraph-text {{
            font-size: 1em;
            line-height: 1.6;
        }}
        
        .word {{
            cursor: pointer;
            transition: background-color 0.2s;
            padding: 2px 1px;
            border-radius: 2px;
            display: inline-block;
            margin-right: 2px;
            position: relative;
        }}
        
        .word:hover {{
            background-color: #e8f5e9;
        }}
        
        .word.current {{
            background-color: #69e3c2;
            text-shadow: 0 0 0.01px black;
        }}
        
        .word.played {{
            color: #767676;
        }}
        
        .word.low-confidence {{
            border-bottom: 1px dotted blue;
        }}
        
        .word.editing {{
            background-color: #fff3cd;
            outline: 2px solid #ffc107;
        }}
        
        .word.corrected {{
            background-color: #d4edda;
        }}
        
        .word-input {{
            display: inline-block;
            border: 2px solid #ffc107;
            background: white;
            padding: 2px 4px;
            font-size: inherit;
            font-family: inherit;
            border-radius: 2px;
            min-width: 50px;
            outline: none;
        }}
        
        .timecode {{
            font-weight: lighter;
            cursor: pointer;
            color: #666;
            font-size: 0.85em;
            margin-right: 0.5em;
        }}
        
        .timecode:hover {{
            text-decoration: underline;
        }}
        
        .loading {{
            display: flex;
            align-items: center;
            justify-content: center;
            height: 100vh;
            font-size: 18px;
            color: #666;
        }}
        
        .edit-mode-hint {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px 16px;
            margin: 0 16px 16px 16px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        
        .modal-overlay {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
        }}
        
        .modal {{
            background: white;
            border-radius: 8px;
            padding: 24px;
            max-width: 500px;
            width: 90%;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }}
        
        .modal h2 {{
            margin: 0 0 16px 0;
            font-size: 1.5rem;
            color: #2c3e50;
        }}
        
        .modal label {{
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #333;
        }}
        
        .modal input {{
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 4px;
            font-size: 16px;
            box-sizing: border-box;
            margin-bottom: 16px;
        }}
        
        .modal input:focus {{
            outline: none;
            border-color: #3498db;
        }}
        
        .modal-actions {{
            display: flex;
            gap: 10px;
            justify-content: flex-end;
            margin-top: 20px;
        }}
        
        .modal-button {{
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            font-size: 16px;
            cursor: pointer;
            transition: background-color 0.2s;
        }}
        
        .modal-button-primary {{
            background-color: #3498db;
            color: white;
        }}
        
        .modal-button-primary:hover {{
            background-color: #2980b9;
        }}
        
        .modal-button-secondary {{
            background-color: #95a5a6;
            color: white;
        }}
        
        .modal-button-secondary:hover {{
            background-color: #7f8c8d;
        }}
        
        .modal-button-danger {{
            background-color: #e74c3c;
            color: white;
        }}
        
        .modal-button-danger:hover {{
            background-color: #c0392b;
        }}
        
        .modal-checkbox {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin: 16px 0;
        }}
        
        .modal-checkbox input[type="checkbox"] {{
            width: auto;
            margin: 0;
        }}
        
        .speaker-label {{
            cursor: pointer;
            transition: background-color 0.2s;
            padding: 2px 4px;
            border-radius: 3px;
        }}
        
        .speaker-label:hover {{
            background-color: #e8f5e9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title} - Light Editor</h1>
            <div class="header-buttons">
                <a href="index.html" class="button back-button">← Back to Viewer</a>
                <button id="resetButton" class="button reset-button" onclick="resetEdits()" style="background-color: #dc3545; margin-right: 10px;">🔄 Reset Edits</button>
                <button id="saveButton" class="button save-button" onclick="saveCorrections()">💾 Save Corrections</button>
            </div>
    </div>

        <div class="main-content">
            <div class="audio-player-container">
                <audio id="audioPlayer" class="audio-player" controls preload="metadata">
                    <source src="./{audio_filename}" type="audio/webm">
                    <source src="./{audio_filename}" type="audio/opus">
                    Your browser does not support the audio element.
                </audio>
            </div>
            
            <div class="transcript-container">
                <div class="edit-mode-hint">
                    💡 <strong>Edit Mode:</strong> Click a word to play audio or double-click to edit. Click speaker name to edit it. Corrected words are highlighted in green.
                </div>
                <div id="transcriptContent" class="transcript-content">
                    <div class="loading">Loading transcript...</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // Transcript data
        let transcriptData = {transcript_json};
        const STORAGE_KEY = 'transcript_edits_' + '{audio_filename}';
        let originalWords = []; // Store original word data
        let wordCorrections = new Map(); // Map word index to corrections
        let speakerNameChanges = new Map(); // Map speaker index to new name (for "replace all")
        let paragraphSpeakerChanges = new Map(); // Map paragraph index to new speaker index and name (for single paragraph)
        const audioPlayer = document.getElementById('audioPlayer');
        const transcriptContent = document.getElementById('transcriptContent');
        const saveButton = document.getElementById('saveButton');
        const resetButton = document.getElementById('resetButton');
        
        // Save edits to localStorage
        function saveEditsToStorage() {{
            try {{
                const edits = {{
                    wordCorrections: Array.from(wordCorrections.entries()),
                    speakerNameChanges: Array.from(speakerNameChanges.entries()),
                    paragraphSpeakerChanges: Array.from(paragraphSpeakerChanges.entries())
                }};
                localStorage.setItem(STORAGE_KEY, JSON.stringify(edits));
                console.log('Edits saved to localStorage');
            }} catch (error) {{
                console.error('Error saving edits to localStorage:', error);
            }}
        }}
        
        // Load edits from localStorage
        function loadEditsFromStorage() {{
            try {{
                const saved = localStorage.getItem(STORAGE_KEY);
                if (saved) {{
                    const edits = JSON.parse(saved);
                    
                    // Restore wordCorrections
                    if (edits.wordCorrections && Array.isArray(edits.wordCorrections)) {{
                        wordCorrections = new Map(edits.wordCorrections);
                    }}
                    
                    // Restore speakerNameChanges
                    if (edits.speakerNameChanges && Array.isArray(edits.speakerNameChanges)) {{
                        speakerNameChanges = new Map(edits.speakerNameChanges);
                    }}
                    
                    // Restore paragraphSpeakerChanges
                    if (edits.paragraphSpeakerChanges && Array.isArray(edits.paragraphSpeakerChanges)) {{
                        // Convert array entries back to objects
                        paragraphSpeakerChanges = new Map(
                            edits.paragraphSpeakerChanges.map(([key, value]) => [Number(key), value])
                        );
                    }}
                    
                    console.log('Edits loaded from localStorage:', {{
                        wordCorrections: wordCorrections.size,
                        speakerNameChanges: speakerNameChanges.size,
                        paragraphSpeakerChanges: paragraphSpeakerChanges.size
                    }});
                    return true;
                }}
            }} catch (error) {{
                console.error('Error loading edits from localStorage:', error);
            }}
            return false;
        }}
        
        // Reset edits (clear localStorage and reload)
        function resetEdits() {{
            if (!confirm('Are you sure you want to reset all edits? This will clear all corrections and reload the original transcript.')) {{
                return;
            }}
            
            try {{
                localStorage.removeItem(STORAGE_KEY);
                wordCorrections.clear();
                speakerNameChanges.clear();
                paragraphSpeakerChanges.clear();
                console.log('Edits reset - localStorage cleared');
                
                // Re-render transcript to show original state
                renderTranscript();
                
                alert('All edits have been reset. The transcript has been reloaded to its original state.');
            }} catch (error) {{
                console.error('Error resetting edits:', error);
                alert('Error resetting edits: ' + error.message);
            }}
        }}
        
        // Normalize transcript data to RichWordsTranscript format
        function normalizeTranscript(data) {{
            // Check if it's already RichWordsTranscript format
            if (data.words && Array.isArray(data.words)) {{
                return data;
            }}
            
            // Check if it's raw Deepgram format
                let rawResponse = null;
                let preservedCorrections = null;
                
            if (data.raw_response && data.raw_response.results) {{
                rawResponse = data.raw_response;
                preservedCorrections = data.corrections || null;
            }} else if (data.result && data.result.raw_response && data.result.raw_response.results) {{
                rawResponse = data.result.raw_response;
                preservedCorrections = data.result.corrections || data.corrections || null;
            }} else if (data.results && data.results.channels) {{
                rawResponse = data;
                preservedCorrections = data.corrections || null;
                }}
                
                if (rawResponse) {{
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
                                const enrichedWords = words.map(word => ({{
                                    ...word,
                                    paragraph_start: false,
                                    paragraph_end: false
                                }}));
                                
                            // Mark paragraph boundaries
                                if (paragraphs && paragraphs.length > 0) {{
                                    for (let paraIdx = 0; paraIdx < paragraphs.length; paraIdx++) {{
                                        const paragraph = paragraphs[paraIdx];
                                        const sentences = paragraph.sentences || [];
                                        
                                        if (sentences.length > 0) {{
                                            const firstSentence = sentences[0];
                                            const paraStartTime = firstSentence.start;
                                            
                                            if (paraStartTime !== undefined && paraStartTime !== null) {{
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
                                                }}
                                            }}
                                            
                                            if (paraIdx === paragraphs.length - 1) {{
                                                const lastSentence = sentences[sentences.length - 1];
                                                const paraEndTime = lastSentence.end;
                                                
                                                if (paraEndTime !== undefined && paraEndTime !== null) {{
                                                    let bestMatch = null;
                                                    let bestTimeDiff = Infinity;
                                                    
                                                    for (const word of enrichedWords) {{
                                                    if (word.paragraph_start) continue;
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
                                
                            return {{
                                    words: enrichedWords,
                                    corrections: preservedCorrections || {{
                                        version: 1,
                                        timestamp: new Date().toISOString(),
                                        speaker_names: {{}}
                                    }}
                                }};
                            }}
                        }}
                    }}
                }}
            
            throw new Error('Could not parse transcript data');
        }}
        
        // Get speaker name
        function getSpeakerName(speakerIndex, speakerNames) {{
            if (speakerNames && speakerNames[speakerIndex] !== undefined) {{
                return speakerNames[speakerIndex];
            }}
            return 'Speaker ' + speakerIndex;
        }}
        
        // Format timecode
        function formatTimecode(seconds) {{
            const h = Math.floor(seconds / 3600);
            const m = Math.floor((seconds % 3600) / 60);
            const s = Math.floor(seconds % 60);
            const ms = Math.floor((seconds % 1) * 100);
            
            if (h > 0) {{
                return `${{h}}:${{String(m).padStart(2, '0')}}:${{String(s).padStart(2, '0')}}.${{String(ms).padStart(2, '0')}}`;
            }}
            return `${{m}}:${{String(s).padStart(2, '0')}}.${{String(ms).padStart(2, '0')}}`;
        }}
        
        // Normalize word: lowercase and strip punctuation (for 'word' field)
        function normalizeWord(wordText) {{
            if (!wordText) return wordText;
            // Convert to lowercase and remove punctuation
            return wordText.toLowerCase().trim().replace(/[.,!?;:"()\\[\\]{{}}]+/g, '');
        }}
        
        // Get speaker name (with applied changes) for a specific paragraph
        function getSpeakerName(speakerIndex, speakerNames, paragraphIndex) {{
            // Check if this specific paragraph has a speaker change
            if (paragraphIndex !== undefined && paragraphSpeakerChanges.has(paragraphIndex)) {{
                const change = paragraphSpeakerChanges.get(paragraphIndex);
                return change.name;
            }}
            // Check if speaker name was changed globally (replace all)
            if (speakerNameChanges.has(speakerIndex)) {{
                return speakerNameChanges.get(speakerIndex);
            }}
            // Check original speaker names
            if (speakerNames && speakerNames[speakerIndex] !== undefined) {{
                return speakerNames[speakerIndex];
            }}
            return 'Speaker ' + speakerIndex;
        }}
        
        // Show speaker editor modal
        function showSpeakerEditor(speakerIndex, currentName, paragraphIndex) {{
            // Create modal overlay
            const overlay = document.createElement('div');
            overlay.className = 'modal-overlay';
            overlay.id = 'speakerModalOverlay';
            
            const modal = document.createElement('div');
            modal.className = 'modal';
            
            // Escape quotes in currentName for HTML
            const escapedName = currentName.replace(/'/g, "\\'").replace(/"/g, "&quot;");
            
            modal.innerHTML = `
                <h2>Edit Speaker</h2>
                <label for="speakerNameInput">Speaker Name:</label>
                <input type="text" id="speakerNameInput" value="${{escapedName}}" placeholder="Enter speaker name">
                <div class="modal-checkbox">
                    <input type="checkbox" id="replaceAllCheckbox">
                    <label for="replaceAllCheckbox">Replace all occurrences of "${{escapedName}}" with new name</label>
                </div>
                <div class="modal-actions">
                    <button class="modal-button modal-button-secondary" onclick="closeSpeakerModal()">Cancel</button>
                    <button class="modal-button modal-button-primary" onclick="saveSpeakerChange(${{speakerIndex}}, ${{paragraphIndex !== undefined && paragraphIndex !== null ? paragraphIndex : 'undefined'}})">Save</button>
                </div>
            `;
            
            overlay.appendChild(modal);
            document.body.appendChild(overlay);
            
            // Close on overlay click
            overlay.addEventListener('click', function(e) {{
                if (e.target === overlay) {{
                    closeSpeakerModal();
                }}
            }});
            
            // Focus input
            setTimeout(() => {{
                const input = document.getElementById('speakerNameInput');
                input.focus();
                input.select();
                
                // Handle Enter key
                input.addEventListener('keydown', function(e) {{
                    if (e.key === 'Enter') {{
                        e.preventDefault();
                        saveSpeakerChange(speakerIndex, paragraphIndex);
                    }} else if (e.key === 'Escape') {{
                        e.preventDefault();
                        closeSpeakerModal();
                    }}
                }});
            }}, 100);
        }}
        
        // Close speaker modal
        function closeSpeakerModal() {{
            const overlay = document.getElementById('speakerModalOverlay');
            if (overlay) {{
                overlay.remove();
            }}
        }}
        
        // Save speaker change
        function saveSpeakerChange(speakerIndex, paragraphIndex) {{
            const input = document.getElementById('speakerNameInput');
            const replaceAll = document.getElementById('replaceAllCheckbox').checked;
            const newName = input.value.trim();
            
            if (!newName) {{
                alert('Speaker name cannot be empty');
                            return;
                        }}
                        
            const normalized = normalizeTranscript(transcriptData);
            const speakerNames = normalized.corrections?.speaker_names || {{}};
            const currentName = getSpeakerName(speakerIndex, speakerNames, paragraphIndex);
            
            if (replaceAll) {{
                // Find all speaker indices that have the same name
                const words = normalized.words || [];
                const speakersToReplace = new Set();
                speakersToReplace.add(speakerIndex);
                
                // Find all speakers with the same name
                for (let i = 0; i < words.length; i++) {{
                    const word = words[i];
                    if (word.speaker !== undefined && word.speaker === speakerIndex) {{
                        speakersToReplace.add(word.speaker);
                    }}
                }}
                
                // Replace all matching speakers globally
                speakersToReplace.forEach(speakerIdx => {{
                    speakerNameChanges.set(speakerIdx, newName);
                }});
                
                // Don't delete paragraph-specific changes when doing "replace all"
                // Paragraph-specific changes create a NEW unique speaker index for those paragraphs,
                // making them independent from the original speaker. They should NOT be affected by
                // global "replace all" operations on the original speaker.
                // The paragraph-specific changes will remain intact, and those paragraphs will keep
                // their custom speaker names.
            }} else {{
                // Only replace this specific paragraph
                // Check that paragraphIndex is valid
                if (paragraphIndex === undefined || paragraphIndex === null) {{
                    alert('Error: Paragraph index is required for single paragraph changes');
                    return;
                }}
                
                // Find the next available speaker index (use a high number to avoid conflicts)
                let newSpeakerIndex = speakerIndex;
                const existingIndices = new Set();
                const words = normalized.words || [];
                words.forEach(word => {{
                                if (word.speaker !== undefined) {{
                        existingIndices.add(word.speaker);
                                }}
                            }});
                paragraphSpeakerChanges.forEach(change => {{
                    existingIndices.add(change.newSpeakerIndex);
                }});
                
                // Find next available index starting from max + 1
                const maxIndex = Math.max(...Array.from(existingIndices), 0);
                newSpeakerIndex = maxIndex + 1;
                while (existingIndices.has(newSpeakerIndex)) {{
                    newSpeakerIndex++;
                }}
                
                paragraphSpeakerChanges.set(paragraphIndex, {{
                    originalSpeakerIndex: speakerIndex,
                    newSpeakerIndex: newSpeakerIndex,
                    name: newName
                }});
            }}
            
            closeSpeakerModal();
            saveEditsToStorage(); // Save to localStorage after speaker change
            // Re-render transcript to show updated speaker names
            renderTranscript();
        }}
        
        // Edit word
        function editWord(wordIndex, wordElement) {{
            const word = originalWords[wordIndex];
            if (!word) return;
            
            // Pause audio playback when entering edit mode
            if (audioPlayer && !audioPlayer.paused) {{
                audioPlayer.pause();
            }}
            
            const originalText = word.punctuated_word || word.punct || word.word || '';
            const input = document.createElement('input');
            input.type = 'text';
            input.className = 'word-input';
            input.value = originalText;
            input.style.width = (wordElement.offsetWidth + 10) + 'px';
            
            wordElement.classList.add('editing');
            wordElement.style.display = 'none';
            wordElement.parentNode.insertBefore(input, wordElement);
            input.focus();
            input.select();
            
            function finishEdit() {{
                const newText = input.value.trim();
                if (newText && newText !== originalText) {{
                    // Word was corrected
                    wordCorrections.set(wordIndex, {{
                        original_word: word.word || '',
                        original_punct: originalText,
                        corrected_word: newText
                    }});
                    wordElement.textContent = newText;
                    wordElement.classList.add('corrected');
                    wordElement.classList.remove('editing');
                    saveEditsToStorage(); // Save to localStorage
                                }} else {{
                    wordElement.classList.remove('editing');
                }}
                input.remove();
                wordElement.style.display = '';
            }}
            
            input.addEventListener('blur', finishEdit);
            input.addEventListener('keydown', function(e) {{
                if (e.key === 'Enter') {{
                    e.preventDefault();
                    finishEdit();
                }} else if (e.key === 'Escape') {{
                    e.preventDefault();
                    input.value = originalText;
                    finishEdit();
                }}
            }});
        }}
        
        // Render transcript
        function renderTranscript() {{
            try {{
                const normalized = normalizeTranscript(transcriptData);
                const words = normalized.words || [];
                originalWords = [...words]; // Store original words
                const speakerNames = normalized.corrections?.speaker_names || {{}};
                
                if (words.length === 0) {{
                    transcriptContent.innerHTML = '<div class="loading">No transcript data available</div>';
                    return;
                }}
                
                // Group words into paragraphs based on paragraph_start markers
                const paragraphs = [];
                let currentParagraph = null;
                
                words.forEach((word, index) => {{
                    // Start a new paragraph if this word marks a paragraph start
                    if (word.paragraph_start) {{
                        // Save previous paragraph if it exists
                        if (currentParagraph && currentParagraph.words.length > 0) {{
                            paragraphs.push(currentParagraph);
                        }}
                        // Start new paragraph
                        currentParagraph = {{
                            speaker: word.speaker || 0,
                            startTime: word.start || 0,
                            words: []
                        }};
                    }}
                    
                    // If no paragraph started yet, start one
                    if (!currentParagraph) {{
                        currentParagraph = {{
                            speaker: word.speaker || 0,
                            startTime: word.start || 0,
                            words: []
                        }};
                    }}
                    
                    // Add word to current paragraph
                    currentParagraph.words.push(word);
                    
                    // End paragraph if this word marks paragraph end
                    if (word.paragraph_end) {{
                        paragraphs.push(currentParagraph);
                        currentParagraph = null;
                    }}
                }});
                
                // Don't forget the last paragraph if it wasn't ended
                if (currentParagraph && currentParagraph.words.length > 0) {{
                    paragraphs.push(currentParagraph);
                }}
                
                // Build word index map for paragraphs
                let globalWordIndex = 0;
                
                // Render paragraphs
                let html = '';
                paragraphs.forEach((para, paraIdx) => {{
                    // Check if this paragraph has a speaker change
                    const paraSpeakerIndex = paragraphSpeakerChanges.has(paraIdx) 
                        ? paragraphSpeakerChanges.get(paraIdx).newSpeakerIndex 
                        : para.speaker;
                    const speakerName = getSpeakerName(para.speaker, speakerNames, paraIdx);
                    const timecode = formatTimecode(para.startTime);
                    // Escape quotes for onclick attribute
                    const escapedSpeakerName = speakerName.replace(/'/g, "\\'").replace(/"/g, '&quot;');
                    
                    html += '<div class="paragraph-block">';
                    html += `  <div class="speaker-label" data-speaker-index="${{paraSpeakerIndex}}" data-paragraph-index="${{paraIdx}}" onclick="showSpeakerEditor(${{para.speaker}}, '${{escapedSpeakerName}}', ${{paraIdx}})">${{speakerName}}</div>`;
                    html += '  <div class="paragraph-text">';
                    html += `    <span class="timecode" data-time="${{para.startTime}}">${{timecode}}</span>`;
                    
                    para.words.forEach((word, wordIdx) => {{
                        const wordIndex = globalWordIndex++;
                        const correction = wordCorrections.get(wordIndex);
                        const displayText = correction ? correction.corrected_word : (word.punctuated_word || word.punct || word.word || '');
                        const confidence = word.confidence || 0.9;
                        const isLowConfidence = confidence < 0.7;
                        const isCorrected = correction !== undefined;
                        const wordClasses = ['word'];
                        if (isLowConfidence) wordClasses.push('low-confidence');
                        if (isCorrected) wordClasses.push('corrected');
                        
                        html += `<span class="${{wordClasses.join(' ')}}" data-word-index="${{wordIndex}}" data-start="${{word.start}}" data-end="${{word.end}}" data-prev-times="${{Math.floor(word.start)}} ${{Math.floor(word.end)}}">${{displayText}}</span>`;
                    }});
                    
                    html += '  </div>';
                    html += '</div>';
                }});
                
                transcriptContent.innerHTML = html;
                
                // Attach word click handlers
                document.querySelectorAll('.word').forEach(wordEl => {{
                    let clickTimeout;
                    let clickCount = 0;
                    
                    wordEl.addEventListener('click', function() {{
                        clickCount++;
                        clearTimeout(clickTimeout);
                        
                        clickTimeout = setTimeout(function() {{
                            if (clickCount === 1) {{
                                // Single click: play audio
                                const startTime = parseFloat(wordEl.dataset.start);
                                if (audioPlayer && !isNaN(startTime)) {{
                                    audioPlayer.currentTime = startTime;
                                    audioPlayer.play();
                                }}
                            }}
                            clickCount = 0;
                        }}, 300);
                    }});
                    
                    wordEl.addEventListener('dblclick', function(e) {{
                        e.preventDefault();
                        clearTimeout(clickTimeout);
                        clickCount = 0;
                        // Double click: edit word
                        const wordIndex = parseInt(wordEl.dataset.wordIndex);
                        editWord(wordIndex, wordEl);
                    }});
                }});
                
                // Attach timecode click handlers
                document.querySelectorAll('.timecode').forEach(timecodeEl => {{
                    timecodeEl.addEventListener('click', function() {{
                        const time = parseFloat(this.dataset.time);
                        if (audioPlayer && !isNaN(time)) {{
                            audioPlayer.currentTime = time;
                            audioPlayer.play();
                        }}
                    }});
                }});
                
                // Update word highlighting based on audio playback
                let currentWordElement = null;
                
                function updateHighlighting() {{
                    const currentTime = audioPlayer.currentTime;
                    const time = Math.round(currentTime * 4.0) / 4.0;
                    
                    // Remove previous highlighting
                    if (currentWordElement) {{
                        currentWordElement.classList.remove('current');
                    }}
                    
                    // Find current word
                    document.querySelectorAll('.word').forEach(wordEl => {{
                        const start = parseFloat(wordEl.dataset.start);
                        const end = parseFloat(wordEl.dataset.end);
                        
                        if (currentTime >= start && currentTime < end) {{
                            wordEl.classList.add('current');
                            currentWordElement = wordEl;
                            
                            // Scroll into view
                            wordEl.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                                }} else {{
                            wordEl.classList.remove('current');
                        }}
                        
                        // Mark played words
                        if (currentTime >= end) {{
                            wordEl.classList.add('played');
                        }} else {{
                            wordEl.classList.remove('played');
                        }}
                    }});
                }}
                
                audioPlayer.addEventListener('timeupdate', updateHighlighting);
                audioPlayer.addEventListener('loadedmetadata', updateHighlighting);
                
            }} catch (error) {{
                console.error('Error rendering transcript:', error);
                transcriptContent.innerHTML = '<div class="loading" style="color: red;">Error loading transcript: ' + error.message + '</div>';
            }}
        }}
        
        // Save corrections
        function saveCorrections() {{
            if (wordCorrections.size === 0 && speakerNameChanges.size === 0 && paragraphSpeakerChanges.size === 0) {{
                alert('No corrections made. Nothing to save.');
                return;
            }}
            
            try {{
                const normalized = normalizeTranscript(transcriptData);
                const words = normalized.words || [];
                const speakerNames = normalized.corrections?.speaker_names || {{}};
                
                // Build paragraph index to word index mapping for speaker changes
                const paragraphWordMap = new Map(); // Map paragraph index to array of word indices
                let currentParaIdx = 0;
                let currentParaWordIndices = [];
                words.forEach((word, wordIdx) => {{
                    if (word.paragraph_start && currentParaWordIndices.length > 0) {{
                        paragraphWordMap.set(currentParaIdx, currentParaWordIndices);
                        currentParaIdx++;
                        currentParaWordIndices = [];
                    }}
                    currentParaWordIndices.push(wordIdx);
                }});
                if (currentParaWordIndices.length > 0) {{
                    paragraphWordMap.set(currentParaIdx, currentParaWordIndices);
                }}
                
                // Apply corrections to words
                const correctedWords = words.map((word, index) => {{
                    const correction = wordCorrections.get(index);
                    let correctedWord = word;
                    
                    if (correction) {{
                        // Normalize word field: lowercase and strip punctuation
                        const normalizedWord = normalizeWord(correction.corrected_word);
                        // Keep punctuated_word with proper capitalization and punctuation
                        const punctuatedWord = correction.corrected_word;
                        
                        correctedWord = {{
                            ...word,
                            word: normalizedWord,
                            punctuated_word: punctuatedWord,
                            corrected: true,
                            original_word: correction.original_word,
                            original_punct: correction.original_punct
                        }};
                    }}
                    
                    // Apply paragraph-specific speaker changes
                    paragraphWordMap.forEach((wordIndices, paraIdx) => {{
                        if (paragraphSpeakerChanges.has(paraIdx) && wordIndices.includes(index)) {{
                            const change = paragraphSpeakerChanges.get(paraIdx);
                            correctedWord = {{
                                ...correctedWord,
                                speaker: change.newSpeakerIndex
                            }};
                        }}
                    }});
                    
                    return correctedWord;
                }});
                
                // Get original corrections version and increment
                const originalCorrections = normalized.corrections || {{}};
                        const version = (originalCorrections.version || 0) + 1;
                        
                // Merge speaker name changes with original speaker names
                const mergedSpeakerNames = {{...speakerNames}};
                // Add global speaker name changes
                speakerNameChanges.forEach((newName, speakerIndex) => {{
                    mergedSpeakerNames[speakerIndex] = newName;
                }});
                // Add paragraph-specific speaker changes (use new speaker index)
                paragraphSpeakerChanges.forEach((change, paraIdx) => {{
                    mergedSpeakerNames[change.newSpeakerIndex] = change.name;
                }});
                
                // Build RichWordsTranscript format with corrections
                        const richWordsTranscript = {{
                    words: correctedWords,
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
                        setTimeout(() => {{
                            a.click();
                            setTimeout(() => {{
                                document.body.removeChild(a);
                                window.URL.revokeObjectURL(url);
                            }}, 100);
                        }}, 0);
                        
                const wordCount = wordCorrections.size;
                const speakerCount = speakerNameChanges.size;
                const paragraphSpeakerCount = paragraphSpeakerChanges.size;
                let message = 'Corrections saved! ';
                const parts = [];
                if (wordCount > 0) {{
                    parts.push(`${{wordCount}} word(s) corrected`);
                }}
                if (speakerCount > 0) {{
                    parts.push(`${{speakerCount}} speaker(s) renamed globally`);
                }}
                if (paragraphSpeakerCount > 0) {{
                    parts.push(`${{paragraphSpeakerCount}} paragraph speaker(s) changed`);
                }}
                if (parts.length > 0) {{
                    message += parts.join(', ') + '.';
                }}
                message += ' File download started.';
                alert(message);
            }} catch (error) {{
                console.error('Error saving corrections:', error);
                alert('Failed to save corrections: ' + (error.message || String(error)));
            }}
        }}
        
        // Load edits from localStorage on page load
        loadEditsFromStorage();
        
        // Render transcript on load
        renderTranscript();
    </script>
</body>
</html>
'''

# Heavy React editor template removed - using lightweight editor instead

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
    
    # Prepare transcript JSON string
    transcript_json_str = json.dumps(transcript_data, indent=2)
    
    # Generate viewer HTML (lightweight vanilla JS)
    viewer_html = VIEWER_TEMPLATE.format(
        title=lecture_name,
        transcript_json='__TRANSCRIPT_JSON_PLACEHOLDER__',
        audio_filename=audio_filename
    )
    viewer_html = viewer_html.replace('__TRANSCRIPT_JSON_PLACEHOLDER__', transcript_json_str)
    
    with open(bundle_dir / "index.html", 'w', encoding='utf-8') as f:
        f.write(viewer_html)
    
    # Generate light editor HTML (lightweight vanilla JS with editing)
    light_editor_html = LIGHT_EDITOR_TEMPLATE.format(
        title=lecture_name,
        transcript_json='__TRANSCRIPT_JSON_PLACEHOLDER__',
        audio_filename=audio_filename
    )
    light_editor_html = light_editor_html.replace('__TRANSCRIPT_JSON_PLACEHOLDER__', transcript_json_str)
    
    with open(bundle_dir / "light-editor.html", 'w', encoding='utf-8') as f:
        f.write(light_editor_html)
    
    print(f"✅ Generated bundle: {seminar_group}/{lecture_name} (viewer + editor)")
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

