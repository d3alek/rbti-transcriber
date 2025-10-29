/**
 * Validation schemas and error handling types for Deepgram responses and transcript data.
 */

import type { WordData, ParagraphData, SentenceData } from './deepgram';

// Validation result types (using string arrays to match deepgram.ts)
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

export interface ValidationWarning {
  field: string;
  message: string;
  value?: any;
}

// Error categories
export const ErrorType = {
  FILE_SYSTEM: 'file_system',
  DATA_INTEGRITY: 'data_integrity',
  UI_STATE: 'ui_state',
  VALIDATION: 'validation',
  AUDIO_SYNC: 'audio_sync',
  VERSION_CONFLICT: 'version_conflict'
} as const;

export interface TranscriptError {
  type: typeof ErrorType[keyof typeof ErrorType];
  message: string;
  details?: any;
  recoverable: boolean;
  timestamp: string;
}

// Validation functions interface
export interface DeepgramValidator {
  validateResponse(response: any): ValidationResult;
  validateWordData(word: WordData): ValidationResult;
  validateParagraphData(paragraph: ParagraphData): ValidationResult;
  validateSentenceData(sentence: SentenceData): ValidationResult;
  validateTimingConsistency(words: WordData[]): ValidationResult;
}

// Schema definitions for runtime validation
export const DeepgramResponseSchema = {
  type: 'object',
  required: ['metadata', 'results'],
  properties: {
    metadata: {
      type: 'object',
      required: ['request_id', 'created', 'duration', 'channels', 'models'],
      properties: {
        request_id: { type: 'string' },
        sha256: { type: 'string' },
        created: { type: 'string' },
        duration: { type: 'number', minimum: 0 },
        channels: { type: 'number', minimum: 1 },
        models: { type: 'array', items: { type: 'string' } },
        model_info: { type: 'object' }
      }
    },
    results: {
      type: 'object',
      required: ['channels'],
      properties: {
        channels: {
          type: 'array',
          minItems: 1,
          items: {
            type: 'object',
            required: ['alternatives'],
            properties: {
              alternatives: {
                type: 'array',
                minItems: 1,
                items: {
                  type: 'object',
                  required: ['transcript', 'words'],
                  properties: {
                    transcript: { type: 'string' },
                    words: {
                      type: 'array',
                      items: {
                        type: 'object',
                        required: ['word', 'start', 'end', 'confidence'],
                        properties: {
                          word: { type: 'string' },
                          start: { type: 'number', minimum: 0 },
                          end: { type: 'number', minimum: 0 },
                          confidence: { type: 'number', minimum: 0, maximum: 1 },
                          speaker: { type: 'number', minimum: 0 },
                          speaker_confidence: { type: 'number', minimum: 0, maximum: 1 },
                          punctuated_word: { type: 'string' }
                        }
                      }
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
} as const;

export const WordDataSchema = {
  type: 'object',
  required: ['word', 'start', 'end', 'confidence'],
  properties: {
    word: { type: 'string', minLength: 1 },
    start: { type: 'number', minimum: 0 },
    end: { type: 'number', minimum: 0 },
    confidence: { type: 'number', minimum: 0, maximum: 1 },
    speaker: { type: 'number', minimum: 0 },
    speaker_confidence: { type: 'number', minimum: 0, maximum: 1 },
    punctuated_word: { type: 'string' },
    index: { type: 'number', minimum: 0 }
  }
} as const;

// Confidence thresholds (moved to deepgram.ts to avoid conflicts)
// export const DEFAULT_CONFIDENCE_THRESHOLDS: ConfidenceThresholds = {
//   high: 0.9,
//   medium: 0.7,
//   low: 0.0
// };

// Timing validation constants
export const TIMING_VALIDATION = {
  MAX_WORD_DURATION: 30, // seconds
  MIN_WORD_DURATION: 0.01, // seconds
  MAX_GAP_BETWEEN_WORDS: 5, // seconds
  SYNC_TOLERANCE: 0.1 // 100ms tolerance for audio sync
} as const;
// Confidence level types (moved to deepgram.ts to avoid conflicts)
// export type ConfidenceLevel = 'high' | 'medium' | 'low';

// export interface ConfidenceThresholds {
//   high: number;
//   medium: number;
//   low: number;
// }