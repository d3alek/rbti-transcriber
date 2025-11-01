/**
 * Convert Deepgram transcript json to DraftJS
 * Groups words by Deepgram utterance segments (result.speakers) for proper paragraph breaks
 */

import generateEntitiesRanges from '../generate-entities-ranges/index.js';

// Configuration: Maximum paragraph duration in seconds
const MAX_PARAGRAPH_DURATION_SECONDS = 60; // 1 minute
// When approaching the limit, allow up to this multiplier to find a natural break point (full stop)
const DURATION_FLEXIBILITY_MULTIPLIER = 1.2; // Allow up to 20% over limit to find full stop

/**
 * Check if an utterance's text ends with a sentence-ending punctuation (full stop, question mark, exclamation)
 * @param {array} wordsInUtterance - array of word objects from the utterance
 * @return {boolean} - true if the utterance ends with sentence-ending punctuation
 */
const endsWithFullStop = (wordsInUtterance) => {
  if (!wordsInUtterance || wordsInUtterance.length === 0) {
    return false;
  }
  const lastWord = wordsInUtterance[wordsInUtterance.length - 1];
  const lastChar = lastWord.punct ? lastWord.punct.slice(-1) : '';
  return /[.?!]/.test(lastChar);
};

/**
 * Groups words by Deepgram utterance segments, splitting on sentence boundaries (full stops).
 * Always breaks paragraphs on sentence-ending punctuation (. ? !) while respecting speaker boundaries.
 * @param {array} words - array of word objects from Deepgram transcript
 * @param {array} utterances - array of utterance objects from Deepgram result.speakers
 * @param {number} maxParagraphDurationSeconds - maximum duration for a paragraph in seconds (not currently used, but kept for compatibility)
 * @return {array} - array of paragraph objects with words, text, and speaker attributes
 */
const groupWordsInParagraphsByUtterances = (words, utterances, maxParagraphDurationSeconds = MAX_PARAGRAPH_DURATION_SECONDS) => {
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
      
      // Check if speaker changed
      const speakerChanged = currentParagraph && currentParagraph.speaker !== speakerLabel;
      
      // Always break on speaker change
      if (speakerChanged) {
        if (currentParagraph) {
          results.push(currentParagraph);
        }
        currentParagraph = null;
      }
      
      // Split words in this utterance into sentences (break on . ? !)
      // Process words one at a time to detect sentence boundaries
      wordsInUtterance.forEach((word, wordIndex) => {
        // Check if this word ends a sentence (ends with . ? !)
        // Check the last character of the punctuated word
        const endsSentence = word.punct && /[.?!]$/.test(word.punct.trim());
        
        // If we don't have a current paragraph, start a new one
        if (!currentParagraph) {
          currentParagraph = {
            words: [],
            text: '',
            speaker: speakerLabel
          };
        }
        
        // Add word to current paragraph
        currentParagraph.words.push(word);
        currentParagraph.text = currentParagraph.words.map(w => w.punct).join(' ');
        
        // If this word ends a sentence, finalize the paragraph and start a new one
        if (endsSentence) {
          results.push(currentParagraph);
          currentParagraph = null; // Will start new paragraph on next word
        }
      });
    }
  });

  // Add the last paragraph if it exists (might not end with punctuation)
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

  // Group words by utterance segments, breaking paragraphs at max duration (default 60 seconds)
  // Will try to break on full stops when approaching the limit
  const wordsByParagraphs = groupWordsInParagraphsByUtterances(words, utterances, MAX_PARAGRAPH_DURATION_SECONDS);

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

