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
 * Extended Deepgram response with manual corrections
 */
export interface CorrectedDeepgramResponse extends DeepgramResponse {
  corrections?: {
    version: number;
    timestamp: string;
    speaker_names?: {
      [speakerIndex: number]: string; // Maps "0" -> "Dr. Smith", "1" -> "Student A", etc.
    };
  };
  // Note: Word-level corrections are embedded directly in raw_response.results.channels[0].alternatives[0].words
  // Each word can have additional properties: corrected?: boolean, original_word?: string, original_punct?: string
}

/**
 * Extended word interface for corrected transcripts
 */
export interface CorrectedDeepgramWord extends DeepgramWord {
  corrected?: boolean;
  original_word?: string;
  original_punct?: string;
}