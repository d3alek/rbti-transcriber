/**
 * DeepgramTransformer Round-Trip Conversion Test
 * 
 * Tests the complete conversion flow:
 * 1. Raw Deepgram response -> RichWordsTranscript
 * 2. RichWordsTranscript -> ReactTranscriptEditorData (UI format)
 * 3. ReactTranscriptEditorData -> RichWordsTranscript (back)
 * 
 * Verifies that speakers and speaker names are preserved throughout.
 */

import { DeepgramTransformer } from '../DeepgramTransformer';
import { DeepgramRawResponse, RichWordsTranscript } from '../../types/deepgram';
import { ReactTranscriptEditorData } from '../../types/transcriptEditor';

// Create a test Deepgram raw response with multiple speakers
const createTestDeepgramRawResponse = (): DeepgramRawResponse => ({
  metadata: {
    request_id: "test-request-id",
    sha256: "test-sha256",
    created: "2025-11-03T12:00:00.000Z",
    duration: 10.0,
    channels: 1,
    models: ["general-nova-3"],
    model_info: {
      "general-nova-3": {
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
            transcript: "Hello everyone. Welcome to the seminar.",
            words: [
              {
                word: "Hello",
                start: 0.5,
                end: 1.0,
                confidence: 0.99,
                speaker: 0,
                speaker_confidence: 0.95,
                punctuated_word: "Hello"
              },
              {
                word: "everyone",
                start: 1.0,
                end: 1.5,
                confidence: 0.98,
                speaker: 0,
                speaker_confidence: 0.95,
                punctuated_word: "everyone."
              },
              {
                word: "Welcome",
                start: 2.0,
                end: 2.5,
                confidence: 0.97,
                speaker: 1,
                speaker_confidence: 0.92,
                punctuated_word: "Welcome"
              },
              {
                word: "to",
                start: 2.5,
                end: 2.7,
                confidence: 0.99,
                speaker: 1,
                speaker_confidence: 0.92,
                punctuated_word: "to"
              },
              {
                word: "the",
                start: 2.7,
                end: 2.9,
                confidence: 0.98,
                speaker: 1,
                speaker_confidence: 0.92,
                punctuated_word: "the"
              },
              {
                word: "seminar",
                start: 2.9,
                end: 3.3,
                confidence: 0.96,
                speaker: 1,
                speaker_confidence: 0.92,
                punctuated_word: "seminar."
              }
            ],
            paragraphs: {
              transcript: "Hello everyone. Welcome to the seminar.",
              paragraphs: [
                {
                  sentences: [
                    {
                      text: "Hello everyone.",
                      start: 0.5,
                      end: 1.5,
                      words: [],
                      speaker: 0,
                      id: "sentence-1"
                    }
                  ]
                },
                {
                  sentences: [
                    {
                      text: "Welcome to the seminar.",
                      start: 2.0,
                      end: 3.3,
                      words: [],
                      speaker: 1,
                      id: "sentence-2"
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
});

// Test runner
class RoundTripTestRunner {
  private tests: Array<{ name: string; fn: () => void | Promise<void> }> = [];
  private passed = 0;
  private failed = 0;

  test(name: string, fn: () => void | Promise<void>): void {
    this.tests.push({ name, fn });
  }

  expect(actual: any) {
    return {
      toBe: (expected: any) => {
        if (actual !== expected) {
          throw new Error(`Expected ${JSON.stringify(actual)} to be ${JSON.stringify(expected)}`);
        }
      },
      toEqual: (expected: any) => {
        if (JSON.stringify(actual) !== JSON.stringify(expected)) {
          throw new Error(`Expected ${JSON.stringify(actual)} to equal ${JSON.stringify(expected)}`);
        }
      },
      toBeCloseTo: (expected: number, precision: number = 2) => {
        const threshold = Math.pow(10, -precision);
        if (Math.abs(actual - expected) >= threshold) {
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
          throw new Error(`Expected length ${length}, got ${actualLength}`);
        }
      },
      toContain: (item: any) => {
        if (!Array.isArray(actual) || !actual.includes(item)) {
          throw new Error(`Expected array to contain ${item}`);
        }
      }
    };
  }

  async run(): Promise<void> {
    console.log('\n=== DeepgramTransformer Round-Trip Conversion Tests ===\n');

    for (const { name, fn } of this.tests) {
      try {
        const result = fn();
        if (result instanceof Promise) {
          await result;
        }
        console.log(`✅ ${name}`);
        this.passed++;
      } catch (error: any) {
        console.log(`❌ ${name}`);
        console.log(`   Error: ${error.message}`);
        if (error.stack) {
          console.log(`   Stack: ${error.stack.split('\n')[1]?.trim()}`);
        }
        this.failed++;
      }
    }

    console.log(`\n=== Test Results ===`);
    console.log(`Passed: ${this.passed}`);
    console.log(`Failed: ${this.failed}`);
    console.log(`Total: ${this.passed + this.failed}\n`);

    if (this.failed > 0) {
      process.exit(1);
    }
  }
}

const runner = new RoundTripTestRunner();

// Test 1: Deepgram Raw -> RichWordsTranscript
runner.test('should convert raw Deepgram response to RichWordsTranscript', () => {
  const rawResponse = createTestDeepgramRawResponse();
  const richTranscript = DeepgramTransformer.convertDeepgramToRichWordsTranscript(rawResponse);

  runner.expect(richTranscript.words).toHaveLength(6);
  runner.expect(richTranscript.words[0].speaker).toBe(0);
  runner.expect(richTranscript.words[2].speaker).toBe(1);
  runner.expect(richTranscript.words[0].paragraph_start).toBe(true);
  runner.expect(richTranscript.words[2].paragraph_start).toBe(true);
  // Paragraph end is only marked on the last paragraph's last word
  runner.expect(richTranscript.words[5].paragraph_end).toBe(true);
  runner.expect(richTranscript.corrections).toBeTruthy();
});

// Test 2: RichWordsTranscript -> UI format -> RichWordsTranscript (round-trip)
runner.test('should preserve speakers in RichWordsTranscript -> UI -> RichWordsTranscript round-trip', () => {
  const rawResponse = createTestDeepgramRawResponse();
  
  // Step 1: Convert to RichWordsTranscript
  const richTranscript1 = DeepgramTransformer.convertDeepgramToRichWordsTranscript(rawResponse);
  
  // Step 2: Convert to UI format
  const uiData = DeepgramTransformer.transformToReactTranscriptEditor(richTranscript1);
  
  // Step 3: Convert back to RichWordsTranscript
  const richTranscript2 = DeepgramTransformer.convertReactTranscriptEditorToRichWordsTranscript(
    uiData,
    richTranscript1
  );

  // Verify speakers are preserved
  runner.expect(richTranscript2.words).toHaveLength(richTranscript1.words.length);
  
  for (let i = 0; i < richTranscript1.words.length; i++) {
    runner.expect(richTranscript2.words[i].speaker).toBe(richTranscript1.words[i].speaker);
    runner.expect(richTranscript2.words[i].word).toBe(richTranscript1.words[i].word);
    runner.expect(richTranscript2.words[i].start).toBeCloseTo(richTranscript1.words[i].start);
    runner.expect(richTranscript2.words[i].end).toBeCloseTo(richTranscript1.words[i].end);
  }
  
  console.log('   ✓ All speakers preserved');
  console.log(`   ✓ Speaker 0 words: ${richTranscript2.words.filter(w => w.speaker === 0).length}`);
  console.log(`   ✓ Speaker 1 words: ${richTranscript2.words.filter(w => w.speaker === 1).length}`);
});

// Test 3: RichWordsTranscript -> UI format -> RichWordsTranscript with speaker names
runner.test('should preserve speaker names in round-trip conversion', () => {
  const rawResponse = createTestDeepgramRawResponse();
  
  // Step 1: Convert to RichWordsTranscript
  const richTranscript1 = DeepgramTransformer.convertDeepgramToRichWordsTranscript(rawResponse);
  
  // Add speaker names
  richTranscript1.corrections = {
    version: 1,
    timestamp: new Date().toISOString(),
    speaker_names: {
      0: 'Dr. Smith',
      1: 'Student A'
    }
  };
  
  // Step 2: Convert to UI format
  const uiData = DeepgramTransformer.transformToReactTranscriptEditor(richTranscript1);
  
  // Verify speaker names are in UI format
  runner.expect(uiData.speaker_names).toBeTruthy();
  runner.expect(uiData.speaker_names?.[0]).toBe('Dr. Smith');
  runner.expect(uiData.speaker_names?.[1]).toBe('Student A');
  
  // Step 3: Convert back to RichWordsTranscript
  const richTranscript2 = DeepgramTransformer.convertReactTranscriptEditorToRichWordsTranscript(
    uiData,
    richTranscript1
  );

  // Verify speaker names are preserved
  runner.expect(richTranscript2.corrections?.speaker_names).toBeTruthy();
  runner.expect(richTranscript2.corrections?.speaker_names?.[0]).toBe('Dr. Smith');
  runner.expect(richTranscript2.corrections?.speaker_names?.[1]).toBe('Student A');
  
  console.log('   ✓ Speaker names preserved in corrections');
});

// Test 4: Full round-trip: Raw -> RichWordsTranscript -> UI -> RichWordsTranscript
runner.test('should complete full round-trip: Raw Deepgram -> RichWordsTranscript -> UI -> RichWordsTranscript', () => {
  const rawResponse = createTestDeepgramRawResponse();
  
  // Step 1: Raw Deepgram -> RichWordsTranscript
  const richTranscript1 = DeepgramTransformer.convertDeepgramToRichWordsTranscript(rawResponse);
  runner.expect(richTranscript1.words).toHaveLength(6);
  runner.expect(richTranscript1.words[0].speaker).toBe(0);
  runner.expect(richTranscript1.words[2].speaker).toBe(1);
  
  // Step 2: RichWordsTranscript -> UI format
  const uiData = DeepgramTransformer.transformToReactTranscriptEditor(richTranscript1);
  runner.expect(uiData.words).toHaveLength(6);
  runner.expect(uiData.words[0].speaker).toBe(0);
  runner.expect(uiData.words[2].speaker).toBe(1);
  
  // Step 3: UI format -> RichWordsTranscript
  const richTranscript2 = DeepgramTransformer.convertReactTranscriptEditorToRichWordsTranscript(
    uiData,
    richTranscript1
  );
  
  // Verify complete round-trip
  runner.expect(richTranscript2.words).toHaveLength(6);
  runner.expect(richTranscript2.words[0].speaker).toBe(0);
  runner.expect(richTranscript2.words[1].speaker).toBe(0);
  runner.expect(richTranscript2.words[2].speaker).toBe(1);
  runner.expect(richTranscript2.words[3].speaker).toBe(1);
  runner.expect(richTranscript2.words[4].speaker).toBe(1);
  runner.expect(richTranscript2.words[5].speaker).toBe(1);
  
  // Verify paragraph markers
  runner.expect(richTranscript2.words[0].paragraph_start).toBe(true);
  runner.expect(richTranscript2.words[2].paragraph_start).toBe(true);
  // Paragraph end is only marked on the last paragraph's last word
  runner.expect(richTranscript2.words[5].paragraph_end).toBe(true);
  
  console.log('   ✓ Full round-trip successful');
  console.log(`   ✓ All ${richTranscript2.words.length} words preserved`);
  console.log(`   ✓ Speaker 0: ${richTranscript2.words.filter(w => w.speaker === 0).length} words`);
  console.log(`   ✓ Speaker 1: ${richTranscript2.words.filter(w => w.speaker === 1).length} words`);
});

// Test 5: UI format with speaker names -> RichWordsTranscript
runner.test('should include speaker names when converting UI format to RichWordsTranscript', () => {
  const uiData: ReactTranscriptEditorData = {
    words: [
      {
        start: 0.5,
        end: 1.0,
        word: 'Hello',
        confidence: 0.99,
        punct: 'Hello',
        index: 0,
        speaker: 0
      },
      {
        start: 1.0,
        end: 1.5,
        word: 'everyone',
        confidence: 0.98,
        punct: 'everyone.',
        index: 1,
        speaker: 0
      },
      {
        start: 2.0,
        end: 2.5,
        word: 'Welcome',
        confidence: 0.97,
        punct: 'Welcome',
        index: 2,
        speaker: 1
      }
    ],
    speakers: [],
    transcript: 'Hello everyone. Welcome',
    metadata: {
      duration: 3.0,
      confidence: 0.98,
      service: 'deepgram'
    },
    speaker_names: {
      0: 'Dr. Reams',
      1: 'Student'
    }
  };
  
  const richTranscript = DeepgramTransformer.convertReactTranscriptEditorToRichWordsTranscript(uiData);
  
  // Verify speakers
  runner.expect(richTranscript.words[0].speaker).toBe(0);
  runner.expect(richTranscript.words[1].speaker).toBe(0);
  runner.expect(richTranscript.words[2].speaker).toBe(1);
  
  // Verify speaker names
  runner.expect(richTranscript.corrections?.speaker_names).toBeTruthy();
  runner.expect(richTranscript.corrections?.speaker_names?.[0]).toBe('Dr. Reams');
  runner.expect(richTranscript.corrections?.speaker_names?.[1]).toBe('Student');
  
  console.log('   ✓ Speaker names included in corrections');
});

// Run all tests
runner.run().catch(error => {
  console.error('Test runner error:', error);
  process.exit(1);
});

