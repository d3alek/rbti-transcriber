/**
 * Convert Deepgram transcript json to DraftJS
 * Groups words by Deepgram utterance segments (result.speakers) for proper paragraph breaks
 */

import generateEntitiesRanges from '../generate-entities-ranges/index.js';

/**
 * Groups words by Deepgram utterance segments, coalescing consecutive utterances
 * from the same speaker into longer paragraphs
 * @param {array} words - array of word objects from Deepgram transcript
 * @param {array} utterances - array of utterance objects from Deepgram result.speakers
 * @return {array} - array of paragraph objects with words, text, and speaker attributes
 */
const groupWordsInParagraphsByUtterances = (words, utterances) => {
  const results = [];
  
  if (!utterances || utterances.length === 0) {
    // Fallback: group by punctuation if no utterances
    return groupWordsInParagraphs(words);
  }

  let currentParagraph = null;

  utterances.forEach((utterance) => {
    // Find words that overlap with this utterance's time range
    // Use a more lenient approach: word starts or ends within utterance range, or overlaps
    const wordsInUtterance = words.filter(word => {
      const wordStart = word.start;
      const wordEnd = word.end;
      const utteranceStart = utterance.start_time;
      const utteranceEnd = utterance.end_time;
      
      // Word overlaps if it starts before utterance ends and ends after utterance starts
      return wordStart < utteranceEnd && wordEnd > utteranceStart;
    });

    if (wordsInUtterance.length > 0) {
      // Use speaker label from utterance (e.g., "Speaker 0", "Speaker 1")
      const speakerLabel = utterance.speaker || 'TBC';
      
      // If this is the first utterance or speaker changed, start a new paragraph
      if (!currentParagraph || currentParagraph.speaker !== speakerLabel) {
        // Save previous paragraph if it exists
        if (currentParagraph) {
          results.push(currentParagraph);
        }
        
        // Start new paragraph
        currentParagraph = {
          words: [...wordsInUtterance],
          text: wordsInUtterance.map(word => word.punct).join(' '),
          speaker: speakerLabel
        };
      } else {
        // Same speaker: append to current paragraph
        currentParagraph.words.push(...wordsInUtterance);
        currentParagraph.text = currentParagraph.words.map(word => word.punct).join(' ');
      }
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
 * @param {object} deepgramJson - Deepgram transcript data
 * @return {array} - array of DraftJS content blocks
 */
const deepgramToDraft = (deepgramJson) => {
  const results = [];
  
  // Extract words and utterances from Deepgram format
  // Expected format: { words: [...], speakers: [...], segmentation: {...} }
  const words = deepgramJson.words || [];
  const utterances = deepgramJson.speakers || [];
  
  if (!words || words.length === 0) {
    console.warn('Deepgram adapter: No words found in transcript data');
    return results;
  }

  // Group words by utterance segments
  const wordsByParagraphs = groupWordsInParagraphsByUtterances(words, utterances);

  // Convert each paragraph to a DraftJS content block
  wordsByParagraphs.forEach((paragraph, i) => {
    if (paragraph.words && paragraph.words.length > 0) {
      const speakerLabel = paragraph.speaker || `TBC ${i}`;

      const draftJsContentBlockParagraph = {
        text: paragraph.text,
        type: 'paragraph',
        data: {
          speaker: speakerLabel,
          words: paragraph.words,
          start: paragraph.words[0].start
        },
        // Generate entity ranges for word-level timing and highlighting
        entityRanges: generateEntitiesRanges(paragraph.words, 'punct')
      };
      
      results.push(draftJsContentBlockParagraph);
    }
  });

  return results;
};

export default deepgramToDraft;

