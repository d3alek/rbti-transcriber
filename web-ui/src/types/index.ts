/**
 * Main types export file for the Audio Transcription Web Manager
 */

// API and core types
export * from './api';
export * from './deepgram';
export * from './transcriptEditor';
export * from './publisher';
export * from './errors';

// Re-export commonly used interfaces for convenience
export type {
  APIResponse,
  AudioFileInfo,
  DirectoryScanResult,
  TranscriptionResult,
  TranscriptionStatus
} from './api';

export type {
  DeepgramResponse,
  CorrectedDeepgramResponse,
  DeepgramWord,
  CorrectedDeepgramWord,
  DeepgramCacheFile
} from './deepgram';

export type {
  ReactTranscriptEditorData,
  ReactTranscriptEditorWord,
  TranscriptEditorProps,
  SpeakerNameMapping,
  EditSession
} from './transcriptEditor';

export type {
  PublishBundle,
  LocalPagesStructure,
  PublishingStatus,
  SiteStructure,
  PublishOptions
} from './publisher';

export type {
  AppError,
  ValidationError,
  FileSystemError,
  TranscriptionError,
  LocalSiteError,
  APIError,
  ErrorHandler,
  RetryStrategy,
  ErrorCodes
} from './errors';