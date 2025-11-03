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
  CorrectedDeepgramWord,
  DeepgramRawResponse,
} from '../types/deepgram';
import { 
  ReactTranscriptEditorData
} from '../types/transcriptEditor';

export class DeepgramTransformer {
  /**
   * Detects if response is in raw Deepgram format and converts to RichWordsTranscript
   * Otherwise validates that response is in RichWordsTranscript format
   */
  static normalizeToSimplifiedFormat(response: any): RichWordsTranscript {
    // Check if it's already RichWordsTranscript format
    if (response.words && Array.isArray(response.words)) {
      return response as RichWordsTranscript;
    }

    // Check if it's raw Deepgram format - either direct raw_response or nested in result
    let rawResponse: DeepgramRawResponse | null = null;
    
    if (response.raw_response && response.raw_response.results) {
      // Direct raw_response
      rawResponse = response.raw_response;
    } else if (response.result && response.result.raw_response && response.result.raw_response.results) {
      // Nested in result.raw_response (from transcription_orchestrator format)
      rawResponse = response.result.raw_response;
    } else if (response.results && response.results.channels) {
      // Top-level raw Deepgram response
      rawResponse = response as DeepgramRawResponse;
    }

    if (rawResponse) {
      console.log('🔄 DeepgramTransformer: Detected raw Deepgram format, converting to RichWordsTranscript');
      return this.convertDeepgramToRichWordsTranscript(rawResponse);
    }

    // If not in expected format, provide helpful error
    throw new Error(
      'Transcript is not in RichWordsTranscript or raw Deepgram format. ' +
      'Expected format: { words: [...] } or raw Deepgram response structure.'
    );
  }

  /**
   * Converts raw Deepgram response to RichWordsTranscript format
   * Ported from Python backend _convert_to_rich_words_transcript method
   */
  static convertDeepgramToRichWordsTranscript(rawResponse: DeepgramRawResponse): RichWordsTranscript {
    // Extract words from raw Deepgram response
    const results = rawResponse.results;
    const channels = results?.channels || [];

    if (!channels || channels.length === 0) {
      throw new Error('No channels found in Deepgram response');
    }

    const channel = channels[0];
    const alternatives = channel.alternatives || [];

    if (!alternatives || alternatives.length === 0) {
      throw new Error('No alternatives found in Deepgram response');
    }

    const alternative = alternatives[0];
    const words = alternative.words || [];

    if (!words || words.length === 0) {
      throw new Error('No words found in Deepgram response');
    }

    // Extract paragraphs to mark word boundaries
    const paragraphs = alternative.paragraphs?.paragraphs || [];

    // Initialize paragraph markers
    const enrichedWords: CorrectedDeepgramWord[] = words.map((word) => ({
      ...word,
      paragraph_start: false,
      paragraph_end: false,
    }));

    // Mark paragraph boundaries using exclusive matching
    // Strategy: Match by BOTH time AND text content to ensure accuracy
    // Paragraph boundaries are exclusive: paragraph N ends where paragraph N+1 starts
    if (paragraphs && paragraphs.length > 0) {
      for (let paraIdx = 0; paraIdx < paragraphs.length; paraIdx++) {
        const paragraph = paragraphs[paraIdx];
        const sentences = paragraph.sentences || [];

        if (!sentences || sentences.length === 0) {
          continue;
        }

        // Find paragraph start: first word of first sentence
        const firstSentence = sentences[0];
        const paraStartTime = firstSentence.start;
        const firstSentenceText = firstSentence.text?.trim() || '';

        // Extract first word from sentence text (case-insensitive, ignoring punctuation)
        let firstWordFromText: string | null = null;
        if (firstSentenceText) {
          const wordsInText = firstSentenceText.split(/\s+/);
          if (wordsInText.length > 0) {
            firstWordFromText = wordsInText[0].replace(/[.,!?;:"()\[\]{}]/g, '').toLowerCase();
          }
        }

        // Find the word that matches both time and text
        if (paraStartTime !== undefined && paraStartTime !== null) {
          let bestMatch: CorrectedDeepgramWord | null = null;
          let bestTimeDiff = Infinity;

          for (const word of enrichedWords) {
            const wordStart = word.start || 0;
            const timeDiff = Math.abs(wordStart - paraStartTime);

            // Must match time within tolerance
            if (timeDiff >= 0.1) {
              continue;
            }

            // Match by text: compare punctuated_word (case-insensitive, normalized)
            const wordPunct = (word.punctuated_word || word.word || '').trim().toLowerCase();
            const wordPunctClean = wordPunct.replace(/[.,!?;:"()\[\]{}]/g, '');

            if (firstWordFromText && wordPunctClean === firstWordFromText) {
              // Text matches - this is our word
              if (timeDiff < bestTimeDiff) {
                bestMatch = word;
                bestTimeDiff = timeDiff;
              }
            }
          }

          if (bestMatch) {
            bestMatch.paragraph_start = true;
            // Clear paragraph_end if this word starts a new paragraph
            bestMatch.paragraph_end = false;
          }
        }

        // Find paragraph end: last word of last sentence
        // For all except the last paragraph, the end is exclusive (ends at next paragraph's start)
        if (paraIdx === paragraphs.length - 1) {
          // Last paragraph: mark its actual end
          const lastSentence = sentences[sentences.length - 1];
          const paraEndTime = lastSentence.end;
          const lastSentenceText = lastSentence.text?.trim() || '';

          // Extract last word from sentence text
          let lastWordFromText: string | null = null;
          if (lastSentenceText) {
            const wordsInText = lastSentenceText.split(/\s+/);
            if (wordsInText.length > 0) {
              lastWordFromText = wordsInText[wordsInText.length - 1]
                .replace(/[.,!?;:"()\[\]{}]/g, '')
                .toLowerCase();
            }
          }

          if (paraEndTime !== undefined && paraEndTime !== null) {
            let bestMatch: CorrectedDeepgramWord | null = null;
            let bestTimeDiff = Infinity;

            for (const word of enrichedWords) {
              const wordEnd = word.end || 0;
              const timeDiff = Math.abs(wordEnd - paraEndTime);

              // Must match time within tolerance
              if (timeDiff >= 0.1) {
                continue;
              }

              // Must NOT be a paragraph_start (exclusive boundary)
              if (word.paragraph_start) {
                continue;
              }

              // Match by text: compare punctuated_word
              const wordPunct = (word.punctuated_word || word.word || '').trim().toLowerCase();
              const wordPunctClean = wordPunct.replace(/[.,!?;:"()\[\]{}]/g, '');

              if (lastWordFromText && wordPunctClean === lastWordFromText) {
                // Text matches
                if (timeDiff < bestTimeDiff) {
                  bestMatch = word;
                  bestTimeDiff = timeDiff;
                }
              }
            }

            if (bestMatch) {
              bestMatch.paragraph_end = true;
            }
          }
        }
      }
    }

    // Return RichWordsTranscript format
    return {
      words: enrichedWords,
      corrections: {
        version: 1,
        timestamp: new Date().toISOString(),
        speaker_names: {},
      },
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
      const transformedWord = {
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
      
      return transformedWord;
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
   * Converts ReactTranscriptEditorData directly to RichWordsTranscript format
   * No word diffing - simply converts the entire edited content to RichWordsTranscript
   */
  static convertReactTranscriptEditorToRichWordsTranscript(
    edited: ReactTranscriptEditorData,
    original: RichWordsTranscript | null = null
  ): RichWordsTranscript {

    // Convert all words from edited format to RichWordsTranscript format
    // Note: paragraph_start/paragraph_end may be present but not in ReactTranscriptEditorWord type
    const words: CorrectedDeepgramWord[] = edited.words.map((word, index) => {
      const wordAny = word as any; // Allow access to paragraph markers that may be present
      if (word.speaker === undefined || word.speaker === null) {
        const errorMsg = `Word at index ${index} (${word.word}) is missing speaker property. Word: ${JSON.stringify(word)}`;
        console.error('❌ [convertReactTranscriptEditorToRichWordsTranscript] Missing speaker:', errorMsg);
        throw new Error(errorMsg);
      }
      const speakerValue = word.speaker;
      return {
        word: word.word,
        start: word.start,
        end: word.end,
        confidence: word.confidence || 0.9,
        speaker: speakerValue,
        speaker_confidence: word.confidence || 0.9,
        punctuated_word: word.punct || word.word,
        paragraph_start: wordAny.paragraph_start || false,
        paragraph_end: wordAny.paragraph_end || false,
        // Preserve correction metadata if present
        corrected: word.corrected,
        original_word: word.original_word,
        original_punct: word.original_punct,
      };
    });

    // Extract speaker names - only save custom names (not "Speaker X" format)
    const speakerNames: { [speakerIndex: number]: string } = {};
    if (edited.speaker_names) {
      for (const [indexStr, name] of Object.entries(edited.speaker_names)) {
        const speakerIndex = parseInt(indexStr);
        // Only save if it's a custom name (not "Speaker X" format)
        if (name && !name.match(/^Speaker \d+$/)) {
          speakerNames[speakerIndex] = name;
        }
      }
    }


    // Determine version - increment from original if available, otherwise start at 1
    const version = original?.corrections?.version 
      ? original.corrections.version + 1 
      : 1;

    // Build RichWordsTranscript
    const result: RichWordsTranscript = {
      words,
      corrections: {
        version,
      timestamp: new Date().toISOString(),
        speaker_names: speakerNames,
      },
    };

    return result;
  }

  /**
   * Legacy method for backward compatibility
   * Now just calls convertReactTranscriptEditorToRichWordsTranscript
   */
  static mergeCorrectionsIntoDeepgramResponse(
    original: RichWordsTranscript, 
    edited: ReactTranscriptEditorData
  ): RichWordsTranscript {
    return this.convertReactTranscriptEditorToRichWordsTranscript(edited, original);
  }

  /**
   * Reconstructs transcript text from corrected words
   * Handles punctuation and spacing properly
   * @deprecated Not currently used, kept for potential future use
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