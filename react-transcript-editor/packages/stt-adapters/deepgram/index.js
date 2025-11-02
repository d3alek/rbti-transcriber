/**
 * Convert Deepgram transcript json to DraftJS
 * Groups words using paragraph_start and paragraph_end markers from RichWordsTranscript format
 */

import generateEntitiesRanges from '../generate-entities-ranges/index.js';

/**
 * Groups words by paragraph boundaries marked with paragraph_start and paragraph_end
 * Uses Deepgram's paragraph intelligence - words are marked at creation time
 * @param {array} words - array of word objects with paragraph_start/paragraph_end markers
 * @return {array} - array of paragraph objects with words, text, and speaker attributes
 */
const groupWordsInParagraphsByMarkers = (words) => {
  const results = [];
  
  if (!words || words.length === 0) {
    return results;
  }

  let currentParagraph = null;
  let currentSpeaker = null;

  words.forEach((word) => {
    // Get speaker name - use custom name if available (from speaker_names in corrections)
    // For now, we'll determine speaker from the word's speaker index
    // The speaker label will be determined when we process the paragraph
    const speakerIndex = word.speaker !== undefined ? word.speaker : 0;
    
    // Start a new paragraph if this word is marked as paragraph_start
    // OR if we don't have a current paragraph yet
    if (word.paragraph_start || !currentParagraph) {
      // Save previous paragraph if it exists
      if (currentParagraph) {
        results.push(currentParagraph);
      }
      
      // Determine speaker label for this paragraph
      // We'll use "Speaker X" format for now, custom names are handled elsewhere
      const speakerLabel = `Speaker ${speakerIndex}`;
      currentSpeaker = speakerIndex;
      
      // Start new paragraph
      currentParagraph = {
        words: [word],
        text: word.punct || word.word,
        speaker: speakerLabel
      };
    } else {
      // Continue current paragraph
      currentParagraph.words.push(word);
      currentParagraph.text += ' ' + (word.punct || word.word);
      
      // Update speaker if it changed within the paragraph (shouldn't happen with proper markers, but handle it)
      if (word.speaker !== undefined && word.speaker !== currentSpeaker) {
        // Speaker changed mid-paragraph - this shouldn't happen with Deepgram paragraphs
        // but we'll handle it gracefully by using the most common speaker in the paragraph
        const speakerCounts = {};
        currentParagraph.words.forEach(w => {
          const spk = w.speaker !== undefined ? w.speaker : 0;
          speakerCounts[spk] = (speakerCounts[spk] || 0) + 1;
        });
        const mostCommonSpeaker = Object.keys(speakerCounts).reduce((a, b) => 
          speakerCounts[a] > speakerCounts[b] ? a : b
        );
        currentParagraph.speaker = `Speaker ${mostCommonSpeaker}`;
        currentSpeaker = parseInt(mostCommonSpeaker);
      }
    }
    
    // End paragraph if this word is marked as paragraph_end
    if (word.paragraph_end && currentParagraph) {
      results.push(currentParagraph);
      currentParagraph = null;
      currentSpeaker = null;
    }
  });

  // Add the last paragraph if it exists
  if (currentParagraph) {
    results.push(currentParagraph);
  }

  return results;
};

/**
 * Fallback: groups words list from transcript based on punctuation
 * @param {array} words - array of word objects from Deepgram transcript
 */
const groupWordsInParagraphs = (words) => {
  const results = [];
  let paragraph = { words: [], text: [] };

  words.forEach(word => {
    paragraph.words.push(word);
    paragraph.text.push(word.punct);

    // if word contains punctuation
    if (/[.?!]/.test(word.punct)) {
      paragraph.text = paragraph.text.join(' ');
      results.push(paragraph);
      // reset paragraph
      paragraph = { words: [], text: [] };
    }
  });

  // Add final paragraph if there are remaining words
  if (paragraph.words.length > 0) {
    paragraph.text = paragraph.text.join(' ');
    results.push(paragraph);
  }

  return results;
};

/**
 * Convert Deepgram transcript to DraftJS format
 * @param {object} deepgramJson - Deepgram transcript data (RichWordsTranscript format)
 * Expected format: { words: [...], speakers: [...], segmentation: {...}, speaker_names: {...} }
 * Words should have paragraph_start and paragraph_end markers from Deepgram paragraphs
 * @return {array} - array of DraftJS content blocks
 */
const deepgramToDraft = (deepgramJson) => {
  const results = [];
  
  // Extract words from RichWordsTranscript format
  const words = deepgramJson.words || [];
  
  if (!words || words.length === 0) {
    console.warn('Deepgram adapter: No words found in transcript data');
    return results;
  }

  // Apply custom speaker names if available
  const speakerNamesMap = deepgramJson.speaker_names || {};
  const wordsWithSpeakerNames = words.map(word => {
    const speakerIndex = word.speaker !== undefined ? word.speaker : 0;
    const customName = speakerNamesMap[speakerIndex];
    return {
      ...word,
      _speakerLabel: customName || `Speaker ${speakerIndex}`  // Internal label for grouping
    };
  });

  // Group words by paragraph markers (paragraph_start/paragraph_end)
  const wordsByParagraphs = groupWordsInParagraphsByMarkers(wordsWithSpeakerNames);

  // Convert each paragraph to a DraftJS content block
  wordsByParagraphs.forEach((paragraph, i) => {
    if (paragraph.words && paragraph.words.length > 0) {
      // Use custom speaker name if available, otherwise use the determined speaker
      const firstWord = paragraph.words[0];
      const speakerIndex = firstWord.speaker !== undefined ? firstWord.speaker : 0;
      const customName = speakerNamesMap[speakerIndex];
      const speakerLabel = customName || paragraph.speaker || `Speaker ${speakerIndex}`;

      // Remove internal _speakerLabel from words before storing
      const cleanWords = paragraph.words.map(word => {
        const { _speakerLabel, ...cleanWord } = word;
        return cleanWord;
      });

      // Generate entity ranges for word-level timing and highlighting
      const entityRanges = generateEntitiesRanges(cleanWords, 'punct');
      
      // Debug: Verify entity ranges match paragraph text
      if (i < 3) { // Only log first few paragraphs to avoid spam
        console.log('📊 [Deepgram Adapter Debug] Block created:', {
          blockIndex: i,
          paragraphText: paragraph.text,
          paragraphTextLength: paragraph.text.length,
          wordCount: cleanWords.length,
          entityRangesCount: entityRanges.length,
          firstFewWords: cleanWords.slice(0, 3).map(w => ({
            text: w.punct,
            start: w.start,
            end: w.end
          })),
          firstFewEntities: entityRanges.slice(0, 3).map(e => ({
            text: e.text,
            start: e.start,
            end: e.end,
            offset: e.offset,
            length: e.length
          })),
          // Verify offsets match text
          textAtOffsets: entityRanges.slice(0, 3).map(e => ({
            offset: e.offset,
            expectedText: paragraph.text.substr(e.offset, e.length),
            actualText: e.text
          }))
        });
      }
      
      const draftJsContentBlockParagraph = {
        text: paragraph.text,
        type: 'paragraph',
        data: {
          speaker: speakerLabel,
          words: cleanWords,
          start: cleanWords[0].start
        },
        entityRanges: entityRanges
      };
      
      results.push(draftJsContentBlockParagraph);
    }
  });

  return results;
};

export default deepgramToDraft;
