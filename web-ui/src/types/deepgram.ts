/**
 * Deepgram API response types and corrected response structures
 */

export interface DeepgramWord {
  word: string;
  start: number;
  end: number;
  confidence: number;
  speaker: number;
  speaker_confidence: number;
  punctuated_word: string;
}

export interface DeepgramSentence {
  text: string;
  start: number;
  end: number;
  words: DeepgramWord[];
  speaker: number;
  id: string;
}

export interface DeepgramParagraph {
  sentences: DeepgramSentence[];
}

export interface DeepgramAlternative {
  transcript: string;
  words: DeepgramWord[];
  paragraphs: {
    transcript: string;
    paragraphs: DeepgramParagraph[];
  };
}

export interface DeepgramChannel {
  alternatives: DeepgramAlternative[];
}

export interface DeepgramModelInfo {
  name: string;
  version: string;
  arch: string;
}

export interface DeepgramMetadata {
  request_id: string;
  sha256: string;
  created: string;
  duration: number;
  channels: number;
  models: string[];
  model_info: {
    [modelId: string]: DeepgramModelInfo;
  };
}

export interface DeepgramResults {
  channels: DeepgramChannel[];
}

export interface DeepgramRawResponse {
  metadata: DeepgramMetadata;
  results: DeepgramResults;
}

export interface DeepgramSpeaker {
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number;
}

export interface DeepgramResponse {
  text: string;
  speakers: DeepgramSpeaker[];
  confidence: number;
  audio_duration: number;
  processing_time: number;
  raw_response: DeepgramRawResponse;
}

export interface DeepgramCacheFile {
  audio_file: string;
  service: string;
  config: {
    speaker_labels: boolean;
    custom_vocabulary: string[];
    punctuate: boolean;
    format_text: boolean;
    language_code: string;
    max_speakers: number;
  };
  timestamp: string;
  result: DeepgramResponse;
}

/**
 * RichWordsTranscript - Simplified transcript format with word-level data
 * Words are at top-level with paragraph boundaries marked on words themselves
 * This is the single source of truth - paragraphs are reconstructed from word-level markers
 */
export interface RichWordsTranscript {
  // Words with paragraph boundaries marked
  words: CorrectedDeepgramWord[];
  
  // Corrections metadata (speaker names, etc.)
  corrections?: {
    version: number;
    timestamp: string;
    speaker_names?: {
      [speakerIndex: number]: string; // Maps "0" -> "Dr. Smith", "1" -> "Student A", etc.
    };
  };
}

// Legacy alias for backward compatibility during migration
export type CorrectedDeepgramResponse = RichWordsTranscript;

/**
 * Extended word interface for corrected transcripts
 */
export interface CorrectedDeepgramWord extends DeepgramWord {
  corrected?: boolean;
  original_word?: string;
  original_punct?: string;
  paragraph_start?: boolean;  // True if this word starts a paragraph (from Deepgram paragraphs)
  paragraph_end?: boolean;    // True if this word ends a paragraph (from Deepgram paragraphs)
}