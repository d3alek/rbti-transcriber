/**
 * Core API response and request types for the Audio Transcription Web Manager
 */

export interface APIResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  timestamp: string;
}

export interface AudioFileInfo {
  path: string;
  filename: string;
  size: number;
  duration: number;
  file_id: string;
  last_modified: string;
  seminar_group: string;
  transcription_status: string;
  transcription_files: string[];
  cache_files: string[];
  last_transcription_attempt?: string;
  transcription_error?: string;
  has_compressed_version: boolean;
  compressed_size?: number;
  compressed_path?: string;
  compression_ratio?: number;
}

export interface DirectoryScanResult {
  directory: string;
  total_files: number;
  transcribed_files: number;
  audio_files: AudioFileInfo[];
  seminar_groups: string[];
  groups_detail: { [key: string]: AudioFileInfo[] };
  scan_timestamp: string;
}

export interface TranscriptionStatus {
  exists: boolean;
  status: 'completed' | 'failed';
  error?: string;
  cacheFile?: string;
  compressedAudio?: string;
  lastAttempt?: string;
  processingTime?: number;
}

export interface TranscriptionResult {
  success: boolean;
  audioFile: string;
  result?: any; // Will be typed as DeepgramResponse in deepgram.ts
  error?: string;
  processingTime?: number;
  cacheFile?: string;
  compressedAudio?: string;
}

export interface AudioMetadata {
  duration: number;
  size: number;
  format: string;
  sampleRate?: number;
  channels?: number;
}

export interface PublishResult {
  success: boolean;
  localPath: string;
  error?: string;
}

export interface TranscriptMetadata {
  filename: string;
  title: string;
  duration: number;
  publishDate: string;
  fileSize: number;
  compressedSize: number;
  speakerNames?: { [speakerIndex: number]: string };
}