/**
 * Convert Deepgram transcript json to DraftJS
 * Groups words by Deepgram utterance segments (result.speakers) for proper paragraph breaks
 */

import generateEntitiesRanges from '../generate-entities-ranges/index.js';

// Configuration: Maximum paragraph duration in seconds
const MAX_PARAGRAPH_DURATION_SECONDS = 30; // 30 seconds (half a minute)

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
 * Groups words by Deepgram utterance segments, combining sentences into paragraphs.
 * Splits on sentence boundaries (full stops) and combines sentences into paragraphs
 * based on time duration (default 30 seconds). Always ends paragraphs at full stops.
 * @param {array} words - array of word objects from Deepgram transcript
 * @param {array} utterances - array of utterance objects from Deepgram result.speakers
 * @param {number} maxParagraphDurationSeconds - maximum duration for a paragraph in seconds
 * @return {array} - array of paragraph objects with words, text, and speaker attributes
 */
const groupWordsInParagraphsByUtterances = (words, utterances, maxParagraphDurationSeconds = MAX_PARAGRAPH_DURATION_SECONDS) => {
  const results = [];
  
  if (!utterances || utterances.length === 0) {
    // Fallback: group by punctuation if no utterances
    return groupWordsInParagraphs(words);
  }

  let currentParagraph = null;
  let currentSentence = null;

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
        if (currentSentence) {
          // Add current sentence to paragraph if exists
          if (currentParagraph) {
            currentParagraph.words.push(...currentSentence.words);
            currentParagraph.text = currentParagraph.words.map(w => w.punct).join(' ');
          } else {
            currentParagraph = {
              words: [...currentSentence.words],
              text: currentSentence.words.map(w => w.punct).join(' '),
              speaker: currentSentence.speaker
            };
          }
          currentSentence = null;
        }
        if (currentParagraph) {
          results.push(currentParagraph);
        }
        currentParagraph = null;
      }
      
      // Process words to build sentences and paragraphs
      wordsInUtterance.forEach((word) => {
        // Check if this word ends a sentence (ends with . ? !)
        const endsSentence = word.punct && /[.?!]$/.test(word.punct.trim());
        
        // Start a new sentence if we don't have one
        if (!currentSentence) {
          currentSentence = {
            words: [],
            speaker: speakerLabel
          };
        }
        
        // Add word to current sentence
        currentSentence.words.push(word);
        
        // If sentence ends, check if we should add it to current paragraph or start a new one
        if (endsSentence) {
          // Start a new paragraph if we don't have one
          if (!currentParagraph) {
            currentParagraph = {
              words: [...currentSentence.words],
              text: currentSentence.words.map(w => w.punct).join(' '),
              speaker: speakerLabel
            };
          } else {
            // Check if adding this sentence would exceed the duration limit
            const paragraphStart = currentParagraph.words[0].start;
            const sentenceEnd = currentSentence.words[currentSentence.words.length - 1].end;
            const paragraphDuration = sentenceEnd - paragraphStart;
            
            if (paragraphDuration >= maxParagraphDurationSeconds) {
              // Duration limit reached - finalize current paragraph and start a new one
              results.push(currentParagraph);
              currentParagraph = {
                words: [...currentSentence.words],
                text: currentSentence.words.map(w => w.punct).join(' '),
                speaker: speakerLabel
              };
            } else {
              // Add sentence to current paragraph
              currentParagraph.words.push(...currentSentence.words);
              currentParagraph.text = currentParagraph.words.map(w => w.punct).join(' ');
            }
          }
          
          // Reset sentence for next one
          currentSentence = null;
        }
      });
    }
  });

  // Handle any remaining sentence
  if (currentSentence) {
    if (currentParagraph) {
      currentParagraph.words.push(...currentSentence.words);
      currentParagraph.text = currentParagraph.words.map(w => w.punct).join(' ');
    } else {
      currentParagraph = {
        words: [...currentSentence.words],
        text: currentSentence.words.map(w => w.punct).join(' '),
        speaker: currentSentence.speaker
      };
    }
  }

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

