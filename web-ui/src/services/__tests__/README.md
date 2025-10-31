# DeepgramTransformer Round-Trip Transformation Tests

This directory contains comprehensive tests for the DeepgramTransformer service, focusing on validating the bidirectional transformation between `CorrectedDeepgramResponse` and `ReactTranscriptEditorData` formats.

## Test Overview

The round-trip transformation test ensures that:

1. **Data Integrity**: No data is lost during the transformation cycle
2. **Correction Preservation**: Manual corrections are properly embedded and preserved
3. **Speaker Mapping**: Speaker name mappings are correctly handled
4. **Validation Accuracy**: The validation functions correctly detect issues

## Test Structure

### Test Data

The test uses a realistic Deepgram response structure based on actual API responses:

```typescript
interface TestDeepgramResponse {
  // High-level processed data
  text: string;
  speakers: DeepgramSpeaker[];
  confidence: number;
  audio_duration: number;
  processing_time: number;
  
  // Raw Deepgram API response
  raw_response: {
    metadata: DeepgramMetadata;
    results: {
      channels: [{
        alternatives: [{
          transcript: string;
          words: DeepgramWord[];
          paragraphs: DeepgramParagraphs;
        }]
      }]
    }
  }
}
```

### Test Cases

#### 1. Basic Transformation Test
- **Purpose**: Validates that `transformToReactTranscriptEditor` correctly converts data structure
- **Checks**: 
  - Word count preservation
  - Timing data accuracy
  - Speaker assignment
  - Metadata integrity

#### 2. Round-Trip Integrity Test
- **Purpose**: Ensures no data loss during complete transformation cycle
- **Process**:
  1. Start with `CorrectedDeepgramResponse`
  2. Transform to `ReactTranscriptEditorData`
  3. Transform back to `CorrectedDeepgramResponse`
  4. Validate equivalence with original
- **Validation**: Uses `validateRoundTripTransformation` function

#### 3. Correction Preservation Test
- **Purpose**: Validates that manual corrections are properly handled
- **Process**:
  1. Create response with existing corrections
  2. Transform through both formats
  3. Verify corrections are preserved
- **Checks**:
  - `corrected` flags
  - `original_word` preservation
  - Speaker name mappings

#### 4. Speaker Name Mapping Test
- **Purpose**: Ensures speaker name customization works correctly
- **Process**:
  1. Add custom speaker names to `ReactTranscriptEditorData`
  2. Transform back to `CorrectedDeepgramResponse`
  3. Verify names are stored in corrections metadata
  4. Check speaker segments are updated

#### 5. Word Correction Test
- **Purpose**: Validates word-level editing functionality
- **Process**:
  1. Modify words in `ReactTranscriptEditorData`
  2. Transform back to `CorrectedDeepgramResponse`
  3. Verify corrections are embedded in raw response
  4. Check transcript is updated

#### 6. Validation Function Test
- **Purpose**: Ensures validation functions work correctly
- **Process**:
  1. Create valid round-trip transformation
  2. Verify validation passes
  3. Introduce data corruption
  4. Verify validation detects issues

## Running Tests

### Method 1: Node.js Test Runner
```bash
cd web-ui
node test-runner.js
```

### Method 2: TypeScript Compilation (when available)
```bash
cd web-ui
npx tsc src/services/__tests__/DeepgramTransformer.test.ts --outDir dist
node dist/DeepgramTransformer.test.js
```

### Method 3: Direct TypeScript Execution (with ts-node)
```bash
cd web-ui
npx ts-node src/services/__tests__/DeepgramTransformer.test.ts
```

## Expected Results

All tests should pass with output similar to:

```
=== DeepgramTransformer Round-Trip Transformation Tests ===

✅ should transform CorrectedDeepgramResponse to ReactTranscriptEditorData
✅ should perform round-trip transformation without data loss
✅ should preserve corrections during round-trip transformation
✅ should handle speaker name mappings correctly
✅ should handle word corrections correctly
✅ should validate data integrity correctly
✅ should detect data integrity issues

=== Test Results ===
Passed: 7
Failed: 0
Total: 7
```

## Test Data Validation

The test uses realistic data that matches the actual structure from the RBTI seminar transcription system:

- **Word-level timing**: Precise start/end times for audio synchronization
- **Speaker identification**: Multiple speakers with confidence scores
- **Confidence scoring**: Word and utterance-level confidence values
- **Punctuation handling**: Separate word and punctuated_word fields
- **Metadata preservation**: Request IDs, model information, processing times

## Integration with Main System

These tests validate the core transformation logic that enables:

1. **Transcript Editor Integration**: Converting Deepgram responses for react-transcript-editor
2. **Manual Correction Storage**: Embedding user edits back into Deepgram structure
3. **Speaker Customization**: Mapping generic "Speaker 0" to custom names
4. **Data Persistence**: Ensuring corrections survive save/load cycles

## Troubleshooting

### Common Issues

1. **Timing Precision**: Floating-point comparison issues
   - Solution: Use `toBeCloseTo` with appropriate precision

2. **Deep Object Comparison**: JSON.stringify limitations
   - Solution: Implement custom deep equality checks

3. **Async Test Handling**: Promise-based test execution
   - Solution: Use proper async/await patterns

### Debugging Tips

1. **Enable Verbose Logging**: Add console.log statements to track data flow
2. **Inspect Intermediate Results**: Log transformed data at each step
3. **Validate Test Data**: Ensure test data matches real Deepgram responses
4. **Check Type Definitions**: Verify TypeScript interfaces match actual data

## Future Enhancements

1. **Performance Testing**: Add benchmarks for large transcripts
2. **Edge Case Coverage**: Test with malformed or incomplete data
3. **Concurrent Modification**: Test behavior with simultaneous edits
4. **Memory Usage**: Monitor memory consumption with large datasets
5. **Real Data Testing**: Use actual RBTI seminar transcription files