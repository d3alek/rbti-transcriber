/**
 * Service for processing Deepgram responses and managing transcript data.
 */

import type {
  DeepgramResponse,
  ParagraphData,
  SentenceData,
  WordData,
  CachedTranscriptionResponse
} from '../types';
import { validateDeepgramResponse } from '../utils/validation';

export class TranscriptProcessor {
  /**
   * Extract paragraph data from a raw Deepgram response.
   */
  extractParagraphs(response: DeepgramResponse): ParagraphData[] {
    const validation = validateDeepgramResponse(response);
    if (!validation.isValid) {
      const errorMessages = validation.errors.join(', ');
      throw new Error(`Invalid Deepgram response: ${errorMessages}`);
    }

    const paragraphs: ParagraphData[] = [];
    
    // Get the first channel and alternative (standard for single-channel audio)
    const channel = response.results.channels[0];
    const alternative = channel.alternatives[0];
    
    if (!alternative.paragraphs?.paragraphs) {
      // Fallback: create paragraphs from sentences if paragraphs structure is missing
      return this.createParagraphsFromWords(alternative.words);
    }

    alternative.paragraphs.paragraphs.forEach((paragraph, index) => {
      const paragraphData = this.processParagraph(paragraph, index);
      if (paragraphData) {
        paragraphs.push(paragraphData);
      }
    });

    return paragraphs;
  }

  /**
   * Process a single paragraph from Deepgram response.
   */
  private processParagraph(paragraph: any, index: number): ParagraphData | null {
    if (!paragraph.sentences || paragraph.sentences.length === 0) {
      return null;
    }

    const sentences: SentenceData[] = [];
    const allWords: WordData[] = [];
    let startTime = Infinity;
    let endTime = 0;
    let totalConfidence = 0;
    let wordCount = 0;
    let speaker = 0;

    // Process each sentence in the paragraph
    paragraph.sentences.forEach((sentence: any, sentenceIndex: number) => {
      if (sentence.words && sentence.words.length > 0) {
        const sentenceWords = sentence.words.map((w: any, wordIndex: number): WordData => ({
          word: w.word,
          start: w.start,
          end: w.end,
          confidence: w.confidence,
          speaker: w.speaker || 0,
          speaker_confidence: w.speaker_confidence || 0,
          punctuated_word: w.punctuated_word || w.word,
          index: allWords.length + wordIndex
        }));

        const sentenceData: SentenceData = {
          id: `${index}-${sentenceIndex}`,
          text: sentence.text || sentenceWords.map((w: WordData) => w.punctuated_word || w.word).join(' '),
          start: sentence.start || sentenceWords[0].start,
          end: sentence.end || sentenceWords[sentenceWords.length - 1].end,
          words: sentenceWords,
          speaker: sentence.speaker || sentenceWords[0].speaker || 0
        };

        sentences.push(sentenceData);
        allWords.push(...sentenceWords);

        // Update paragraph timing and confidence
        startTime = Math.min(startTime, sentenceData.start);
        endTime = Math.max(endTime, sentenceData.end);
        
        sentenceWords.forEach((word: WordData) => {
          totalConfidence += word.confidence;
          wordCount++;
        });

        // Use the most common speaker in the paragraph
        speaker = sentenceData.speaker;
      }
    });

    if (allWords.length === 0) {
      return null;
    }

    const paragraphText = sentences.map(s => s.text).join(' ');
    const averageConfidence = wordCount > 0 ? totalConfidence / wordCount : 0;

    return {
      id: `paragraph-${index}`,
      text: paragraphText,
      startTime: startTime === Infinity ? 0 : startTime,
      endTime,
      speaker,
      sentences,
      words: allWords,
      confidence: averageConfidence
    };
  }

  /**
   * Create paragraphs from words when paragraph structure is missing.
   */
  private createParagraphsFromWords(words: WordData[]): ParagraphData[] {
    if (!words || words.length === 0) {
      return [];
    }

    const paragraphs: ParagraphData[] = [];
    const PARAGRAPH_BREAK_THRESHOLD = 2.0; // seconds of silence to break paragraph
    const MAX_PARAGRAPH_DURATION = 30.0; // maximum paragraph length in seconds

    let currentParagraphWords: WordData[] = [];
    let currentSpeaker = words[0].speaker || 0;
    let paragraphStartTime = words[0].start;
    let paragraphIndex = 0;

    for (let i = 0; i < words.length; i++) {
      const word = { ...words[i], index: i };
      const nextWord = words[i + 1];
      
      // Check if we should start a new paragraph
      const shouldBreak = 
        // Speaker change
        word.speaker !== currentSpeaker ||
        // Long silence
        (nextWord && (nextWord.start - word.end) > PARAGRAPH_BREAK_THRESHOLD) ||
        // Maximum duration reached
        (word.end - paragraphStartTime) > MAX_PARAGRAPH_DURATION ||
        // End of words
        i === words.length - 1;

      currentParagraphWords.push(word);

      if (shouldBreak) {
        const paragraph = this.createParagraphFromWords(
          currentParagraphWords,
          paragraphIndex,
          currentSpeaker
        );
        
        if (paragraph) {
          paragraphs.push(paragraph);
        }

        // Reset for next paragraph
        currentParagraphWords = [];
        currentSpeaker = nextWord?.speaker || currentSpeaker;
        paragraphStartTime = nextWord?.start || 0;
        paragraphIndex++;
      }
    }

    return paragraphs;
  }

  /**
   * Create a paragraph from a collection of words.
   */
  private createParagraphFromWords(
    words: WordData[],
    index: number,
    speaker: number
  ): ParagraphData | null {
    if (words.length === 0) {
      return null;
    }

    const text = words.map(w => w.punctuated_word || w.word).join(' ');
    const startTime = words[0].start;
    const endTime = words[words.length - 1].end;
    const totalConfidence = words.reduce((sum, w) => sum + w.confidence, 0);
    const averageConfidence = totalConfidence / words.length;

    // Create a single sentence for this paragraph
    const sentence: SentenceData = {
      id: `${index}-0`,
      text,
      start: startTime,
      end: endTime,
      words,
      speaker
    };

    return {
      id: `paragraph-${index}`,
      text,
      startTime,
      endTime,
      speaker,
      sentences: [sentence],
      words,
      confidence: averageConfidence
    };
  }

  /**
   * Update paragraph text and recalculate timing data.
   */
  updateParagraphText(
    response: DeepgramResponse,
    _paragraphId: string,
    _newText: string
  ): DeepgramResponse {
    // This is a complex operation that would need to:
    // 1. Find the paragraph in the response
    // 2. Update the text
    // 3. Recalculate word timing based on the new text
    // 4. Update the response structure
    
    // For now, return a deep copy with the text updated
    // In a full implementation, this would use more sophisticated timing adjustment
    const updatedResponse = JSON.parse(JSON.stringify(response));
    
    // TODO: Implement sophisticated text update with timing preservation
    // This would involve:
    // - Text diff analysis
    // - Word alignment algorithms
    // - Timing interpolation for new/changed words
    
    return updatedResponse;
  }

  /**
   * Find the word being spoken at a specific time.
   */
  findWordAtTime(response: DeepgramResponse, time: number): WordData | null {
    const channel = response.results.channels[0];
    const alternative = channel.alternatives[0];
    
    if (!alternative.words) {
      return null;
    }

    // Binary search for efficiency with large word arrays
    let left = 0;
    let right = alternative.words.length - 1;
    
    while (left <= right) {
      const mid = Math.floor((left + right) / 2);
      const word = alternative.words[mid];
      
      if (time >= word.start && time <= word.end) {
        return { ...word, index: mid };
      } else if (time < word.start) {
        right = mid - 1;
      } else {
        left = mid + 1;
      }
    }
    
    // If no exact match, find the closest word
    const closestIndex = Math.min(left, alternative.words.length - 1);
    return { ...alternative.words[closestIndex], index: closestIndex };
  }

  /**
   * Calculate timing adjustments for edited text.
   */
  calculateTimingAdjustments(
    originalText: string,
    newText: string,
    words: WordData[]
  ): WordData[] {
    // Simplified implementation - in practice, this would use:
    // - Levenshtein distance for text comparison
    // - Word alignment algorithms
    // - Timing interpolation for new words
    
    if (originalText === newText) {
      return words;
    }
    
    // For now, return the original words
    // TODO: Implement sophisticated timing adjustment
    return words;
  }

  /**
   * Extract speaker information from Deepgram response.
   */
  extractSpeakers(response: DeepgramResponse): Array<{ id: number; name: string; confidence: number }> {
    const channel = response.results.channels[0];
    const alternative = channel.alternatives[0];
    
    if (!alternative.words) {
      return [];
    }

    const speakerMap = new Map<number, { totalConfidence: number; wordCount: number }>();
    
    alternative.words.forEach(word => {
      const speakerId = word.speaker || 0;
      const existing = speakerMap.get(speakerId) || { totalConfidence: 0, wordCount: 0 };
      
      speakerMap.set(speakerId, {
        totalConfidence: existing.totalConfidence + (word.speaker_confidence || 0),
        wordCount: existing.wordCount + 1
      });
    });

    return Array.from(speakerMap.entries()).map(([id, data]) => ({
      id,
      name: `Speaker ${id}`,
      confidence: data.wordCount > 0 ? data.totalConfidence / data.wordCount : 0
    }));
  }

  /**
   * Convert cached transcription response to paragraph format.
   */
  processCachedResponse(cachedResponse: CachedTranscriptionResponse): ParagraphData[] {
    return this.extractParagraphs(cachedResponse.raw_response);
  }
}

export const transcriptProcessor = new TranscriptProcessor();