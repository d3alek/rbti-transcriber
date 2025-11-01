# Data Format Reference Guide

This document explains the different data formats used throughout the application and how they transform between each other.

## 1. Raw Deepgram Response

**Source**: Deepgram API  
**Location**: `DeepgramResponse.raw_response`

```typescript
{
  metadata: {
    transaction_key: "...",
    request_id: "...",
    sha256: "...",
    created: "2025-01-01T00:00:00.000Z",
    duration: 3671.748,
    channels: 1
  },
  results: {
    channels: [{
      alternatives: [{
        transcript: "Full transcript text...",
        confidence: 0.95,
        words: [
          {
            word: "i'd",
            start: 0.48,
            end: 0.64,
            confidence: 0.99,
            speaker: 0,
            speaker_confidence: 0.97,
            punctuated_word: "I'd"
          },
          // ... more words
        ]
      }]
    }]
  }
}
```

**Key characteristics**:
- Flat array of words under `results.channels[0].alternatives[0].words`
- Each word has: `word`, `start`, `end`, `confidence`, `speaker`, `punctuated_word`
- No `index` field - words are ordered by array position
- Speaker is a number (0, 1, 2, etc.)

## 2. CorrectedDeepgramResponse

**Purpose**: Our extended format that preserves corrections  
**Location**: `CorrectedDeepgramResponse`

```typescript
{
  // Top-level metadata
  text: "Full transcript text...",
  speakers: [ /* utterance segments */ ],
  confidence: 0.95,
  audio_duration: 3671.748,
  processing_time: 45.2,
  
  // Embedded raw response
  raw_response: DeepgramResponse.raw_response,
  
  // Optional corrections metadata
  corrections?: {
    version: 2,
    timestamp: "2025-11-01T01:32:43.970Z",
    speaker_names?: {
      0: "Dr. Smith",
      1: "Student A"
    }
  }
}
```

**Word-level corrections** are embedded directly in `raw_response.results.channels[0].alternatives[0].words` with additional fields:
```typescript
{
  word: "corrected",      // Current corrected value
  punctuated_word: "corrected",
  corrected: true,        // Flag indicating correction
  original_word: "wrong", // Preserved original value
  original_punct: "wrong",
  // ... all standard Deepgram fields
}
```

**Speaker name corrections** are in `corrections.speaker_names` mapping speaker numbers to custom names.

## 3. ReactTranscriptEditorData

**Purpose**: Input format for `@bbc/react-transcript-editor` component  
**Location**: `ReactTranscriptEditorData`

```typescript
{
  words: [
    {
      start: 0.48,
      end: 0.64,
      word: "i'd",
      confidence: 0.99,
      punct: "I'd",
      index: 0,
      speaker: 0,
      corrected?: true,
      original_word?: "wrong",
      original_punct?: "wrong"
    },
    // ... more words with global indices
  ],
  speakers: [ /* utterance segments */ ],
  segmentation: { /* bbckaldi format */ },
  transcript: "Full transcript text...",
  metadata: {
    duration: 3671.748,
    confidence: 0.95,
    service: "deepgram"
  },
  speaker_names?: {
    0: "Dr. Smith",
    1: "Student A"
  }
}
```

**Key characteristics**:
- Flat array of words with **global `index`** starting from 0
- Words are NOT split into paragraphs - entire transcript is one flat list
- Field name is `punct` (not `punctuated_word`)
- Passed to `react-transcript-editor` via `transcriptData` prop

## 4. DraftJS Format (react-transcript-editor Internal)

**Purpose**: Internal format used by react-transcript-editor for editing  
**Location**: Within `react-transcript-editor` component

```typescript
{
  blocks: [
    {
      key: "block-1",
      text: "There is a day.",
      type: "paragraph",
      data: {
        speaker: "Speaker 0",
        words: [
          {
            start: 13.02,
            end: 13.17,
            word: "there",
            punct: "There",
            index: 0,      // Block-local index!
            speaker: 0
          },
          {
            start: 13.17,
            end: 13.38,
            word: "is",
            punct: "is",
            index: 1,      // Block-local index!
            speaker: 0
          },
          // ... words in this paragraph
        ],
        start: 13.02
      },
      entityRanges: [ /* DraftJS entities */ ]
    },
    {
      // Next paragraph block...
      data: {
        speaker: "Speaker 0",
        words: [
          {
            index: 0,  // Starts at 0 again! Not global!
            // ...
          }
        ]
      }
    }
  ],
  entityMap: { /* DraftJS entity map */ }
}
```

**Key characteristics**:
- Words are organized into **paragraph blocks**
- Each block has `block.data.words` array
- **Critical**: `index` is **block-local**, not global! It resets to 0 for each block
- Paragraphs are created by the Deepgram adapter based on utterance segments
- Speaker names are strings like "Speaker 0" in blocks, but numbers in words

## 5. DraftJS Auto-Save Output

**Purpose**: What `react-transcript-editor` returns when `autoSaveContentType="draftjs"`  
**Returned from**: `handleAutoSaveChanges` callback

```typescript
{
  data: {
    blocks: [ /* DraftJS blocks as above */ ],
    entityMap: { /* entity map */ }
  },
  ext: "json"
}
```

**Key characteristics**:
- Wrapped in `{ data: {...}, ext: "json" }` structure
- The actual DraftJS blocks are at `data.blocks`
- Entity map at `data.entityMap`
- This is what we receive in `handleAutoSaveChanges`

## Data Flow Transformations

### Load Flow: Deepgram → Editor
```
1. CorrectedDeepgramResponse (from API/file)
   ↓
2. DeepgramTransformer.transformToReactTranscriptEditor()
   - Extracts raw_response.results.channels[0].alternatives[0].words
   - Adds global `index` field to each word
   - Maps `punctuated_word` → `punct`
   - Adds speaker_names from corrections
   ↓
3. ReactTranscriptEditorData
   ↓
4. react-transcript-editor component
   ↓
5. Deepgram adapter (deepgramToDraft)
   - Groups words into paragraph blocks by utterance segments
   - Adds block-local indices (0, 1, 2... for each block)
   - Creates entityRanges
   ↓
6. DraftJS internal format (blocks with local indices)
```

### Save Flow: Editor → Deepgram
```
1. User edits in react-transcript-editor
   ↓
2. DraftJS auto-save triggers
   - Returns { data: { blocks: [...], entityMap: {...} }, ext: "json" }
   - Each block has words with block-local indices
   ↓
3. Our extractWordsFromDraftJS()
   - Flattens all blocks.data.words into single array
   - Preserves word data but loses block-local indices
   - Extracts speaker names from block.data.speaker
   ↓
4. ReactTranscriptEditorData
   - Flat word array (no proper global indices)
   ↓
5. DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse()
   - Maps words by array position (index 0, 1, 2...)
   - Compares each edited word with original at same position
   - Marks changes as corrected
   ↓
6. CorrectedDeepgramResponse
   - Embeds corrections in raw_response.words
   - Updates speaker segments if names changed
   ↓
7. Saved to file via API
```

## Common Pitfalls

### ⚠️ Index Mismatch Problem
When extracting from DraftJS:
- Block 0 has words with indices [0, 1, 2, ..., 99]
- Block 1 has words with indices [0, 1, 2, ..., 150]
- Flattening creates duplicate indices!

**Current workaround**: We ignore indices and map by array position during merge.

### ⚠️ Word Count Discrepancy
Original might have 7825 words, but extracted has 7833. This happens because:
- Words might be duplicated across block boundaries
- Or paragraph grouping changed during editing

**Current workaround**: We compare words by array position, not total count.

### ⚠️ Speaker Name Format
- In blocks: `"Speaker 0"` (string)
- In words: `0` (number)  
- In speaker_names mapping: `{ 0: "Dr. Smith" }` (number key)

Must handle all three formats when mapping!

## See Also
- `.kiro/steering/react-transcript-editor.md` - Integration guide
- `.kiro/steering/web-ui.md` - Web UI architecture
- `web-ui/src/types/deepgram.ts` - TypeScript definitions
- `web-ui/src/types/transcriptEditor.ts` - Editor types
- `web-ui/src/services/DeepgramTransformer.ts` - Transformation logic

