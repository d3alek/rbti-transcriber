/**
 * DeepgramTransformer Service
 * 
 * Handles bidirectional transformation between CorrectedDeepgramResponse and ReactTranscriptEditorData formats.
 * Preserves word-level corrections and speaker name mappings throughout the transformation process.
 */

import { 
  CorrectedDeepgramResponse, 
  CorrectedDeepgramWord,
  // DeepgramWord // TODO: Use when needed
} from '../types/deepgram';
import { 
  ReactTranscriptEditorData
} from '../types/transcriptEditor';

export class DeepgramTransformer {
  /**
   * Transforms CorrectedDeepgramResponse to ReactTranscriptEditorData format
   * Preserves word-level corrections and speaker name mappings
   */
  static transformToReactTranscriptEditor(response: CorrectedDeepgramResponse): ReactTranscriptEditorData {
    console.log('🔄 DeepgramTransformer: Input response structure:', {
      hasRawResponse: !!response.raw_response,
      hasText: !!response.text,
      hasSpeakers: !!response.speakers,
      responseKeys: Object.keys(response)
    });

    const rawResponse = response.raw_response;
    
    if (!rawResponse || !rawResponse.results || !rawResponse.results.channels) {
      throw new Error('Invalid Deepgram response structure');
    }

    const channel = rawResponse.results.channels[0];
    const alternative = channel.alternatives[0];

    if (!alternative || !alternative.words) {
      throw new Error('No words found in Deepgram response');
    }

    // Transform words to the exact format expected by react-transcript-editor
    // This matches the format from deepgram-demo.html
    // Preserve correction metadata if present
    const words = alternative.words.map((word, index) => {
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
        original_punct: correctedWord.original_punct
      };
    });

    // Create speaker segments if available
    const speakerSegments = response.speakers || [];

    console.log('📊 Deepgram response structure check:', {
      hasResponseSpeakers: !!response.speakers,
      speakersCount: response.speakers?.length || 0,
      firstSpeaker: response.speakers?.[0] || null
    });

    // Build segmentation for bbckaldi adapter to handle speaker grouping
    // bbckaldi expects { words: [...], segmentation: { segments: [...] } } format
    // Use Deepgram utterance-level segments for best granularity
    const segmentation = this.buildSegmentationFromDeepgramData(alternative, words, response);
    console.log('🎯 Built segmentation:', {
      hasSegmentation: !!segmentation,
      segmentsCount: segmentation?.segments?.length || 0,
      speakersCount: segmentation?.speakers?.length || 0
    });

    const processedData = {
      words: words,
      speakers: speakerSegments,
      segmentation: segmentation,
      transcript: alternative.transcript || response.text,
      metadata: {
        duration: rawResponse.metadata.duration,
        confidence: response.confidence,
        service: 'deepgram'
      },
      speaker_names: response.corrections?.speaker_names
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
   * Build segmentation structure from Deepgram data for bbckaldi adapter
   * Uses Deepgram utterance-level speaker segments when available (better granularity),
   * falls back to paragraphs/sentences, then to simple speaker grouping
   */
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
   * Merges corrections from ReactTranscriptEditorData back into CorrectedDeepgramResponse
   * Embeds word-level corrections and speaker name mappings in the Deepgram structure
   */
  static mergeCorrectionsIntoDeepgramResponse(
    original: CorrectedDeepgramResponse, 
    edited: ReactTranscriptEditorData
  ): CorrectedDeepgramResponse {
    // Create a deep copy of the original response
    const corrected: CorrectedDeepgramResponse = JSON.parse(JSON.stringify(original));
    
    // Update the corrections metadata
    corrected.corrections = {
      version: (original.corrections?.version || 0) + 1,
      timestamp: new Date().toISOString(),
      speaker_names: edited.speaker_names
    };

    // Update words in the raw response with corrections
    const channel = corrected.raw_response.results.channels[0];
    const alternative = channel.alternatives[0];
    
    // Merge word-level corrections
    let correctionCount = 0;
    alternative.words = alternative.words.map((originalWord, index) => {
      const editedWord = edited.words[index];
      if (!editedWord) return originalWord;

      const correctedWord = originalWord as CorrectedDeepgramWord;
      
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
    
    console.log(`📊 Merge summary: ${correctionCount} words corrected out of ${alternative.words.length} total`);

    // Update the main transcript with corrected text
    const correctedTranscript = this.reconstructTranscriptFromWords(alternative.words as CorrectedDeepgramWord[]);
    alternative.transcript = correctedTranscript;
    corrected.text = correctedTranscript;

    // Update speaker segments with custom names if available
    if (edited.speaker_names) {
      corrected.speakers = corrected.speakers.map(speaker => {
        const speakerIndex = parseInt(speaker.speaker.replace('Speaker ', ''));
        const customName = edited.speaker_names?.[speakerIndex];
        
        return {
          ...speaker,
          speaker: customName || speaker.speaker
        };
      });
    }

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
    original: CorrectedDeepgramResponse,
    transformed: ReactTranscriptEditorData,
    roundTrip: CorrectedDeepgramResponse
  ): { isValid: boolean; errors: string[] } {
    const errors: string[] = [];
    
    // Validate transformed data structure
    if (!transformed.words || transformed.words.length === 0) {
      errors.push('Transformed data has no words');
    }

    // Check word count consistency
    const originalWords = original.raw_response.results.channels[0].alternatives[0].words;
    const roundTripWords = roundTrip.raw_response.results.channels[0].alternatives[0].words;
    
    if (originalWords.length !== roundTripWords.length) {
      errors.push(`Word count mismatch: original ${originalWords.length}, round-trip ${roundTripWords.length}`);
    }

    // Check word-level data preservation
    for (let i = 0; i < Math.min(originalWords.length, roundTripWords.length); i++) {
      const orig = originalWords[i];
      const roundTrip = roundTripWords[i];
      
      // Timing should be preserved
      if (Math.abs(orig.start - roundTrip.start) > 0.001) {
        errors.push(`Word ${i} start time mismatch: ${orig.start} vs ${roundTrip.start}`);
      }
      
      if (Math.abs(orig.end - roundTrip.end) > 0.001) {
        errors.push(`Word ${i} end time mismatch: ${orig.end} vs ${roundTrip.end}`);
      }
      
      // Speaker assignment should be preserved
      if (orig.speaker !== roundTrip.speaker) {
        errors.push(`Word ${i} speaker mismatch: ${orig.speaker} vs ${roundTrip.speaker}`);
      }
      
      // Confidence should be preserved
      if (Math.abs(orig.confidence - roundTrip.confidence) > 0.001) {
        errors.push(`Word ${i} confidence mismatch: ${orig.confidence} vs ${roundTrip.confidence}`);
      }
    }

    // Check metadata preservation
    if (Math.abs(original.audio_duration - roundTrip.audio_duration) > 0.001) {
      errors.push(`Audio duration mismatch: ${original.audio_duration} vs ${roundTrip.audio_duration}`);
    }

    if (Math.abs(original.confidence - roundTrip.confidence) > 0.001) {
      errors.push(`Overall confidence mismatch: ${original.confidence} vs ${roundTrip.confidence}`);
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