/**
 * Constants for the enhanced transcript editor.
 */

import type { ConfidenceThresholds } from '../types/deepgram';

// Confidence level thresholds
export const CONFIDENCE_THRESHOLDS: ConfidenceThresholds = {
  high: 0.9,
  medium: 0.7,
  low: 0.0
};

// Audio synchronization settings
export const AUDIO_SYNC = {
  UPDATE_INTERVAL: 100, // milliseconds
  SEEK_TOLERANCE: 0.1, // seconds
  HIGHLIGHT_TOLERANCE: 0.05, // seconds for word highlighting
  SCROLL_OFFSET: 100 // pixels to keep highlighted word visible
} as const;

// Version management settings
export const VERSION_MANAGEMENT = {
  MAX_VERSIONS: 50,
  AUTO_SAVE_INTERVAL: 300000, // 5 minutes in milliseconds
  VERSION_NAME_MAX_LENGTH: 100
} as const;

// UI settings
export const UI_SETTINGS = {
  PARAGRAPH_MIN_HEIGHT: 60, // pixels
  WORD_HIGHLIGHT_DURATION: 200, // milliseconds for transition
  CONFIDENCE_INDICATOR_SIZE: 4, // pixels for confidence dots
  VIRTUAL_SCROLL_ITEM_HEIGHT: 80 // pixels for virtual scrolling
} as const;

// File system paths
export const FILE_PATHS = {
  TRANSCRIPTIONS_DIR: 'transcriptions',
  VERSIONS_DIR: 'versions',
  CACHE_DIR: 'cache',
  AUDIO_DIR: 'audio'
} as const;

// API endpoints
export const API_ENDPOINTS = {
  TRANSCRIPTS: '/api/transcripts',
  VERSIONS: '/api/transcripts/{audioHash}/versions',
  PARAGRAPHS: '/api/transcripts/{audioHash}/paragraphs',
  AUDIO: '/api/audio'
} as const;

// Keyboard shortcuts
export const KEYBOARD_SHORTCUTS = {
  SAVE_VERSION: 'Ctrl+S',
  PLAY_PAUSE: 'Space',
  SEEK_BACKWARD: 'ArrowLeft',
  SEEK_FORWARD: 'ArrowRight',
  JUMP_TO_WORD: 'Enter',
  EDIT_PARAGRAPH: 'F2',
  CANCEL_EDIT: 'Escape'
} as const;

// Error messages
export const ERROR_MESSAGES = {
  INVALID_DEEPGRAM_RESPONSE: 'Invalid Deepgram response format',
  VERSION_LOAD_FAILED: 'Failed to load transcript version',
  AUDIO_SYNC_FAILED: 'Audio synchronization failed',
  SAVE_VERSION_FAILED: 'Failed to save new version',
  VALIDATION_FAILED: 'Data validation failed',
  FILE_NOT_FOUND: 'Transcript file not found',
  PERMISSION_DENIED: 'Permission denied accessing transcript files'
} as const;

// Success messages
export const SUCCESS_MESSAGES = {
  VERSION_SAVED: 'New version saved successfully',
  VERSION_LOADED: 'Version loaded successfully',
  PARAGRAPH_UPDATED: 'Paragraph updated successfully',
  AUDIO_SYNCED: 'Audio synchronized with transcript'
} as const;

// CSS class names
export const CSS_CLASSES = {
  CONFIDENCE_HIGH: 'confidence-high',
  CONFIDENCE_MEDIUM: 'confidence-medium',
  CONFIDENCE_LOW: 'confidence-low',
  WORD_HIGHLIGHTED: 'word-highlighted',
  PARAGRAPH_EDITING: 'paragraph-editing',
  SPEAKER_INDICATOR: 'speaker-indicator',
  VERSION_CURRENT: 'version-current',
  ERROR_STATE: 'error-state'
} as const;

// Timing validation constants
export const TIMING_VALIDATION = {
  MAX_WORD_DURATION: 30, // seconds
  MIN_WORD_DURATION: 0.01, // seconds
  MAX_GAP_BETWEEN_WORDS: 5, // seconds
  SYNC_TOLERANCE: 0.1 // 100ms tolerance for audio sync
} as const;

// Performance settings
export const PERFORMANCE = {
  DEBOUNCE_DELAY: 300, // milliseconds for input debouncing
  THROTTLE_DELAY: 100, // milliseconds for scroll/resize throttling
  VIRTUAL_SCROLL_BUFFER: 5, // number of items to render outside viewport
  MAX_RENDERED_PARAGRAPHS: 100 // maximum paragraphs to render at once
} as const;