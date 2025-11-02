/**
 * DeepgramTransformer Service
 * 
 * Handles bidirectional transformation between RichWordsTranscript and ReactTranscriptEditorData formats.
 * Preserves word-level corrections and speaker name mappings throughout the transformation process.
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
   * Normalizes response to RichWordsTranscript format
   * Converts old format (with raw_response) to new format (words at top-level with paragraph markers)
   * Handles backward compatibility with old format
   */
  static normalizeToSimplifiedFormat(response: any): RichWordsTranscript {
    // Check if already in new format (has words at top-level)
    if (response.words && Array.isArray(response.words)) {
      return response as RichWordsTranscript;
    }

    // Old format: extract from raw_response
    const rawResponse = (response as any).raw_response;
    
    if (!rawResponse || !rawResponse.results || !rawResponse.results.channels) {
      throw new Error('Invalid Deepgram response structure - missing raw_response');
    }

    const channel = rawResponse.results.channels[0];
    const alternative = channel.alternatives[0];

    if (!alternative || !alternative.words) {
      throw new Error('No words found in Deepgram response');
    }

    // Extract words
    const words = alternative.words.map((word: any) => ({
      ...word,
      // Preserve any correction metadata
      corrected: word.corrected,
      original_word: word.original_word,
      original_punct: word.original_punct,
      paragraph_start: false,  // Will be set below
      paragraph_end: false     // Will be set below
    }));

    // Enrich words with paragraph markers from Deepgram paragraphs
    const paragraphs = alternative.paragraphs?.paragraphs || [];
    if (paragraphs.length > 0) {
      paragraphs.forEach((paragraph: any) => {
        const paraStart = paragraph.start;
        const paraEnd = paragraph.end;

        // Find words that match paragraph start/end times (within 0.1s tolerance)
        for (let i = 0; i < words.length; i++) {
          const word = words[i];
          
          // Mark paragraph start - word start time matches paragraph start
          if (Math.abs(word.start - paraStart) < 0.1) {
            word.paragraph_start = true;
          }
          
          // Mark paragraph end - word end time matches paragraph end
          if (Math.abs(word.end - paraEnd) < 0.1) {
            word.paragraph_end = true;
          }
        }
      });
    }

    // Return simplified format
    return {
      words: words as CorrectedDeepgramWord[],
      corrections: (response as any).corrections
    };
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

  static buildSegmentationFromDeepgramData(alternative: any, words: any[], deepgramResponse: any): any {
    // Use utterance-level speaker segments from result.speakers if available (best granularity)
    if (deepgramResponse && deepgramResponse.speakers && deepgramResponse.speakers.length > 0) {
      return this.buildSegmentationFromUtterances(deepgramResponse.speakers, words);
    }
    
    // Fall back to sentence-based from paragraphs
    if (alternative.paragraphs && alternative.paragraphs.paragraphs) {
      return this.buildSegmentationFromParagraphs(alternative.paragraphs.paragraphs, words);
    }
    
    // Fallback to simple speaker grouping
    return this.buildSegmentationFromSpeakerOnly(words);
  }

  /**
   * Build segmentation from Deepgram utterance-level speaker segments (result.speakers)
   * These are the finest-grained segments with proper speaker attribution
   */
  static buildSegmentationFromUtterances(utterances: any[], words: any[]): any {
    if (utterances.length === 0) {
      return null;
    }

    const uniqueSpeakers = Array.from(new Set(utterances.map(u => u.speaker))).sort();
    const speakerList = uniqueSpeakers.map(speakerLabel => {
      // Extract speaker number from "Speaker 0", "Speaker 1", etc.
      const speakerNum = parseInt(speakerLabel.replace('Speaker ', '')) || 0;
      return {
        '@id': `S${speakerNum}`,
        'gender': 'U'
      };
    });

    const segments = utterances.map(utterance => {
      const speakerNum = parseInt(utterance.speaker.replace('Speaker ', '')) || 0;
      return {
        '@type': 'Segment',
        start: utterance.start_time,
        duration: utterance.end_time - utterance.start_time,
        bandwidth: 'S',
        speaker: {
          '@id': `S${speakerNum}`,
          'gender': 'U'
        }
      };
    });

    return {
      metadata: {
        version: '0.0.10'
      },
      '@type': 'AudioFile',
      speakers: speakerList,
      segments: segments
    };
  }

  /**
   * Build segmentation from Deepgram paragraphs structure
   * Creates segments at sentence boundaries within paragraphs
   */
  static buildSegmentationFromParagraphs(paragraphs: any[], words: any[]): any {
    if (paragraphs.length === 0) {
      return this.buildSegmentationFromSpeakerOnly(words);
    }

    // Get unique speakers
    const uniqueSpeakers = Array.from(new Set(words.map(w => w.speaker))).sort();
    const speakerList = uniqueSpeakers.map(speakerId => ({
      '@id': `S${speakerId}`,
      'gender': 'U'
    }));

    // Build segments from sentences within paragraphs
    const segments: any[] = [];
    
    for (const paragraph of paragraphs) {
      if (!paragraph.sentences || paragraph.sentences.length === 0) {
        continue;
      }
      
      for (const sentence of paragraph.sentences) {
        // Get the speaker for this sentence by finding which words fall within the sentence time range
        const wordsInSentence = words.filter(w => w.start >= sentence.start && w.end <= sentence.end);
        
        // Use the speaker of the first word, or 0 if no words match
        const speakerId = wordsInSentence.length > 0 ? wordsInSentence[0].speaker : 0;
        
        segments.push({
          '@type': 'Segment',
          start: sentence.start,
          duration: sentence.end - sentence.start,
          bandwidth: 'S',
          speaker: {
            '@id': `S${speakerId}`,
            'gender': 'U'
          }
        });
      }
    }

    return {
      metadata: {
        version: '0.0.10'
      },
      '@type': 'AudioFile',
      speakers: speakerList,
      segments: segments
    };
  }

  /**
   * Build segmentation structure from word-level speaker information for bbckaldi adapter
   * Groups consecutive words from the same speaker into segments
   */
  static buildSegmentationFromSpeakerOnly(words: any[]): any {
    if (words.length === 0) {
      return null;
    }

    // Get unique speakers and create speaker list
    const uniqueSpeakers = Array.from(new Set(words.map(w => w.speaker))).sort();
    const speakerList = uniqueSpeakers.map(speakerId => ({
      '@id': `S${speakerId}`,
      'gender': 'U' // Unknown gender for Deepgram speakers
    }));

    // Build segments by grouping consecutive words from the same speaker
    const segments: any[] = [];
    let currentSpeaker = words[0].speaker;
    let segmentStart = words[0].start;
    let segmentEnd = words[0].end;

    for (let i = 1; i < words.length; i++) {
      const word = words[i];
      
      // If speaker changes, create a segment and start a new one
      if (word.speaker !== currentSpeaker) {
        // Complete the previous segment
        segments.push({
          '@type': 'Segment',
          start: segmentStart,
          duration: segmentEnd - segmentStart,
          bandwidth: 'S',
          speaker: {
            '@id': `S${currentSpeaker}`,
            'gender': 'U'
          }
        });
        
        // Start new segment
        currentSpeaker = word.speaker;
        segmentStart = word.start;
        segmentEnd = word.end;
      } else {
        // Same speaker, extend segment
        segmentEnd = word.end;
      }
    }

    // Add the last segment
    segments.push({
      '@type': 'Segment',
      start: segmentStart,
      duration: segmentEnd - segmentStart,
      bandwidth: 'S',
      speaker: {
        '@id': `S${currentSpeaker}`,
        'gender': 'U'
      }
    });

    return {
      metadata: {
        version: '0.0.10'
      },
      '@type': 'AudioFile',
      speakers: speakerList,
      segments: segments
    };
  }

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