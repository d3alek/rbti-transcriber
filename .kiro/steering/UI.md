---
inclusion: fileMatch
fileMatchPattern: ['web-ui/**/*', 'api/**/*']
---

# UI Architecture & Patterns

## Frontend-Backend Architecture

The web UI (`web-ui/`) serves as a visualization and management interface for transcriptions processed by the Python backend. The system follows a clear separation of concerns:

- **React Frontend**: Material-UI based interface for file management, transcription editing, and job monitoring
- **FastAPI Backend**: RESTful API with WebSocket support for real-time updates
- **Core Engine Integration**: Backend interfaces with the Python transcription engine (`src/`)

## Component Architecture

### Main Application Structure
- **App.tsx**: Root component with drawer navigation and view routing
- **View-based routing**: Files, Jobs, Settings, and Editor views
- **Responsive layout**: Collapsible sidebar that hides in editor mode

### Key Components
- **FileManager**: Audio file discovery, selection, and transcription initiation
- **TranscriptEditor**: Full-screen editing interface with custom paragraph-based editing and real-time word highlighting
- **JobManager**: Real-time transcription job monitoring and queue management
- **AudioPlayer**: Synchronized audio playback with transcript navigation

## Service Priority & Data Flow

### Transcription Service Priority
1. **Deepgram**: Primary service with UI priority for display
2. **AssemblyAI**: Secondary option with fallback support
3. **OpenAI**: Additional transcription service option

### Real-time Communication
- **WebSocket connections** for live progress updates during transcription
- **Auto-save functionality** with 3-second debouncing for transcript edits
- **File system monitoring** for automatic audio file discovery

## UI/UX Patterns

### Material-UI Design System
- Consistent theme with primary blue (#1976d2) and secondary red (#dc004e)
- Light mode interface optimized for long-form text editing
- Responsive breakpoints for desktop-first workflow

### Editor Experience
- **Full-screen editor mode** with hidden sidebar for distraction-free editing
- **Synchronized playback** between audio player and transcript segments
- **Visual indicators** for unsaved changes and confidence scores
- **Segment-based navigation** with click-to-play functionality

### State Management
- **Local component state** for UI interactions and temporary data
- **API-driven data flow** with optimistic updates for better UX
- **Error boundaries** with user-friendly error messages and retry options

## API Integration Patterns

### RESTful Endpoints
- `/api/files/*` - File management and metadata
- `/api/transcribe/*` - Transcription job operations
- `/api/export/*` - Format conversion and downloads
- `/api/publish/*` - GitHub publication workflow

### WebSocket Events
- `ws://localhost:8000/ws/transcription/{job_id}` - Job progress updates
- `ws://localhost:8000/ws/files` - File system change notifications

### Error Handling
- **Graceful degradation** when services are unavailable
- **User-friendly error messages** with actionable suggestions
- **Automatic retry logic** for transient failures

## Development Conventions

### TypeScript Usage
- **Strict typing** for all API interfaces and component props
- **Shared type definitions** in `src/types/index.ts`
- **Generic API response types** for consistent error handling

### Component Patterns
- **Functional components** with React hooks
- **Memoized callbacks** to prevent unnecessary re-renders
- **Ref forwarding** for imperative audio player controls
- **Custom hooks** for complex state logic and API interactions