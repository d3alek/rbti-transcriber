/**
 * Validation utilities for Deepgram responses and transcript data.
 */

import type {
  WordData,
  ParagraphData,
  ValidationResult
} from '../types';

// Import timing validation constants
const TIMING_VALIDATION = {
  MAX_WORD_DURATION: 30, // seconds
  MIN_WORD_DURATION: 0.01, // seconds
  MAX_GAP_BETWEEN_WORDS: 5, // seconds
  SYNC_TOLERANCE: 0.1 // 100ms tolerance for audio sync
} as const;

/**
 * Validate a complete Deepgram response structure.
 */
export function validateDeepgramResponse(response: any): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Check basic structure
  if (!response || typeof response !== 'object') {
    errors.push('Response must be a valid object');
    return { isValid: false, errors, warnings };
  }

  // Validate metadata
  if (!response.metadata) {
    errors.push('Missing metadata field');
  } else {
    const metadataValidation = validateMetadata(response.metadata);
    errors.push(...metadataValidation.errors);
    warnings.push(...metadataValidation.warnings);
  }

  // Validate results
  if (!response.results) {
    errors.push('Missing results field');
  } else {
    const resultsValidation = validateResults(response.results);
    errors.push(...resultsValidation.errors);
    warnings.push(...resultsValidation.warnings);
  }

  return {
    isValid: errors.length === 0,
    errors,
    warnings
  };
}

/**
 * Validate Deepgram metadata structure.
 */
function validateMetadata(metadata: any): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  const requiredFields = ['request_id', 'created', 'duration', 'channels', 'models'];
  
  for (const field of requiredFields) {
    if (!(field in metadata)) {
      errors.push(`Missing required field: metadata.${field}`);
    }
  }

  // Validate specific field types
  if (metadata.duration !== undefined && (typeof metadata.duration !== 'number' || metadata.duration < 0)) {
    errors.push(`Duration must be a positive number, got: ${metadata.duration}`);
  }

  if (metadata.channels !== undefined && (typeof metadata.channels !== 'number' || metadata.channels < 1)) {
    errors.push(`Channels must be a positive integer, got: ${metadata.channels}`);
  }

  return { isValid: errors.length === 0, errors, warnings };
}

/**
 * Validate Deepgram results structure.
 */
function validateResults(results: any): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!Array.isArray(results.channels)) {
    errors.push('Channels must be an array');
    return { isValid: false, errors, warnings };
  }

  if (results.channels.length === 0) {
    errors.push('At least one channel is required');
  }

  // Validate each channel
  results.channels.forEach((channel: any, channelIndex: number) => {
    if (!Array.isArray(channel.alternatives)) {
      errors.push(`Channel ${channelIndex} alternatives must be an array`);
      return;
    }

    if (channel.alternatives.length === 0) {
      errors.push(`Channel ${channelIndex} must have at least one alternative`);
    }

    // Validate each alternative
    channel.alternatives.forEach((alternative: any, altIndex: number) => {
      const altValidation = validateAlternative(alternative, `results.channels[${channelIndex}].alternatives[${altIndex}]`);
      errors.push(...altValidation.errors);
      warnings.push(...altValidation.warnings);
    });
  });

  return { isValid: errors.length === 0, errors, warnings };
}

/**
 * Validate a Deepgram alternative structure.
 */
function validateAlternative(alternative: any, fieldPath: string): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (typeof alternative.transcript !== 'string') {
    errors.push(`${fieldPath}.transcript must be a string`);
  }

  if (!Array.isArray(alternative.words)) {
    errors.push(`${fieldPath}.words must be an array`);
  } else {
    // Validate word timing consistency
    const timingValidation = validateWordTimingConsistency(alternative.words);
    errors.push(...timingValidation.errors.map(err => `${fieldPath}.words.${err}`));
    warnings.push(...timingValidation.warnings.map(warn => `${fieldPath}.words.${warn}`));
  }

  return { isValid: errors.length === 0, errors, warnings };
}

/**
 * Validate word-level data structure.
 */
export function validateWordData(word: WordData): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Required fields
  if (!word.word || typeof word.word !== 'string') {
    errors.push('Word text is required and must be a string');
  }

  if (typeof word.start !== 'number' || word.start < 0) {
    errors.push(`Start time must be a non-negative number, got: ${word.start}`);
  }

  if (typeof word.end !== 'number' || word.end < 0) {
    errors.push(`End time must be a non-negative number, got: ${word.end}`);
  }

  if (typeof word.confidence !== 'number' || word.confidence < 0 || word.confidence > 1) {
    errors.push(`Confidence must be a number between 0 and 1, got: ${word.confidence}`);
  }

  // Timing validation
  if (word.start >= word.end) {
    errors.push(`Start time must be less than end time: start=${word.start}, end=${word.end}`);
  }

  const duration = word.end - word.start;
  if (duration > TIMING_VALIDATION.MAX_WORD_DURATION) {
    warnings.push(`Word duration (${duration.toFixed(2)}s) exceeds maximum expected duration`);
  }

  if (duration < TIMING_VALIDATION.MIN_WORD_DURATION) {
    warnings.push(`Word duration (${duration.toFixed(2)}s) is below minimum expected duration`);
  }

  return { isValid: errors.length === 0, errors, warnings };
}

/**
 * Validate timing consistency across multiple words.
 */
export function validateWordTimingConsistency(words: WordData[]): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!Array.isArray(words) || words.length === 0) {
    return { isValid: true, errors, warnings };
  }

  // Check for overlapping or out-of-order words
  for (let i = 1; i < words.length; i++) {
    const prevWord = words[i - 1];
    const currentWord = words[i];

    if (currentWord.start < prevWord.end) {
      const overlap = prevWord.end - currentWord.start;
      if (overlap > TIMING_VALIDATION.SYNC_TOLERANCE) {
        warnings.push(`Word ${i} overlaps with previous word by ${overlap.toFixed(3)}s: ${prevWord.word} -> ${currentWord.word}`);
      }
    }

    const gap = currentWord.start - prevWord.end;
    if (gap > TIMING_VALIDATION.MAX_GAP_BETWEEN_WORDS) {
      warnings.push(`Large gap (${gap.toFixed(2)}s) between words ${i-1} and ${i}: ${prevWord.word} -> ${currentWord.word}`);
    }
  }

  return { isValid: errors.length === 0, errors, warnings };
}

/**
 * Validate paragraph data structure.
 */
export function validateParagraphData(paragraph: ParagraphData): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  if (!paragraph.id || typeof paragraph.id !== 'string') {
    errors.push('Paragraph ID is required and must be a string');
  }

  if (!paragraph.text || typeof paragraph.text !== 'string') {
    errors.push('Paragraph text is required and must be a string');
  }

  if (typeof paragraph.startTime !== 'number' || paragraph.startTime < 0) {
    errors.push('Start time must be a non-negative number');
  }

  if (typeof paragraph.endTime !== 'number' || paragraph.endTime < 0) {
    errors.push('End time must be a non-negative number');
  }

  if (paragraph.startTime >= paragraph.endTime) {
    errors.push('Start time must be less than end time');
  }

  // Validate words array
  if (!Array.isArray(paragraph.words)) {
    errors.push('Words must be an array');
  } else {
    const wordsValidation = validateWordTimingConsistency(paragraph.words);
    errors.push(...wordsValidation.errors);
    warnings.push(...wordsValidation.warnings);
  }

  return { isValid: errors.length === 0, errors, warnings };
}

/**
 * Check if a value is a valid timestamp.
 */
export function isValidTimestamp(timestamp: any): boolean {
  if (typeof timestamp === 'number') {
    return timestamp >= 0 && isFinite(timestamp);
  }
  if (typeof timestamp === 'string') {
    const parsed = parseFloat(timestamp);
    return !isNaN(parsed) && parsed >= 0;
  }
  return false;
}