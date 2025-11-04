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
            display: grid;
            grid-template-columns: 1fr 3fr;
            gap: 1rem;
            padding: 1rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        @media (max-width: 1020px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .audio-player-container {{
            background: white;
            box-shadow: 0 0 10px #ccc;
            padding: 1rem;
            border-radius: 4px;
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
        }}
        
        .transcript-content {{
            max-height: 75vh;
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
            <div style="display: flex; gap: 10px;">
                <a href="light-editor.html" class="edit-button" style="background-color: #2196F3;">✏️ LIGHT EDIT</a>
                <a href="editor.html" class="edit-button">✏️ EDIT</a>
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
            display: grid;
            grid-template-columns: 1fr 3fr;
            gap: 1rem;
            padding: 1rem;
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        @media (max-width: 1020px) {{
            .main-content {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .audio-player-container {{
            background: white;
            box-shadow: 0 0 10px #ccc;
            padding: 1rem;
            border-radius: 4px;
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
        }}
        
        .transcript-content {{
            max-height: 75vh;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title} - Light Editor</h1>
            <div class="header-buttons">
                <a href="index.html" class="button back-button">← Back to Viewer</a>
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
                    💡 <strong>Edit Mode:</strong> Click a word to play audio or double-click to edit. Corrected words are highlighted in green.
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
        let originalWords = []; // Store original word data
        let wordCorrections = new Map(); // Map word index to corrections
        const audioPlayer = document.getElementById('audioPlayer');
        const transcriptContent = document.getElementById('transcriptContent');
        const saveButton = document.getElementById('saveButton');
        
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
        
        // Edit word
        function editWord(wordIndex, wordElement) {{
            const word = originalWords[wordIndex];
            if (!word) return;
            
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
                    const speakerName = getSpeakerName(para.speaker, speakerNames);
                    const timecode = formatTimecode(para.startTime);
                    
                    html += '<div class="paragraph-block">';
                    html += `  <div class="speaker-label">${{speakerName}}</div>`;
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
            if (wordCorrections.size === 0) {{
                alert('No corrections made. Nothing to save.');
                return;
            }}
            
            try {{
                const normalized = normalizeTranscript(transcriptData);
                const words = normalized.words || [];
                const speakerNames = normalized.corrections?.speaker_names || {{}};
                
                // Apply corrections to words
                const correctedWords = words.map((word, index) => {{
                    const correction = wordCorrections.get(index);
                    if (correction) {{
                        // Normalize word field: lowercase and strip punctuation
                        const normalizedWord = normalizeWord(correction.corrected_word);
                        // Keep punctuated_word with proper capitalization and punctuation
                        const punctuatedWord = correction.corrected_word;
                        
                        return {{
                            ...word,
                            word: normalizedWord,
                            punctuated_word: punctuatedWord,
                            corrected: true,
                            original_word: correction.original_word,
                            original_punct: correction.original_punct
                        }};
                    }}
                    return word;
                }});
                
                // Get original corrections version and increment
                const originalCorrections = normalized.corrections || {{}};
                const version = (originalCorrections.version || 0) + 1;
                
                // Build RichWordsTranscript format with corrections
                const richWordsTranscript = {{
                    words: correctedWords,
                    corrections: {{
                        version: version,
                        timestamp: new Date().toISOString(),
                        speaker_names: Object.keys(speakerNames).length > 0 ? speakerNames : undefined
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
                
                alert(`Corrections saved! ${{wordCorrections.size}} word(s) corrected. File download started.`);
            }} catch (error) {{
                console.error('Error saving corrections:', error);
                alert('Failed to save corrections: ' + (error.message || String(error)));
            }}
        }}
        
        // Render transcript on load
        renderTranscript();
    </script>
</body>
</html>
'''

# HTML template for standalone transcript editor (heavy React version)
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
        .button-container {{
            position: fixed;
            top: 30px;
            right: 10px;
            z-index: 1000;
            display: flex;
            gap: 10px;
        }}
        .back-button {{
            background-color: #6c757d;
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
        .back-button:hover {{
            background-color: #5a6268;
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
            
            // Normalize word: lowercase and strip punctuation (for 'word' field)
            function normalizeWord(wordText) {{
                if (!wordText) return wordText;
                // Convert to lowercase and remove punctuation
                return wordText.toLowerCase().trim().replace(/[.,!?;:"()\\[\\]{{}}]+/g, '');
            }}
            
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
                                
                                // Get the punctuated word (with proper capitalization)
                                const punctuatedWord = word.punct || word.word || word.text || '';
                                // Normalize word field: lowercase and strip punctuation
                                const normalizedWord = normalizeWord(punctuatedWord);
                                
                                allWords.push({{
                                    word: normalizedWord,
                                    start: word.start,
                                    end: word.end,
                                    confidence: word.confidence || 0.9,
                                    speaker: speakerIndex,
                                    speaker_confidence: word.confidence || 0.9,
                                    punctuated_word: punctuatedWord,
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
                        React.createElement('div', {{ className: 'button-container' }},
                            React.createElement('a', {{
                                className: 'back-button',
                                href: 'index.html'
                            }}, '← Back to Viewer'),
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
    
    # Generate editor HTML (heavy React version)
    editor_html = HTML_TEMPLATE.format(
        title=lecture_name,
        transcript_json='__TRANSCRIPT_JSON_PLACEHOLDER__',
        audio_filename=audio_filename
    )
    editor_html = editor_html.replace('__TRANSCRIPT_JSON_PLACEHOLDER__', transcript_json_str)
    
    with open(bundle_dir / "editor.html", 'w', encoding='utf-8') as f:
        f.write(editor_html)
    
    print(f"✅ Generated bundle: {seminar_group}/{lecture_name} (viewer + light editor + editor)")
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

