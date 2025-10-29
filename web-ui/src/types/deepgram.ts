/**
 * TypeScript interfaces for Deepgram API responses and transcript editor data structures.
 * These interfaces match the raw Deepgram response format to avoid data loss from conversions.
 */

// Raw Deepgram API Response Structure
export interface DeepgramResponse {
  metadata: DeepgramMetadata;
  results: DeepgramResults;
}

export interface DeepgramMetadata {
  transaction_key?: string;
  request_id: string;
  sha256: string;
  created: string;
  duration: number;
  channels: number;
  models: string[];
  model_info: Record<string, ModelInfo>;
}

export interface ModelInfo {
  name: string;
  version: string;
  arch: string;
}

export interface DeepgramResults {
  channels: DeepgramChannel[];
}

export interface DeepgramChannel {
  alternatives: DeepgramAlternative[];
}

export interface DeepgramAlternative {
  transcript: string;
  words: WordData[];
  paragraphs: ParagraphsStructure;
}

export interface ParagraphsStructure {
  transcript: string;
  paragraphs: DeepgramParagraph[];
}

export interface DeepgramParagraph {
  sentences: SentenceData[];
}

// Core Data Structures for the Editor
export interface WordData {
  word: string;
  start: number;
  end: number;
  confidence: number;
  speaker: number;
  speaker_confidence: number;
  punctuated_word: string;
  index?: number; // Added for efficient lookups
}

export interface SentenceData {
  id: string;
  text: string;
  start: number;
  end: number;
  words: WordData[];
  speaker: number;
}

export interface ParagraphData {
  id: string;
  text: string;
  startTime: number;
  endTime: number;
  speaker: number;
  sentences: SentenceData[];
  words: WordData[];
  confidence: number;
}

// Version Management
export interface DeepgramVersion {
  version: number;
  filename: string;
  timestamp: string;
  changes: string;
  response: DeepgramResponse;
}

export interface VersionMetadata {
  versions: VersionInfo[];
  currentVersion: number;
  lastModified: string;
}

export interface VersionInfo {
  version: number;
  filename: string;
  timestamp: string;
  changes: string;
  fileSize: number;
}

// API Request/Response types
export interface ParagraphUpdateRequest {
  paragraph_id: string;
  new_text: string;
}

export interface VersionSaveRequest {
  changes: string;
  response: DeepgramResponse;
}

export interface VersionListResponse {
  versions: VersionInfo[];
  current_version: number;
}

export interface TranscriptLoadResponse {
  version: number;
  paragraphs: ParagraphData[];
  audio_duration: number;
  confidence: number;
}

// Application-specific interfaces that extend the cached response format
export interface CachedTranscriptionResponse {
  audio_file: string;
  service: 'deepgram';
  config: TranscriptionConfig;
  timestamp: string;
  text: string;
  speakers: SpeakerSegment[];
  confidence: number;
  audio_duration: number;
  processing_time: number;
  raw_response: DeepgramResponse;
}

export interface TranscriptionConfig {
  speaker_labels: boolean;
  custom_vocabulary: string[];
  punctuate: boolean;
  format_text: boolean;
  language_code: string;
  max_speakers: number;
}

export interface SpeakerSegment {
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number;
}

// UI Component Props
export interface TranscriptEditorProps {
  audioFile: string;
  transcriptVersions: DeepgramVersion[];
  currentVersion: number;
  onVersionChange: (version: number) => void;
  onSaveVersion: () => void;
}

export interface TranscriptEditorState {
  currentPlaybackTime: number;
  activeWordIndex: number;
  editingParagraph: string | null;
  paragraphs: ParagraphData[];
  hasUnsavedChanges: boolean;
}

export interface ParagraphEditorProps {
  paragraph: ParagraphData;
  isEditing: boolean;
  currentPlaybackTime: number;
  onEdit: (paragraphId: string, newText: string) => void;
  onStartEdit: (paragraphId: string) => void;
  onEndEdit: () => void;
  showConfidenceIndicators?: boolean;
}

export interface AudioPlayerProps {
  audioFile: string;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onSeek: (time: number) => void;
  duration?: number;
}

export interface VersionManagerProps {
  versions: DeepgramVersion[];
  currentVersion: number;
  onVersionSelect: (version: number) => void;
  onSaveVersion: () => void;
  canSave: boolean;
  isLoading?: boolean;
}

// Confidence level thresholds
export const ConfidenceLevel = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low'
} as const;

export type ConfidenceLevel = typeof ConfidenceLevel[keyof typeof ConfidenceLevel];

export interface ConfidenceThresholds {
  high: number; // > 0.9
  medium: number; // 0.7-0.9
  low: number; // < 0.7
}

// Error handling (import and re-export from validation types)
import type { TranscriptError } from './validation';
import { ErrorType } from './validation';

export type { TranscriptError };
export { ErrorType };

// Validation schemas
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}