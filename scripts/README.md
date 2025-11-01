# GitHub Pages Publishing Scripts

This directory contains scripts for automatically publishing transcription bundles to GitHub Pages.

## Overview

When transcription files (`transcriptions/*.json`) are created or updated, a GitHub Actions workflow automatically:

1. **Builds** a browser-compatible bundle of `react-transcript-editor`
2. **Generates** self-contained HTML bundles for each transcription
3. **Creates** an index page listing all seminars and lectures
4. **Publishes** everything to GitHub Pages

## Scripts

### `generate-gh-pages-bundles.py`

Scans the repository for transcription JSON files and generates bundles for each one.

Each bundle contains:
- **Compressed MP3** audio file
- **Transcript JSON** file (for reference)
- **Standalone HTML** file with `react-transcript-editor` preloaded

**Output structure:**
```
gh-pages-output/
├── bundles/
│   └── react-transcript-editor-bundle.js
├── seminar-name-1/
│   ├── lecture-name-1/
│   │   ├── index.html
│   │   ├── audio.mp3
│   │   └── transcript.json
│   └── lecture-name-2/
│       └── ...
└── seminar-name-2/
    └── ...
```

### `generate-index-page.py`

Generates an `index.html` page that lists all seminars and their lectures.

### `build-browser-bundle.js`

Builds a UMD bundle of `react-transcript-editor` that can be loaded in the browser.

## Usage

### Automatic (GitHub Actions)

The workflow runs automatically when:
- Transcription files (`**/transcriptions/*.json`) are pushed
- The workflow file itself is updated
- Manually triggered via GitHub Actions UI

### Manual Testing

To test locally:

```bash
# 1. Install dependencies and build the browser bundle
cd react-transcript-editor
npm ci
npm install --save-dev webpack webpack-cli babel-loader @babel/core @babel/preset-env @babel/preset-react style-loader css-loader sass-loader node-sass

# 2. Run the build script (from react-transcript-editor directory)
node ../scripts/build-browser-bundle.js

# 2. Generate bundles
python scripts/generate-gh-pages-bundles.py

# 3. Generate index page
python scripts/generate-index-page.py

# 4. View locally (optional)
cd gh-pages-output
python -m http.server 8000
# Then visit http://localhost:8000
```

## Requirements

- Python 3.11+
- Node.js 18+
- npm packages (installed automatically by workflow):
  - react-transcript-editor dependencies
  - webpack and related build tools

## Output Format

### Bundle Structure

Each lecture bundle is self-contained and can be opened directly in a browser. The HTML file:
- Loads React and ReactDOM from CDN
- Loads the react-transcript-editor bundle
- Embeds the transcript data inline
- References the audio file relatively

### Transcript Format

Transcripts are transformed from the internal `CorrectedDeepgramResponse` format to the `ReactTranscriptEditorData` format expected by react-transcript-editor:

- **Words**: Array of word objects with timing, speaker, and text
- **Speakers**: Array of speaker segments with timestamps
- **Segmentation**: bbckaldi-compatible segmentation structure
- **Metadata**: Duration, confidence, service info

## Troubleshooting

### Bundle not found

If you see "react-transcript-editor bundle not found":
1. Ensure the browser bundle was built successfully
2. Check that `gh-pages-output/bundles/react-transcript-editor-bundle.js` exists

### Missing audio files

If a bundle is missing its audio file:
1. Ensure the compressed MP3 exists in `compressed/` directory
2. Check that the filename matches the transcription filename (without extension)

### Transcription format errors

If transcript transformation fails:
1. Check that the JSON file has the correct structure (see `data-formats.md`)
2. Ensure `raw_response.results.channels[0].alternatives[0].words` exists

