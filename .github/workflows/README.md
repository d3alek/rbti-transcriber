# GitHub Pages Publishing Workflow

## Overview

This workflow automatically publishes transcription bundles to GitHub Pages whenever transcription files are created or updated.

## How It Works

1. **Trigger**: Runs on push to files matching `**/transcriptions/*.json` patterns
2. **Build**: Creates a browser-compatible bundle of `react-transcript-editor`
3. **Generate**: Creates self-contained HTML bundles for each transcription
4. **Index**: Generates a main index page listing all seminars and lectures
5. **Publish**: Deploys everything to GitHub Pages

## Output Structure

```
https://your-username.github.io/repo-name/
├── index.html                    # Main index page
├── bundles/
│   └── react-transcript-editor-bundle.js
├── seminar-group-1/
│   ├── lecture-1/
│   │   ├── index.html           # Standalone viewer
│   │   ├── audio.mp3            # Compressed audio
│   │   └── transcript.json      # Transcript data
│   └── lecture-2/
│       └── ...
└── seminar-group-2/
    └── ...
```

## Setup

1. **Enable GitHub Pages** in your repository settings:
   - Go to Settings → Pages
   - Source: "GitHub Actions"

2. **Ensure permissions** are set correctly:
   - The workflow requires `contents: write` and `pages: write` permissions
   - These are set in the workflow file

## Manual Trigger

You can manually trigger the workflow:
1. Go to Actions tab in GitHub
2. Select "Publish Transcriptions to GitHub Pages"
3. Click "Run workflow"

## Troubleshooting

### Workflow fails to deploy

- Check that GitHub Pages is enabled with "GitHub Actions" as source
- Verify repository has Pages write permissions
- Check Actions logs for specific errors

### Bundles missing audio files

- Ensure compressed MP3 files exist in `compressed/` directories
- Verify audio filenames match transcription filenames (without extension)

### Transcript editor doesn't load

- Check browser console for errors
- Verify the react-transcript-editor bundle was built successfully
- Ensure React and ReactDOM CDN links are accessible

## Customization

To customize the HTML output, edit:
- `scripts/generate-gh-pages-bundles.py` - HTML template and bundle generation
- `scripts/generate-index-page.py` - Index page styling and structure

