# React Transcript Editor Integration Guide

This document provides guidance for working with the BBC's react-transcript-editor component for transcript editing functionality.

## Overview

The react-transcript-editor is a React component designed for transcribing audio and video with features like:
- Word-level timing synchronization
- Speaker identification and management
- Real-time audio playback with highlighting
- Multiple export formats (HTML, Markdown, DOCX, SRT, etc.)
- Draft.js based editing with undo/redo
- Keyboard shortcuts for efficient editing

## Repository Structure

```
react-transcript-editor/
├── packages/
│   ├── components/           # Main React components
│   │   ├── transcript-editor/
│   │   ├── timed-text-editor/
│   │   ├── media-player/
│   │   └── video-player/
│   ├── stt-adapters/        # Speech-to-text format adapters
│   │   ├── bbc-kaldi/
│   │   ├── google-stt/
│   │   ├── amazon-transcribe/
│   │   └── digital-paper-edit/
│   ├── export-adapters/     # Export format converters
│   └── util/               # Utility functions
├── demo/                   # Demo application
└── .storybook/            # Storybook configuration
```

## Key Components

### TranscriptEditor (Main Component)
```js
import TranscriptEditor from "@bbc/react-transcript-editor";

<TranscriptEditor
  transcriptData={transcriptJson}
  mediaUrl={audioOrVideoUrl}
  isEditable={true}
  sttJsonType="bbckaldi"
  handleAutoSaveChanges={onSave}
  title="My Transcript"
  fileName="audio.mp3"
/>
```

### Required Props
- `transcriptData`: JSON transcript data
- `mediaUrl`: URL to audio/video file

### Optional Props
- `isEditable`: Enable text editing (default: false)
- `sttJsonType`: Format of transcript data ("bbckaldi", "draftjs", etc.)
- `handleAutoSaveChanges`: Callback for auto-save functionality
- `spellCheck`: Enable spell checking
- `title`: Transcript title
- `fileName`: For local storage functionality

## Data Format Requirements

The component expects transcript data in specific formats. For Deepgram integration, you need to transform the response:

### Deepgram to react-transcript-editor Format
```js
function transformDeepgramToTranscriptEditor(deepgramData) {
  const rawResponse = deepgramData.result.raw_response;
  const words = rawResponse.results.channels[0].alternatives[0].words;
  
  return {
    words: words.map((word, index) => ({
      start: word.start,
      end: word.end,
      word: word.word,
      confidence: word.confidence || 0.9,
      punct: word.punctuated_word || word.word,
      index: index,
      speaker: word.speaker !== undefined ? word.speaker : 0
    })),
    speakers: deepgramData.result.speakers || [],
    transcript: rawResponse.results.channels[0].alternatives[0].transcript
  };
}
```

## STT Adapters

The component includes adapters for various speech-to-text services:
- `bbckaldi`: BBC's Kaldi format
- `google-stt`: Google Speech-to-Text
- `amazon-transcribe`: Amazon Transcribe
- `digital-paper-edit`: Digital Paper Edit format

For Deepgram, you'll need to create a custom adapter or transform the data to match an existing format.

## Export Formats

Supported export formats:
- `draftjs`: Draft.js JSON format
- `txt`: Plain text
- `docx`: Microsoft Word document
- `srt`: SubRip subtitle format
- `vtt`: WebVTT subtitle format
- `csv`: Comma-separated values

## Development Setup

### Prerequisites
- Node.js 10+ (specified in .nvmrc)
- npm 6.1.0+

### Installation
```bash
cd react-transcript-editor
npm install
```

### Development Server
```bash
npm start  # Starts Storybook on http://localhost:6006
```

### Building
```bash
npm run build:component  # Build the component
npm run build:storybook  # Build static Storybook
```

## Integration Patterns

### Basic Integration
```js
import TranscriptEditor from "@bbc/react-transcript-editor";

function MyTranscriptApp() {
  const [transcriptData, setTranscriptData] = useState(null);
  
  return (
    <TranscriptEditor
      transcriptData={transcriptData}
      mediaUrl="/path/to/audio.mp3"
      isEditable={true}
      handleAutoSaveChanges={(data) => {
        // Save changes
        console.log('Transcript updated:', data);
      }}
    />
  );
}
```

### With Deepgram Data
```js
// Transform Deepgram response first
const transformedData = transformDeepgramToTranscriptEditor(deepgramResponse);

<TranscriptEditor
  transcriptData={transformedData}
  mediaUrl="/path/to/audio.mp3"
  sttJsonType="bbckaldi"  // Or create custom adapter
  isEditable={true}
/>
```

## Custom Demo Implementation

For quick prototyping with Deepgram data, you can create a simple HTML demo:

1. Create an HTML file with the transcript display logic
2. Transform Deepgram JSON to display format
3. Add click-to-seek functionality
4. Integrate with HTML5 audio player

See `react-transcript-editor/demo/deepgram-demo.html` for a working example.

## Key Features for RBTI Use Case

### Word-Level Timing
- Each word has start/end timestamps
- Click words to seek to that position in audio
- Real-time highlighting during playback

### Speaker Management
- Support for multiple speakers
- Speaker identification and labeling
- Speaker-based navigation

### Confidence Scoring
- Word-level confidence from STT service
- Visual indicators for low-confidence words
- Editing prioritization based on confidence

### Export Options
- Multiple format support for different use cases
- Customizable export templates
- Batch export capabilities

## Best Practices

### Performance
- Use React.memo for large transcripts
- Implement virtualization for very long transcripts
- Lazy load audio/video files

### Data Management
- Cache transformed transcript data
- Implement auto-save functionality
- Version control for transcript edits

### User Experience
- Provide keyboard shortcuts
- Show loading states during processing
- Clear error messages for failed operations

## Common Issues

### Audio Sync Problems
- Ensure audio file is accessible via HTTPS
- Check CORS headers for cross-origin audio
- Verify timing data accuracy

### Large File Performance
- Consider chunking very long transcripts
- Implement progressive loading
- Use web workers for heavy processing

### Browser Compatibility
- Test audio playback across browsers
- Verify CSS module support
- Check for required polyfills

## Future Considerations

### Deepgram Integration
- Create dedicated Deepgram STT adapter
- Implement real-time transcription updates
- Add confidence-based editing workflows

### RBTI-Specific Features
- Custom glossary integration
- Technical terminology highlighting
- Batch processing for lecture series

This steering document should be updated as we gain more experience with the component and identify additional patterns or issues specific to our use case.