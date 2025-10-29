/**
 * TypeScript type definitions for the transcription web UI.
 */

// Export Deepgram-specific types first
export * from './deepgram';

// Export validation types (excluding conflicting ones)
export type { 
  ValidationError, 
  ValidationWarning, 
  DeepgramValidator,
  TranscriptError 
} from './validation';

export interface AudioFile {
  id: string;
  name: string;
  path: string;
  hash?: string;
  size: number;
  duration: number;
  has_transcription: boolean;
  transcription_status: TranscriptionStatus;
  last_modified: string;
  publication_status?: PublicationStatus;
}

export interface TranscriptionData {
  text: string;
  speakers: SpeakerSegment[];
  duration: number;
  confidence: number;
  audio_duration: number;
  processing_time: number;
}

export interface SpeakerSegment {
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number;
}

export interface PublicationStatus {
  is_published: boolean;
  published_url?: string;
  published_date?: string;
  github_commit_hash?: string;
}

export interface TranscriptionJob {
  id: string;
  status: TranscriptionStatus;
  progress: number;
  message: string;
  error?: string;
}

export interface TranscriptionRequest {
  file_id: string;
  service: 'deepgram';
  compress_audio: boolean;
  output_formats: string[];
}

export interface PublicationRequest {
  file_id: string;
  title?: string;
  description?: string;
  tags: string[];
}

export interface APIResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
}

export type TranscriptionStatus = 'none' | 'processing' | 'completed' | 'error';

export type ExportFormat = 'html' | 'markdown' | 'txt';

export interface ExportRequest {
  file_id: string;
  format: ExportFormat;
}