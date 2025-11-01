/**
 * DeepgramTransformer Round-Trip Transformation Test
 * 
 * Tests the bidirectional transformation between CorrectedDeepgramResponse and ReactTranscriptEditorData
 * to ensure no data loss occurs during the transformation cycle.
 */

import { DeepgramTransformer } from '../DeepgramTransformer';
import { CorrectedDeepgramResponse } from '../../types/deepgram';
// import { ReactTranscriptEditorData } from '../../types/transcriptEditor'; // TODO: Use when needed

// Test data based on actual Deepgram response structure
const createTestDeepgramResponse = (): CorrectedDeepgramResponse => ({
  text: "I'd like to welcome all of you to this seminar on RBTI.",
  speakers: [
    {
      speaker: "Speaker 0",
      start_time: 0.48,
      end_time: 10.5,
      text: "I'd like to welcome all of you to this seminar on RBTI.",
      confidence: 0.98527277
    }
  ],
  confidence: 0.9943198,
  audio_duration: 3670.043,
  processing_time: 21.011720895767212,
  raw_response: {
    metadata: {
      request_id: "test-request-id",
      sha256: "test-sha256",
      created: "2025-10-29T03:39:03.035Z",
      duration: 3671.748,
      channels: 1,
      models: ["test-model-id"],
      model_info: {
        "test-model-id": {
          name: "general-nova-3",
          version: "2025-07-31.0",
          arch: "nova-3"
        }
      }
    },
    results: {
      channels: [
        {
          alternatives: [
            {
              transcript: "I'd like to welcome all of you to this seminar on RBTI.",
              words: [
                {
                  word: "I'd",
                  start: 0.48,
                  end: 0.8,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "I'd"
                },
                {
                  word: "like",
                  start: 0.8,
                  end: 1.2,
                  confidence: 0.98,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "like"
                },
                {
                  word: "to",
                  start: 1.2,
                  end: 1.4,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "to"
                },
                {
                  word: "welcome",
                  start: 1.4,
                  end: 1.8,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "welcome"
                },
                {
                  word: "all",
                  start: 1.8,
                  end: 2.0,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "all"
                },
                {
                  word: "of",
                  start: 2.0,
                  end: 2.2,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "of"
                },
                {
                  word: "you",
                  start: 2.2,
                  end: 2.4,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "you"
                },
                {
                  word: "to",
                  start: 2.4,
                  end: 2.6,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "to"
                },
                {
                  word: "this",
                  start: 2.6,
                  end: 2.8,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "this"
                },
                {
                  word: "seminar",
                  start: 2.8,
                  end: 3.2,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "seminar"
                },
                {
                  word: "on",
                  start: 3.2,
                  end: 3.4,
                  confidence: 0.99,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "on"
                },
                {
                  word: "RBTI",
                  start: 3.4,
                  end: 3.8,
                  confidence: 0.95,
                  speaker: 0,
                  speaker_confidence: 0.89,
                  punctuated_word: "RBTI."
                }
              ],
              paragraphs: {
                transcript: "I'd like to welcome all of you to this seminar on RBTI.",
                paragraphs: [
                  {
                    sentences: [
                      {
                        text: "I'd like to welcome all of you to this seminar on RBTI.",
                        start: 0.48,
                        end: 3.8,
                        words: [],
                        speaker: 0,
                        id: "sentence-1"
                      }
                    ]
                  }
                ]
              }
            }
          ]
        }
      ]
    }
  }
});

// Test runner interface
interface TestResult {
  name: string;
  passed: boolean;
  error?: string;
  details?: any;
}

class TestRunner {
  private results: TestResult[] = [];

  test(name: string, testFn: () => void | Promise<void>): void {
    try {
      const result = testFn();
      if (result instanceof Promise) {
        result
          .then(() => {
            this.results.push({ name, passed: true });
          })
          .catch((error) => {
            this.results.push({ 
              name, 
              passed: false, 
              error: error.message || String(error) 
            });
          });
      } else {
        this.results.push({ name, passed: true });
      }
    } catch (error: any) {
      this.results.push({ 
        name, 
        passed: false, 
        error: error.message || String(error) 
      });
    }
  }

  expect(actual: any): {
    toBe: (expected: any) => void;
    toEqual: (expected: any) => void;
    toBeCloseTo: (expected: number, precision?: number) => void;
    toBeTruthy: () => void;
    toBeFalsy: () => void;
    toHaveLength: (length: number) => void;
  } {
    return {
      toBe: (expected: any) => {
        if (actual !== expected) {
          throw new Error(`Expected ${actual} to be ${expected}`);
        }
      },
      toEqual: (expected: any) => {
        if (JSON.stringify(actual) !== JSON.stringify(expected)) {
          throw new Error(`Expected ${JSON.stringify(actual)} to equal ${JSON.stringify(expected)}`);
        }
      },
      toBeCloseTo: (expected: number, precision: number = 2) => {
        const diff = Math.abs(actual - expected);
        const threshold = Math.pow(10, -precision);
        if (diff >= threshold) {
          throw new Error(`Expected ${actual} to be close to ${expected} (within ${threshold})`);
        }
      },
      toBeTruthy: () => {
        if (!actual) {
          throw new Error(`Expected ${actual} to be truthy`);
        }
      },
      toBeFalsy: () => {
        if (actual) {
          throw new Error(`Expected ${actual} to be falsy`);
        }
      },
      toHaveLength: (length: number) => {
        if (!actual || actual.length !== length) {
          const actualLength = actual ? actual.length : 'undefined';
          throw new Error(`Expected ${actual} to have length ${length}, but got ${actualLength}`);
        }
      }
    };
  }

  runTests(): void {
    console.log('\n=== DeepgramTransformer Round-Trip Transformation Tests ===\n');
    
    // Wait a bit for async tests to complete
    setTimeout(() => {
      let passed = 0;
      let failed = 0;
      
      this.results.forEach(result => {
        if (result.passed) {
          console.log(`✅ ${result.name}`);
          passed++;
        } else {
          console.log(`❌ ${result.name}`);
          console.log(`   Error: ${result.error}`);
          if (result.details) {
            console.log(`   Details:`, result.details);
          }
          failed++;
        }
      });
      
      console.log(`\n=== Test Results ===`);
      console.log(`Passed: ${passed}`);
      console.log(`Failed: ${failed}`);
      console.log(`Total: ${passed + failed}`);
      
      if (failed > 0) {
        process.exit(1);
      }
    }, 100);
  }
}

// Test suite
const runner = new TestRunner();

runner.test('should transform CorrectedDeepgramResponse to ReactTranscriptEditorData', () => {
  const original = createTestDeepgramResponse();
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(original);
  
  // Check basic structure
  runner.expect(transformed.words).toHaveLength(12);
  runner.expect(transformed.speakers).toHaveLength(1);
  runner.expect(transformed.transcript).toBe("I'd like to welcome all of you to this seminar on RBTI.");
  
  // Check word-level data
  const firstWord = transformed.words[0];
  runner.expect(firstWord.word).toBe("I'd");
  runner.expect(firstWord.start).toBeCloseTo(0.48);
  runner.expect(firstWord.end).toBeCloseTo(0.8);
  runner.expect(firstWord.confidence).toBeCloseTo(0.99);
  runner.expect(firstWord.speaker).toBe(0);
  runner.expect(firstWord.index).toBe(0);
  
  // Check metadata
  runner.expect(transformed.metadata.duration).toBeCloseTo(3671.748); // Uses rawResponse.metadata.duration
  runner.expect(transformed.metadata.confidence).toBeCloseTo(0.9943198);
  runner.expect(transformed.metadata.service).toBe('deepgram');
});

runner.test('should perform round-trip transformation without data loss', () => {
  const original = createTestDeepgramResponse();
  
  // Step 1: Transform to ReactTranscriptEditorData
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(original);
  
  // Step 2: Transform back to CorrectedDeepgramResponse
  const roundTrip = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(original, transformed);
  
  // Step 3: Validate round-trip integrity
  const validation = DeepgramTransformer.validateRoundTripTransformation(original, transformed, roundTrip);
  
  runner.expect(validation.isValid).toBeTruthy();
  if (!validation.isValid) {
    console.log('Validation errors:', validation.errors);
  }
  
  // Check specific data preservation
  const originalWords = original.raw_response.results.channels[0].alternatives[0].words;
  const roundTripWords = roundTrip.raw_response.results.channels[0].alternatives[0].words;
  
  runner.expect(roundTripWords).toHaveLength(originalWords.length);
  
  // Check each word
  for (let i = 0; i < originalWords.length; i++) {
    const orig = originalWords[i];
    const rt = roundTripWords[i];
    
    runner.expect(rt.start).toBeCloseTo(orig.start, 3);
    runner.expect(rt.end).toBeCloseTo(orig.end, 3);
    runner.expect(rt.confidence).toBeCloseTo(orig.confidence, 3);
    runner.expect(rt.speaker).toBe(orig.speaker);
    runner.expect(rt.word).toBe(orig.word);
    runner.expect(rt.punctuated_word).toBe(orig.punctuated_word);
  }
});

runner.test('should preserve corrections during round-trip transformation', () => {
  const original = createTestDeepgramResponse();
  
  // Add some corrections to the original
  const correctedOriginal: CorrectedDeepgramResponse = {
    ...original,
    corrections: {
      version: 1,
      timestamp: '2025-10-29T12:00:00.000Z',
      speaker_names: {
        0: 'Dr. Smith'
      }
    }
  };
  
  // Mark some words as corrected
  const words = correctedOriginal.raw_response.results.channels[0].alternatives[0].words as any[];
  words[0].corrected = true;
  words[0].original_word = "I";
  words[0].original_punct = "I";
  words[0].word = "I'd";
  words[0].punctuated_word = "I'd";
  
  // Transform to ReactTranscriptEditorData
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(correctedOriginal);
  
  // Check that corrections are preserved
  runner.expect(transformed.words[0].corrected).toBeTruthy();
  runner.expect(transformed.words[0].original_word).toBe("I");
  runner.expect(transformed.speaker_names?.[0]).toBe('Dr. Smith');
  
  // Transform back
  const roundTrip = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(correctedOriginal, transformed);
  
  // Check that corrections are still there
  const rtWords = roundTrip.raw_response.results.channels[0].alternatives[0].words as any[];
  runner.expect(rtWords[0].corrected).toBeTruthy();
  runner.expect(rtWords[0].original_word).toBe("I");
  runner.expect(roundTrip.corrections?.speaker_names?.[0]).toBe('Dr. Smith');
});

runner.test('should handle speaker name mappings correctly', () => {
  const original = createTestDeepgramResponse();
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(original);
  
  // Add speaker name mappings
  transformed.speaker_names = {
    0: 'Professor Johnson'
  };
  
  // Transform back
  const roundTrip = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(original, transformed);
  
  // Check that speaker names are stored in corrections metadata
  runner.expect(roundTrip.corrections?.speaker_names?.[0]).toBe('Professor Johnson');
  
  // Check that speaker segments are updated
  runner.expect(roundTrip.speakers[0].speaker).toBe('Professor Johnson');
});

runner.test('should handle word corrections correctly', () => {
  const original = createTestDeepgramResponse();
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(original);
  
  // Make some corrections
  transformed.words[3].word = 'greet'; // Change 'welcome' to 'greet'
  transformed.words[3].punct = 'greet';
  
  // Transform back
  const roundTrip = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(original, transformed);
  
  // Check that corrections are embedded
  const rtWords = roundTrip.raw_response.results.channels[0].alternatives[0].words as any[];
  runner.expect(rtWords[3].corrected).toBeTruthy();
  runner.expect(rtWords[3].word).toBe('greet');
  runner.expect(rtWords[3].original_word).toBe('welcome');
  
  // Check that transcript is updated
  runner.expect(roundTrip.text.includes('greet')).toBeTruthy();
});

runner.test('should validate data integrity correctly', () => {
  const original = createTestDeepgramResponse();
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(original);
  const roundTrip = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(original, transformed);
  
  const validation = DeepgramTransformer.validateRoundTripTransformation(original, transformed, roundTrip);
  
  runner.expect(validation.isValid).toBeTruthy();
  runner.expect(validation.errors).toHaveLength(0);
});

runner.test('should detect data integrity issues', () => {
  const original = createTestDeepgramResponse();
  const transformed = DeepgramTransformer.transformToReactTranscriptEditor(original);
  const roundTrip = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(original, transformed);
  
  // Introduce an integrity issue
  roundTrip.audio_duration = 9999;
  
  const validation = DeepgramTransformer.validateRoundTripTransformation(original, transformed, roundTrip);
  
  runner.expect(validation.isValid).toBeFalsy();
  runner.expect(validation.errors.length).toBe(1);
  runner.expect(validation.errors[0].includes('Audio duration mismatch')).toBeTruthy();
});

runner.test('should handle DraftJS-based editing workflow (react-transcript-editor)', () => {
  // This test simulates the actual workflow in TranscriptEditor component
  const original = createTestDeepgramResponse();
  
  // Step 1: Load transcript - transform Deepgram to ReactTranscriptEditorData
  const initialTransform = DeepgramTransformer.transformToReactTranscriptEditor(original);
  runner.expect(initialTransform.words).toHaveLength(12);
  
  // Step 2: Simulate editing in react-transcript-editor
  // react-transcript-editor converts ReactTranscriptEditorData to DraftJS blocks internally
  // When autoSaveContentType="draftjs", it returns DraftJS blocks via handleAutoSaveChanges
  // We need to simulate the DraftJS blocks structure that react-transcript-editor returns
  
  // Create DraftJS blocks structure as react-transcript-editor would return
  const draftJsBlocks = {
    data: {
      blocks: [
        {
          key: 'block-0',
          text: "I'd like to welcome all of you to this seminar on RBTI.",
          type: 'paragraph',
          data: {
            speaker: 'Speaker 0',
            words: initialTransform.words.map((word, index) => ({
              ...word,
              // Simulate an edit: user changed 'welcome' to 'greet'
              ...(index === 3 && {
                word: 'greet',
                punct: 'greet'
              })
            }))
          },
          entityRanges: []
        }
      ],
      entityMap: {}
    },
    ext: 'json'
  };
  
  // Step 3: Extract words from DraftJS blocks (as TranscriptEditor does)
  const blocks = draftJsBlocks.data.blocks;
  const extractedWords: any[] = [];
  blocks.forEach((block: any) => {
    if (block.data && block.data.words && Array.isArray(block.data.words)) {
      extractedWords.push(...block.data.words);
    }
  });
  
  runner.expect(extractedWords).toHaveLength(12);
  runner.expect(extractedWords[3].word).toBe('greet'); // Should reflect the edit
  
  // Step 4: Create updated ReactTranscriptEditorData with edited words
  const editedTranscriptData = {
    ...initialTransform,
    words: extractedWords
  };
  
  // Step 5: Save changes - merge back to Deepgram format
  const correctedResponse = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(
    original,
    editedTranscriptData
  );
  
  // Step 6: Verify corrections are embedded
  const rtWords = correctedResponse.raw_response.results.channels[0].alternatives[0].words as any[];
  runner.expect(rtWords[3].corrected).toBeTruthy();
  runner.expect(rtWords[3].word).toBe('greet');
  runner.expect(rtWords[3].original_word).toBe('welcome');
  
  // Step 7: Reload transcript - transform back to ReactTranscriptEditorData
  const reloadedTransform = DeepgramTransformer.transformToReactTranscriptEditor(correctedResponse);
  
  // Step 8: Verify edits are preserved
  runner.expect(reloadedTransform.words).toHaveLength(12);
  runner.expect(reloadedTransform.words[3].word).toBe('greet');
  runner.expect(reloadedTransform.words[3].corrected).toBeTruthy();
  runner.expect(reloadedTransform.words[3].original_word).toBe('welcome');
  
  console.log('✅ DraftJS workflow test completed successfully');
});

// Run all tests
runner.runTests();

export { TestRunner, createTestDeepgramResponse };