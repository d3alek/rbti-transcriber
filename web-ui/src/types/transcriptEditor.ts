/**
 * Types for react-transcript-editor integration and transcript editing
 * Based on the actual format expected by @bbc/react-transcript-editor
 */

export interface ReactTranscriptEditorWord {
  start: number;
  end: number;
  word: string;
  confidence: number;
  punct: string;
  index: number;
  speaker: number;
  corrected?: boolean;
  original_word?: string;
  original_punct?: string;
}

export interface ReactTranscriptEditorSpeaker {
  speaker: string;
  start_time: number;
  end_time: number;
  text: string;
  confidence: number;
}

export interface ReactTranscriptEditorData {
  words: ReactTranscriptEditorWord[];
  speakers: ReactTranscriptEditorSpeaker[];
  segmentation?: any; // bbckaldi segmentation structure for speaker grouping
  transcript: string;
  metadata: {
    duration: number;
    confidence: number;
    service: string;
  };
  speaker_names?: {
    [speakerIndex: number]: string; // Maps "0" -> "Dr. Smith", "1" -> "Student A", etc.
  };
}

export interface TranscriptEditorProps {
  onClick?: () => void;
  title?: string;
  mediaUrl?: string;
  isEditable?: boolean;
  spellCheck?: boolean;
  sttJsonType?: string;
  handleAnalyticsEvents?: (event: AnalyticsEvent) => void;
  fileName?: string;
  transcriptData?: ReactTranscriptEditorData;
  mediaType?: 'audio' | 'video';
  handleAutoSaveChanges?: (data: ReactTranscriptEditorData) => void;
  autoSaveContentType?: string;
}

export interface AnalyticsEvent {
  category: string;
  action: string;
  name: string;
  value: string | number | boolean;
}

export interface SpeakerNameMapping {
  [speakerIndex: number]: string;
}

export interface EditSession {
  audioFile: string;
  originalData: ReactTranscriptEditorData;
  currentData: ReactTranscriptEditorData;
  hasUnsavedChanges: boolean;
  lastSaved?: string;
}

export interface TranscriptEditHistory {
  version: number;
  timestamp: string;
  changes: {
    type: 'word_edit' | 'speaker_rename' | 'bulk_edit';
    wordIndex?: number;
    speakerIndex?: number;
    oldValue?: string;
    newValue?: string;
    description: string;
  }[];
}