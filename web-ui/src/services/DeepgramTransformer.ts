/**
 * DeepgramTransformer Service
 * 
 * Handles bidirectional transformation between RichWordsTranscript and ReactTranscriptEditorData formats.
 * Preserves word-level corrections and speaker name mappings throughout the transformation process.
 * 
 * Note: Python backend always generates RichWordsTranscript format with correct paragraph markers.
 * This service only validates the format and transforms to ReactTranscriptEditorData - no raw Deepgram parsing.
 */

import { 
  RichWordsTranscript,
  CorrectedDeepgramResponse, // Legacy alias
  CorrectedDeepgramWord,
  // DeepgramWord // TODO: Use when needed
} from '../types/deepgram';
import { 
  ReactTranscriptEditorData
} from '../types/transcriptEditor';

export class DeepgramTransformer {
  /**
   * Validates that response is in RichWordsTranscript format
   * Python backend always generates this format, so we just validate it
   * Throws error if format is invalid (should regenerate from cache using Python script)
   */
  static normalizeToSimplifiedFormat(response: any): RichWordsTranscript {
    // Python backend always generates RichWordsTranscript format with words at top-level
    // and paragraph markers already set correctly
    if (response.words && Array.isArray(response.words)) {
      return response as RichWordsTranscript;
    }

    // If not in expected format, provide helpful error
    throw new Error(
      'Transcript is not in RichWordsTranscript format. ' +
      'Please regenerate it using: python scripts/regenerate_transcription_from_cache.py <audio_file>'
    );
  }

  /**
   * Transforms RichWordsTranscript to ReactTranscriptEditorData format
   * Preserves word-level corrections and speaker name mappings
   */
  static transformToReactTranscriptEditor(response: RichWordsTranscript | any): ReactTranscriptEditorData {
    // Normalize to new format first (handles backward compatibility)
    const normalizedResponse = this.normalizeToSimplifiedFormat(response);
    
    console.log('🔄 DeepgramTransformer: Normalized response structure:', {
      wordsCount: normalizedResponse.words.length,
      hasCorrections: !!normalizedResponse.corrections,
      paragraphStarts: normalizedResponse.words.filter(w => w.paragraph_start).length,
      paragraphEnds: normalizedResponse.words.filter(w => w.paragraph_end).length
    });

    // Transform words to the exact format expected by react-transcript-editor
    // Preserve correction metadata and paragraph markers
    const transformedWords = normalizedResponse.words.map((word, index) => {
      const correctedWord = word as CorrectedDeepgramWord;
      return {
        start: correctedWord.start,
        end: correctedWord.end,
        word: correctedWord.word,
        confidence: correctedWord.confidence || 0.9,
        punct: correctedWord.punctuated_word || correctedWord.word,
      index: index,
        speaker: correctedWord.speaker !== undefined ? correctedWord.speaker : 0,
        corrected: correctedWord.corrected,
        original_word: correctedWord.original_word,
        original_punct: correctedWord.original_punct,
        paragraph_start: correctedWord.paragraph_start,
        paragraph_end: correctedWord.paragraph_end
      };
    });

    // Generate speaker segments from words grouped by paragraphs
    // Use paragraph markers to create segments that match paragraph boundaries
    const speakerSegments: any[] = [];
    let currentSegment: any = null;
    const speakerNamesMap = normalizedResponse.corrections?.speaker_names || {};

    transformedWords.forEach((word) => {
      // Start a new segment at paragraph start
      if (word.paragraph_start || !currentSegment) {
        // Save previous segment if exists
        if (currentSegment) {
          speakerSegments.push(currentSegment);
        }
        
        // Get speaker name (use custom name if available)
        const speakerIndex = word.speaker;
        const speakerName = speakerNamesMap[speakerIndex] || `Speaker ${speakerIndex}`;
        
        // Start new segment
        currentSegment = {
          speaker: speakerName,
          start_time: word.start,
          end_time: word.end,
          text: word.punct,
          confidence: word.confidence
        };
      } else {
        // Continue current segment
        currentSegment.end_time = word.end;
        currentSegment.text += ' ' + word.punct;
        // Update confidence (could average, but using last for simplicity)
        currentSegment.confidence = word.confidence;
      }
      
      // End segment at paragraph end
      if (word.paragraph_end && currentSegment) {
        speakerSegments.push(currentSegment);
        currentSegment = null;
      }
    });

    // Add final segment if exists
    if (currentSegment) {
      speakerSegments.push(currentSegment);
    }

    console.log('📊 Generated speaker segments from words:', {
      segmentsCount: speakerSegments.length,
      firstSpeaker: speakerSegments[0]?.speaker || null,
      hasCustomNames: !!normalizedResponse.corrections?.speaker_names
    });

    // Build segmentation for bbckaldi adapter
    // Use paragraph-based segmentation
    const segmentation = this.buildSegmentationFromWords(transformedWords, normalizedResponse);

    // Reconstruct transcript from words
    const transcript = transformedWords.map(w => w.punct).join(' ');

    // Calculate metadata from words
    const duration = transformedWords.length > 0 
      ? transformedWords[transformedWords.length - 1].end 
      : 0;
    const avgConfidence = transformedWords.length > 0
      ? transformedWords.reduce((sum, w) => sum + w.confidence, 0) / transformedWords.length
      : 0;

    const processedData = {
      words: transformedWords,
      speakers: speakerSegments,
      segmentation: segmentation,
      transcript: transcript,
      metadata: {
        duration: duration,
        confidence: avgConfidence,
        service: 'deepgram'
      },
      speaker_names: normalizedResponse.corrections?.speaker_names
    };

    // Log the processed data we're sending to deepgram adapter
    console.log('📤 Data passed to deepgram adapter:', JSON.stringify({
      wordsCount: processedData.words.length,
      utterancesCount: processedData.speakers?.length || 0,
      sampleWords: processedData.words.slice(0, 5),
      sampleUtterances: processedData.speakers?.slice(0, 5)
    }, null, 2));

    return processedData;
  }

  /**
   * Build segmentation from words with paragraph markers
   * Creates segmentation structure for bbckaldi adapter
   */
  static buildSegmentationFromWords(words: any[], transcript: RichWordsTranscript): any {
    const segments: any[] = [];
    let currentSegment: any = null;

    words.forEach((word, index) => {
      // Start new segment at paragraph start
      if (word.paragraph_start || !currentSegment) {
        if (currentSegment) {
          segments.push(currentSegment);
        }
        
        const speakerIndex = word.speaker;
        const speakerNamesMap = transcript.corrections?.speaker_names || {};
        const speakerName = speakerNamesMap[speakerIndex] || `Speaker ${speakerIndex}`;
        
        currentSegment = {
          speaker: speakerName,
          start: word.start,
          end: word.end,
          words: [index],
          text: word.punct
        };
      } else {
        // Continue current segment
        currentSegment.words.push(index);
        currentSegment.end = word.end;
        currentSegment.text += ' ' + word.punct;
      }
      
      // End segment at paragraph end
      if (word.paragraph_end && currentSegment) {
        segments.push(currentSegment);
        currentSegment = null;
      }
    });

    // Add final segment
    if (currentSegment) {
      segments.push(currentSegment);
    }

    // Build speakers list
    const speakerMap = new Map<number, string>();
    words.forEach(word => {
      const speakerIndex = word.speaker;
      const speakerNamesMap = transcript.corrections?.speaker_names || {};
      speakerMap.set(speakerIndex, speakerNamesMap[speakerIndex] || `Speaker ${speakerIndex}`);
    });

    return {
      speakers: Array.from(speakerMap.values()),
      segments: segments
    };
  }

  // REMOVED: Legacy segmentation methods no longer needed
  // Python backend always generates RichWordsTranscript with paragraph markers on words
  // We only use buildSegmentationFromWords() which uses those markers

  /**
   * Merges corrections from ReactTranscriptEditorData back into RichWordsTranscript
   * Updates word-level corrections and speaker name mappings
   */
  static mergeCorrectionsIntoDeepgramResponse(
    original: RichWordsTranscript, 
    edited: ReactTranscriptEditorData
  ): RichWordsTranscript {
    // Create a deep copy of the original response
    const corrected: RichWordsTranscript = JSON.parse(JSON.stringify(original));
    
    // Filter and merge speaker names - only save custom names (not "Speaker X" format)
    let mergedSpeakerNames = { ...(original.corrections?.speaker_names || {}) };
    if (edited.speaker_names) {
      // Merge edited speaker names, filtering out default "Speaker X" format
      for (const [indexStr, name] of Object.entries(edited.speaker_names)) {
        const speakerIndex = parseInt(indexStr);
        // Only save if it's a custom name (not "Speaker X" format)
        if (!name.match(/^Speaker \d+$/)) {
          mergedSpeakerNames[speakerIndex] = name;
        } else {
          // If it's a default name, remove it from the custom names (in case it was custom before)
          delete mergedSpeakerNames[speakerIndex];
        }
      }
    }
    
    // Only include speaker_names if there are custom names
    const finalSpeakerNames = Object.keys(mergedSpeakerNames).length > 0 ? mergedSpeakerNames : undefined;
    
    // Update the corrections metadata
    corrected.corrections = {
      version: (original.corrections?.version || 0) + 1,
      timestamp: new Date().toISOString(),
      speaker_names: finalSpeakerNames
    };

    // Merge word-level corrections directly into words array
    let correctionCount = 0;
    corrected.words = corrected.words.map((originalWord, index) => {
      const editedWord = edited.words[index];
      if (!editedWord) return originalWord;

      const correctedWord = { ...originalWord } as CorrectedDeepgramWord;
      
      // Check if word was modified
      const wordChanged = editedWord.word !== originalWord.word;
      const punctChanged = editedWord.punct !== originalWord.punctuated_word;
      
      if (wordChanged || punctChanged) {
        correctionCount++;
        if (correctionCount <= 3) {
          console.log(`🔧 Correction ${correctionCount}:`, {
            index,
            original: { word: originalWord.word, punct: originalWord.punctuated_word },
            edited: { word: editedWord.word, punct: editedWord.punct },
            wordChanged,
            punctChanged
          });
        }
        
        // Mark as corrected and preserve original values
        correctedWord.corrected = true;
        correctedWord.original_word = correctedWord.original_word || originalWord.word;
        correctedWord.original_punct = correctedWord.original_punct || originalWord.punctuated_word;
        
        // Update with corrected values
        correctedWord.word = editedWord.word;
        correctedWord.punctuated_word = editedWord.punct;
      }
      
      return correctedWord;
    });
    
    console.log(`📊 Merge summary: ${correctionCount} words corrected out of ${corrected.words.length} total`);
    console.log('🎤 Updated speaker names in corrections:', finalSpeakerNames);

    return corrected;
  }

  /**
   * Reconstructs transcript text from corrected words
   * Handles punctuation and spacing properly
   */
  private static reconstructTranscriptFromWords(words: CorrectedDeepgramWord[]): string {
    if (!words || words.length === 0) return '';

    let transcript = '';
    let currentSpeaker = -1;
    
    for (let i = 0; i < words.length; i++) {
      const word = words[i];
      const punctuatedWord = word.punctuated_word || word.word;
      
      // Add speaker change indicators if needed
      if (word.speaker !== currentSpeaker) {
        if (transcript.length > 0) {
          transcript += ' ';
        }
        currentSpeaker = word.speaker;
      } else if (i > 0) {
        // Add space between words from same speaker
        transcript += ' ';
      }
      
      transcript += punctuatedWord;
    }
    
    return transcript;
  }

  /**
   * Validates that a round-trip transformation preserves data integrity
   * Used for testing and validation purposes
   */
  static validateRoundTripTransformation(
    original: RichWordsTranscript,
    transformed: ReactTranscriptEditorData,
    roundTrip: RichWordsTranscript
  ): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    // Validate transformed data structure
    if (!transformed.words || transformed.words.length === 0) {
      errors.push('Transformed data has no words');
    }

    // Check word count consistency
    if (original.words.length !== roundTrip.words.length) {
      errors.push(`Word count mismatch: original ${original.words.length}, round-trip ${roundTrip.words.length}`);
    }

    // Check word-level data preservation
    for (let i = 0; i < Math.min(original.words.length, roundTrip.words.length); i++) {
      const orig = original.words[i];
      const roundTripWord = roundTrip.words[i];
      
      // Timing should be preserved
      if (Math.abs(orig.start - roundTripWord.start) > 0.001) {
        errors.push(`Word ${i} start time mismatch: ${orig.start} vs ${roundTripWord.start}`);
      }
      
      if (Math.abs(orig.end - roundTripWord.end) > 0.001) {
        errors.push(`Word ${i} end time mismatch: ${orig.end} vs ${roundTripWord.end}`);
      }
      
      // Speaker assignment should be preserved
      if (orig.speaker !== roundTripWord.speaker) {
        errors.push(`Word ${i} speaker mismatch: ${orig.speaker} vs ${roundTripWord.speaker}`);
      }
      
      // Confidence should be preserved
      if (Math.abs((orig.confidence || 0) - (roundTripWord.confidence || 0)) > 0.001) {
        errors.push(`Word ${i} confidence mismatch: ${orig.confidence} vs ${roundTripWord.confidence}`);
      }
    }

    return {
      isValid: errors.length === 0,
      errors
    };
  }

  /**
   * Creates a minimal ReactTranscriptEditorData for testing purposes
   */
  static createTestData(): ReactTranscriptEditorData {
    return {
      words: [
        {
          start: 0.48,
          end: 0.8,
          word: "welcome",
          confidence: 0.99,
          punct: "welcome",
          index: 0,
          speaker: 0
        },
        {
          start: 0.8,
          end: 1.2,
          word: "everyone",
          confidence: 0.95,
          punct: "everyone",
          index: 1,
          speaker: 0
        }
      ],
      speakers: [
        {
          speaker: "Speaker 0",
          start_time: 0.48,
          end_time: 1.2,
          text: "welcome everyone",
          confidence: 0.97
        }
      ],
      transcript: "welcome everyone",
      metadata: {
        duration: 10.0,
        confidence: 0.97,
        service: "deepgram"
      }
    };
  }
}