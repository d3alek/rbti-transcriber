/**
 * Confidence level utilities for transcript editor.
 */

import type { ConfidenceLevel, ConfidenceThresholds } from '../types/deepgram';

const DEFAULT_CONFIDENCE_THRESHOLDS: ConfidenceThresholds = {
  high: 0.9,
  medium: 0.7,
  low: 0.0
};

/**
 * Determine confidence level based on score and thresholds.
 */
export function getConfidenceLevel(
  confidence: number,
  thresholds: ConfidenceThresholds = DEFAULT_CONFIDENCE_THRESHOLDS
): ConfidenceLevel {
  if (confidence >= thresholds.high) {
    return 'high';
  } else if (confidence >= thresholds.medium) {
    return 'medium';
  } else {
    return 'low';
  }
}

/**
 * Get CSS class name for confidence level styling.
 */
export function getConfidenceClassName(level: ConfidenceLevel): string {
  switch (level) {
    case 'high':
      return 'confidence-high';
    case 'medium':
      return 'confidence-medium';
    case 'low':
      return 'confidence-low';
    default:
      return 'confidence-unknown';
  }
}

/**
 * Get color for confidence level.
 */
export function getConfidenceColor(level: ConfidenceLevel): string {
  switch (level) {
    case 'high':
      return '#4caf50'; // Green
    case 'medium':
      return '#ff9800'; // Orange
    case 'low':
      return '#f44336'; // Red
    default:
      return '#9e9e9e'; // Gray
  }
}

/**
 * Calculate average confidence for a collection of words.
 */
export function calculateAverageConfidence(confidences: number[]): number {
  if (confidences.length === 0) return 0;
  
  const sum = confidences.reduce((acc, conf) => acc + conf, 0);
  return sum / confidences.length;
}

/**
 * Format confidence score for display.
 */
export function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

/**
 * Check if confidence score is within acceptable range.
 */
export function isValidConfidence(confidence: number): boolean {
  return confidence >= 0 && confidence <= 1;
}