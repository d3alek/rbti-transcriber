/**
 * CorrectionManager Service
 * 
 * Handles advanced correction operations including batch corrections,
 * speaker name management, and correction history tracking.
 */

import { 
  CorrectedDeepgramResponse, 
  CorrectedDeepgramWord 
} from '../types/deepgram';
import { 
  ReactTranscriptEditorData,
  SpeakerNameMapping,
  TranscriptEditHistory 
} from '../types/transcriptEditor';
// import { DeepgramTransformer } from './DeepgramTransformer'; // TODO: Use when needed

export interface WordCorrection {
  wordIndex: number;
  newWord: string;
  newPunct?: string;
  reason?: string;
}

export interface SpeakerCorrection {
  speakerIndex: number;
  newName: string;
}

export interface BatchCorrectionResult {
  success: boolean;
  correctedResponse: CorrectedDeepgramResponse;
  appliedCorrections: number;
  errors: string[];
}

export class CorrectionManager {
  /**
   * Applies a batch of word corrections to a CorrectedDeepgramResponse
   */
  static applyWordCorrections(
    response: CorrectedDeepgramResponse,
    corrections: WordCorrection[]
  ): BatchCorrectionResult {
    const errors: string[] = [];
    let appliedCorrections = 0;
    
    // Create a deep copy
    const corrected: CorrectedDeepgramResponse = JSON.parse(JSON.stringify(response));
    
    // Get the words array
    const words = corrected.raw_response.results.channels[0].alternatives[0].words as CorrectedDeepgramWord[];
    
    // Apply each correction
    for (const correction of corrections) {
      if (correction.wordIndex < 0 || correction.wordIndex >= words.length) {
        errors.push(`Invalid word index: ${correction.wordIndex}`);
        continue;
      }
      
      const word = words[correction.wordIndex];
      
      // Store original values if not already corrected
      if (!word.corrected) {
        word.original_word = word.word;
        word.original_punct = word.punctuated_word;
      }
      
      // Apply correction
      word.word = correction.newWord;
      word.punctuated_word = correction.newPunct || correction.newWord;
      word.corrected = true;
      
      appliedCorrections++;
    }
    
    // Update corrections metadata
    corrected.corrections = {
      version: (response.corrections?.version || 0) + 1,
      timestamp: new Date().toISOString(),
      speaker_names: response.corrections?.speaker_names
    };
    
    // Reconstruct transcript
    const newTranscript = this.reconstructTranscriptFromWords(words);
    corrected.raw_response.results.channels[0].alternatives[0].transcript = newTranscript;
    corrected.text = newTranscript;
    
    return {
      success: errors.length === 0,
      correctedResponse: corrected,
      appliedCorrections,
      errors
    };
  }

  /**
   * Applies speaker name corrections to a CorrectedDeepgramResponse
   */
  static applySpeakerNameCorrections(
    response: CorrectedDeepgramResponse,
    speakerCorrections: SpeakerCorrection[]
  ): CorrectedDeepgramResponse {
    const corrected: CorrectedDeepgramResponse = JSON.parse(JSON.stringify(response));
    
    // Initialize or update speaker names mapping
    const speakerNames: SpeakerNameMapping = {
      ...corrected.corrections?.speaker_names
    };
    
    // Apply speaker name corrections
    for (const correction of speakerCorrections) {
      speakerNames[correction.speakerIndex] = correction.newName;
    }
    
    // Update corrections metadata
    corrected.corrections = {
      version: (response.corrections?.version || 0) + 1,
      timestamp: new Date().toISOString(),
      speaker_names: speakerNames
    };
    
    // Update speaker segments with new names
    corrected.speakers = corrected.speakers.map(speaker => {
      const speakerIndex = parseInt(speaker.speaker.replace('Speaker ', ''));
      const customName = speakerNames[speakerIndex];
      
      return {
        ...speaker,
        speaker: customName || speaker.speaker
      };
    });
    
    return corrected;
  }

  /**
   * Embeds word-level corrections directly into the Deepgram response structure
   */
  static embedWordCorrections(
    response: CorrectedDeepgramResponse,
    editedData: ReactTranscriptEditorData
  ): CorrectedDeepgramResponse {
    const corrected: CorrectedDeepgramResponse = JSON.parse(JSON.stringify(response));
    const words = corrected.raw_response.results.channels[0].alternatives[0].words as CorrectedDeepgramWord[];
    
    // Compare each word with edited data
    for (let i = 0; i < Math.min(words.length, editedData.words.length); i++) {
      const originalWord = words[i];
      const editedWord = editedData.words[i];
      
      // Check if word was modified
      const wordChanged = editedWord.word !== originalWord.word;
      const punctChanged = editedWord.punct !== originalWord.punctuated_word;
      
      if (wordChanged || punctChanged) {
        // Store original if not already corrected
        if (!originalWord.corrected) {
          (originalWord as CorrectedDeepgramWord).original_word = originalWord.word;
          (originalWord as CorrectedDeepgramWord).original_punct = originalWord.punctuated_word;
        }
        
        // Apply corrections
        originalWord.word = editedWord.word;
        originalWord.punctuated_word = editedWord.punct;
        (originalWord as CorrectedDeepgramWord).corrected = true;
      }
    }
    
    return corrected;
  }

  /**
   * Stores speaker name mappings in corrections metadata
   */
  static storeSpeakerNameMappings(
    response: CorrectedDeepgramResponse,
    speakerNames: SpeakerNameMapping
  ): CorrectedDeepgramResponse {
    const corrected: CorrectedDeepgramResponse = JSON.parse(JSON.stringify(response));
    
    corrected.corrections = {
      version: (response.corrections?.version || 0) + 1,
      timestamp: new Date().toISOString(),
      speaker_names: speakerNames
    };
    
    return corrected;
  }

  /**
   * Extracts all corrections from a CorrectedDeepgramResponse
   */
  static extractCorrections(response: CorrectedDeepgramResponse): {
    wordCorrections: WordCorrection[];
    speakerNames: SpeakerNameMapping;
    version: number;
    timestamp: string;
  } {
    const words = response.raw_response.results.channels[0].alternatives[0].words as CorrectedDeepgramWord[];
    const wordCorrections: WordCorrection[] = [];
    
    // Extract word-level corrections
    words.forEach((word, index) => {
      if (word.corrected) {
        wordCorrections.push({
          wordIndex: index,
          newWord: word.word,
          newPunct: word.punctuated_word,
          reason: 'Manual correction'
        });
      }
    });
    
    return {
      wordCorrections,
      speakerNames: response.corrections?.speaker_names || {},
      version: response.corrections?.version || 0,
      timestamp: response.corrections?.timestamp || ''
    };
  }

  /**
   * Validates correction data integrity
   */
  static validateCorrections(
    original: CorrectedDeepgramResponse,
    corrected: CorrectedDeepgramResponse
  ): { isValid: boolean; issues: string[] } {
    const issues: string[] = [];
    
    const originalWords = original.raw_response.results.channels[0].alternatives[0].words;
    const correctedWords = corrected.raw_response.results.channels[0].alternatives[0].words;
    
    // Check word count consistency
    if (originalWords.length !== correctedWords.length) {
      issues.push(`Word count changed: ${originalWords.length} -> ${correctedWords.length}`);
    }
    
    // Check timing preservation
    for (let i = 0; i < Math.min(originalWords.length, correctedWords.length); i++) {
      const orig = originalWords[i];
      const corr = correctedWords[i];
      
      if (Math.abs(orig.start - corr.start) > 0.001) {
        issues.push(`Word ${i} timing changed: start ${orig.start} -> ${corr.start}`);
      }
      
      if (Math.abs(orig.end - corr.end) > 0.001) {
        issues.push(`Word ${i} timing changed: end ${orig.end} -> ${corr.end}`);
      }
      
      if (orig.speaker !== corr.speaker) {
        issues.push(`Word ${i} speaker changed: ${orig.speaker} -> ${corr.speaker}`);
      }
    }
    
    // Check metadata preservation
    if (original.audio_duration !== corrected.audio_duration) {
      issues.push(`Audio duration changed: ${original.audio_duration} -> ${corrected.audio_duration}`);
    }
    
    return {
      isValid: issues.length === 0,
      issues
    };
  }

  /**
   * Creates a correction history entry
   */
  static createHistoryEntry(
    original: CorrectedDeepgramResponse,
    corrected: CorrectedDeepgramResponse,
    description: string
  ): TranscriptEditHistory {
    const changes: TranscriptEditHistory['changes'] = [];
    // Use description for history entry
    console.log('Creating history entry:', description);
    
    const originalWords = original.raw_response.results.channels[0].alternatives[0].words as CorrectedDeepgramWord[];
    const correctedWords = corrected.raw_response.results.channels[0].alternatives[0].words as CorrectedDeepgramWord[];
    
    // Track word changes
    for (let i = 0; i < Math.min(originalWords.length, correctedWords.length); i++) {
      const orig = originalWords[i];
      const corr = correctedWords[i];
      
      if (orig.word !== corr.word || orig.punctuated_word !== corr.punctuated_word) {
        changes.push({
          type: 'word_edit',
          wordIndex: i,
          oldValue: `${orig.word}|${orig.punctuated_word}`,
          newValue: `${corr.word}|${corr.punctuated_word}`,
          description: `Word ${i}: "${orig.word}" -> "${corr.word}"`
        });
      }
    }
    
    // Track speaker name changes
    const originalSpeakerNames = original.corrections?.speaker_names || {};
    const correctedSpeakerNames = corrected.corrections?.speaker_names || {};
    
    for (const speakerIndex in correctedSpeakerNames) {
      const oldName = originalSpeakerNames[parseInt(speakerIndex)];
      const newName = correctedSpeakerNames[parseInt(speakerIndex)];
      
      if (oldName !== newName) {
        changes.push({
          type: 'speaker_rename',
          speakerIndex: parseInt(speakerIndex),
          oldValue: oldName || `Speaker ${speakerIndex}`,
          newValue: newName,
          description: `Speaker ${speakerIndex}: "${oldName || `Speaker ${speakerIndex}`}" -> "${newName}"`
        });
      }
    }
    
    return {
      version: corrected.corrections?.version || 1,
      timestamp: new Date().toISOString(),
      changes
    };
  }

  /**
   * Reconstructs transcript text from corrected words
   */
  private static reconstructTranscriptFromWords(words: CorrectedDeepgramWord[]): string {
    if (!words || words.length === 0) return '';

    let transcript = '';
    
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const punctuatedWord = word.punctuated_word || word.word;
      
      if (i > 0) {
        transcript += ' ';
      }
      
      transcript += punctuatedWord;
    }
    
    return transcript;
  }
}