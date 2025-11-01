# Web UI Architecture and Implementation

This document describes the current web UI implementation for the Audio Transcription System.

## Overview

The Web UI provides an interactive interface for managing and editing audio transcriptions. It consists of:
- A **React-based frontend** built with TypeScript, Material-UI, and Webpack 4
- Integration with the **BBC react-transcript-editor** component for editing
- A **custom Deepgram adapter** for paragraph grouping and speaker segmentation
- Communication with the **FastAPI backend** via REST endpoints

## Technology Stack

### Build Tools
- **Webpack 4** - Module bundler and build system (chosen for Node 10 compatibility)
- **Babel** - JavaScript/TypeScript transpiler with React support
- **TypeScript** - Type-safe JavaScript

### UI Framework
- **React 16.8.6** - UI library with hooks
- **Material-UI v4** - Component library
- **Draft.js** - Rich text editor framework (via react-transcript-editor)

### Key Dependencies
- `@bbc/react-transcript-editor` - BBC's transcript editing component (used as submodule)
- `react`, `react-dom` - Core React framework
- `@material-ui/core`, `@material-ui/icons`, `@material-ui/lab` - UI components

### Build Toolchain
- `webpack`, `webpack-cli`, `webpack-dev-server` - Bundling and dev server
- `babel-loader`, `css-loader`, `style-loader`, `sass-loader` - Loaders
- `html-webpack-plugin`, `clean-webpack-plugin` - Build plugins
- Node-sass 4.14.1 - SCSS compilation (Node 10 compatible)

## Architecture

### Application Structure

```
web-ui/
├── src/
│   ├── App.tsx                    # Main app component with routing
│   ├── main.tsx                   # Entry point
│   ├── @types/                    # TypeScript declarations
│   │   └── bbc__react-transcript-editor.d.ts
│   ├── components/
│   │   ├── FileManager/          # File browsing and management
│   │   │   ├── FileManager.tsx   # Main file manager container
│   │   │   ├── DirectorySelector.tsx
│   │   │   ├── AudioFileList.tsx # File list display
│   │   │   └── StatusIndicators.tsx
│   │   └── TranscriptEditor/     # Transcript editing interface
│   │       ├── TranscriptEditorWrapper.tsx  # Main editor container
│   │       ├── AudioPlayerIntegration.tsx   # Audio playback sync
│   │       ├── ManualEditManager.tsx        # Manual corrections UI
│   │       └── index.ts
│   ├── services/                  # Business logic and API
│   │   ├── APIClient.ts          # Backend API client
│   │   ├── DeepgramTransformer.ts # Data transformation service
│   │   ├── CorrectionManager.ts  # Correction management
│   │   └── __tests__/            # Unit tests
│   └── types/                     # TypeScript definitions
│       ├── api.ts                # API response types
│       ├── deepgram.ts           # Deepgram data types
│       ├── transcriptEditor.ts   # Editor data types
│       ├── errors.ts             # Error types
│       └── publisher.ts          # Publishing types
├── index.html                     # HTML template
├── webpack.config.js              # Webpack configuration
├── tsconfig.json                  # TypeScript configuration
├── package.json                   # Dependencies and scripts
└── dist/                          # Build output (generated)
```

### View Flow

The application follows a simple two-view architecture:

```
┌─────────────────────────────────┐
│         App.tsx (Router)         │
│                                 │
│  ┌───────────────────────────┐  │
│  │   FileManager View        │  │  ← Browse and select files
│  │   - Directory selection   │  │
│  │   - File listing          │  │
│  │   - Start transcription   │  │
│  └───────────────────────────┘  │
│              │                   │
│     [File Selected]              │
│              │                   │
│              ▼                   │
│  ┌───────────────────────────┐  │
│  │ TranscriptEditor View      │  │  ← Edit transcripts
│  │ - Transcript editor        │  │
│  │ - Audio player sync        │  │
│  │ - Manual corrections       │  │
│  │ - Save changes             │  │
│  └───────────────────────────┘  │
│              │                   │
│     [Back Button]                │
│              │                   │
└──────────────┴───────────────────┘
```

## Key Components

### FileManager

**Purpose**: Browse audio files in the configured directory and trigger transcriptions.

**Features**:
- Directory path input with default value
- Recursive file scanning
- Files grouped by seminar series
- Transcription status indicators
- Start transcription for files
- Navigate to transcript editor

**API Endpoints Used**:
- `POST /api/directory/scan` - Scan directory
- `POST /api/transcribe/{file_path}` - Start transcription

### TranscriptEditorWrapper

**Purpose**: Container for the BBC react-transcript-editor component with custom integrations.

**Key Responsibilities**:
1. Load transcript data from API
2. Transform Deepgram format to editor format (via `DeepgramTransformer`)
3. Manage editing state and unsaved changes
4. Handle auto-save callbacks from editor
5. Coordinate audio playback synchronization
6. Provide manual correction interface

**Props**:
- `audioFile` - Audio file information
- `onBack` - Navigation callback
- `onSave` - Optional save callback
- `apiClient` - API client instance

**Configuration**:
- `sttJsonType="deepgram"` - Uses custom Deepgram adapter
- `autoSaveContentType="draftjs"` - Saves as DraftJS format
- `isEditable={true}` - Enables text editing
- `spellCheck={true}` - Enables spell checking

### DeepgramTransformer

**Purpose**: Bidirectional data transformation between Deepgram and react-transcript-editor formats.

**Key Methods**:

1. **`transformToReactTranscriptEditor`**
   - Input: `CorrectedDeepgramResponse`
   - Output: `ReactTranscriptEditorData`
   - Transforms word-level data, timestamps, speaker info
   - Preserves corrections and custom speaker names
   - Adds metadata (duration, confidence, service)

2. **`transformFromReactTranscriptEditor`**
   - Input: `ReactTranscriptEditorData` + original Deepgram response
   - Output: Updated `CorrectedDeepgramResponse`
   - Merges corrections back into Deepgram structure
   - Updates transcript text
   - Preserves speaker name mappings

**Segmentation Building**:
Creates segmentation objects for paragraph grouping:
- Prioritizes utterance-level segments from `result.speakers` (best granularity)
- Falls back to paragraph/sentence structure
- Falls back to simple speaker-based grouping

### Custom Deepgram Adapter

**Location**: `react-transcript-editor/packages/stt-adapters/deepgram/index.js`

**Purpose**: Custom adapter for react-transcript-editor to handle Deepgram's data format with intelligent paragraph grouping.

**Key Features**:

1. **Smart Paragraph Grouping**
   - Groups words by Deepgram utterance segments (`result.speakers`)
   - Coalesces consecutive utterances from same speaker
   - Breaks on speaker changes
   - Duration-based limits to prevent overly long paragraphs

2. **Configurable Parameters**
   ```javascript
   MAX_PARAGRAPH_DURATION_SECONDS = 60  // 1 minute default
   DURATION_FLEXIBILITY_MULTIPLIER = 1.2  // 20% flexibility
   ```

3. **Natural Break Points**
   - Attempts to break paragraphs on full stops (`.`, `?`, `!`)
   - Allows up to 20% over duration limit to find natural break
   - Hard cap at 1.2x duration to prevent extremely long paragraphs

**Paragraph Break Logic**:
- Always break on speaker change
- Break when duration ≥ max (60s) AND ends with full stop
- Force break if duration ≥ hard maximum (72s)

**Registration**:
Registered in `react-transcript-editor/packages/stt-adapters/index.js`:
```javascript
import deepgramToDraft from './deepgram/index';

case 'deepgram':
  blocks = deepgramToDraft(transcriptData);
  return { blocks, entityMap: createEntityMap(blocks) };
```

### APIClient

**Purpose**: Centralized HTTP client for backend API communication.

**Features**:
- Automatic response wrapping in `APIResponse` format
- Relative URL routing (works with Webpack dev server proxy)
- Error handling and logging
- Type-safe request/response handling

**Key Methods**:
- `scanDirectory(path)` - Scan audio directory
- `startTranscription(path)` - Start transcription job
- `getTranscriptionStatus(path)` - Check job status
- `getTranscript(path)` - Load transcript data
- `saveTranscriptCorrections(path, corrections)` - Save edits

## Build Configuration

### Webpack Setup

**Entry**: `./src/main.tsx`

**Output**: `dist/` directory with hashed filenames in production

**Important Configuration**:

1. **Module Resolution**
   - Alias `@bbc/react-transcript-editor` to local submodule
   - Path aliases for `@/types`, `@/components`, `@/services`

2. **Loaders**
   - **Babel** for TypeScript/JSX with React preset
   - **CSS/SASS** with module support
   - **File** loader for images/assets
   - Custom Babel config for react-transcript-editor with:
     - `@babel/plugin-proposal-class-properties`
     - `@babel/plugin-proposal-object-rest-spread`

3. **Dev Server**
   - Port 3000
   - Hot module reloading
   - Proxy `/api/*` to `http://localhost:8000`
   - History API fallback for client-side routing

4. **Plugins**
   - `HtmlWebpackPlugin` - Inject bundles into HTML
   - `CleanWebpackPlugin` - Clean dist on build

### Development Workflow

**Start Dev Server**:
```bash
cd web-ui
npm run dev
```
- Serves on http://localhost:3000
- Proxies API to http://localhost:8000
- Hot reload enabled

**Build Production**:
```bash
npm run build
```
- Outputs optimized bundle to `dist/`
- Source maps included
- Hashed filenames for cache busting

**Type Check**:
```bash
npm run type-check
```

## Data Flow

### Loading a Transcript

```
1. User selects file in FileManager
2. FileManager.navigateToEditor(audioFile)
   ↓
3. App.tsx sets selectedFile and currentView='transcriptEditor'
   ↓
4. TranscriptEditorWrapper mounts
   ↓
5. useEffect: loadTranscript()
   ↓
6. APIClient.getTranscript(audioFile.path)
   ↓
7. Backend returns CorrectedDeepgramResponse
   ↓
8. DeepgramTransformer.transformToReactTranscriptEditor(response)
   ↓
9. Transform:
   - Extract words with timestamps, speaker, corrections
   - Map Deepgram speakers array to utterances
   - Create segmentation for adapter
   - Return ReactTranscriptEditorData
   ↓
10. Set transcriptData state
   ↓
11. Pass to react-transcript-editor component
   ↓
12. Deepgram adapter (deepgramToDraft):
    - Group words by utterances
    - Apply paragraph grouping logic
    - Generate DraftJS blocks
    ↓
13. Editor renders transcript with paragraphs
```

### Saving Changes

```
1. User edits transcript in editor
2. react-transcript-editor calls handleAutoSaveChanges(data)
   ↓
3. TranscriptEditorWrapper receives DraftJS format
   ↓
4. DeepgramTransformer.transformFromReactTranscriptEditor(data, originalResponse)
   ↓
5. Merge corrections back into Deepgram structure:
   - Update word-level corrections
   - Update transcript text
   - Preserve speaker names
   ↓
6. APIClient.saveTranscriptCorrections(path, correctedResponse)
   ↓
7. Backend saves to JSON cache file
```

## Integration with react-transcript-editor

### Local Submodule Usage

The project uses a local git submodule of react-transcript-editor:
- **Location**: `../react-transcript-editor/` (relative to web-ui)
- **Webpack Alias**: Maps `@bbc/react-transcript-editor` to submodule
- **Custom Build**: Webpack processes submodule's JS/SCSS files
- **Custom Adapter**: Added Deepgram adapter in submodule's `packages/stt-adapters/deepgram/`

**Why Local Submodule?**
- Allows customization of BBC's component
- Can modify adapters for better Deepgram support
- Can add custom features without forking npm package
- Local changes retained across updates

### Adapter Integration

The custom Deepgram adapter provides:
1. **Better Paragraph Grouping** - Uses Deepgram utterance segments instead of generic punctuation
2. **Speaker Attribution** - Proper speaker labels from Deepgram diarization
3. **Configurable Granularity** - Adjustable paragraph length limits
4. **Natural Breaks** - Prefers ending on sentence boundaries

## Current Limitations

### Known Issues
1. **Node Version Constraint** - Limited to Node 10 for react-transcript-editor compatibility
2. **No WebSocket** - Status updates require manual refresh
3. **Limited Publishing** - Static site generation not yet implemented
4. **No Undo/Redo** - Depends on react-transcript-editor's built-in functionality

### Future Enhancements
1. **Real-time Updates** - WebSocket integration for job status
2. **Batch Operations** - Transcribe multiple files simultaneously
3. **Export Functionality** - Download transcripts in various formats
4. **Search and Filter** - Find specific content in transcripts
5. **Speaker Management** - UI for renaming speakers
6. **Collaboration** - Share editing with multiple users

## Development Environment

### Requirements
- Node.js 10+ (required for react-transcript-editor compatibility)
- npm 6+
- Python 3.8+ with FastAPI backend running

### Setup
```bash
# Install dependencies
cd web-ui
npm install

# Initialize react-transcript-editor submodule (if not already done)
cd ..
git submodule update --init --recursive

# Start backend API (in separate terminal)
python start_api.py

# Start frontend dev server
cd web-ui
npm run dev
```

### Directory Structure
- **Source**: `web-ui/src/` - TypeScript source files
- **Build Output**: `web-ui/dist/` - Generated by Webpack
- **Dependencies**: `web-ui/node_modules/` - npm packages
- **Submodule**: `react-transcript-editor/` - BBC component

## API Integration

### Endpoints Used

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/directory/scan` | POST | Scan directory for audio files |
| `/api/transcribe/{path}` | POST | Start transcription job |
| `/api/transcription-status/{path}` | GET | Check job status |
| `/api/transcripts/{path}` | GET | Load transcript data |
| `/api/transcripts/{path}/corrections` | PUT | Save transcript corrections |

### Response Format

All API responses wrapped in `APIResponse`:
```typescript
interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}
```

### Error Handling

- Network errors logged to console
- User-friendly error messages displayed
- Failed requests show snackbar notifications
- Loading states managed per component

## Styling

- **Material-UI Theme** - Consistent design system
- **CSS Modules** - Component-scoped styles
- **Responsive Design** - Adapts to screen size
- **Dark Mode** - Not yet implemented (planned)

## Testing

Unit tests location: `web-ui/src/services/__tests__/`
- `DeepgramTransformer.test.ts` - Transform logic tests
- Uses Jest testing framework

To run tests:
```bash
npm test
```

## Deployment

### Production Build
```bash
npm run build
```

Output in `dist/`:
- `main.[hash].js` - Main application bundle
- `main.[hash].css` - Global styles
- `index.html` - Served HTML template
- Assets (images, fonts)

### Serving
Can be served by any static file server:
- nginx
- Apache
- AWS S3 + CloudFront
- GitHub Pages
- Netlify/Vercel

Backend API must be available at configured endpoint.

## Performance Considerations

1. **Code Splitting** - Not yet implemented (planned)
2. **Lazy Loading** - Components loaded on demand
3. **Audio Compression** - Backend compresses audio for web playback
4. **Caching** - Transcript data cached in backend
5. **Optimistic Updates** - Save corrections optimistically

## Security

- **API Key Security** - Handled by backend only
- **Input Validation** - Backend validates all inputs
- **XSS Protection** - React escapes by default
- **CSRF** - Not applicable for local API
- **CORS** - Configured for development

## Contributing

When modifying the web UI:
1. Follow TypeScript best practices
2. Use existing Material-UI components
3. Maintain type safety
4. Add tests for new services
5. Update this documentation
6. Test in both dev and production builds

