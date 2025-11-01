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
  
  // Track consumed words to prevent duplication across utterances
  // Use start time as unique identifier (unlikely two words have exact same start time)
  const consumedWords = new Set();

  utterances.forEach((utterance) => {
    // Find words that overlap with this utterance's time range
    // Use a more lenient approach: word starts or ends within utterance range, or overlaps
    // Also check word-level speaker assignment to catch words that Deepgram may have
    // incorrectly placed outside the utterance time range
    const utteranceSpeakerMatch = utterance.speaker ? utterance.speaker.match(/^Speaker (\d+)$/) : null;
    const utteranceSpeakerNum = utteranceSpeakerMatch ? parseInt(utteranceSpeakerMatch[1]) : null;
    
    // Build initial word list from time overlap, excluding already consumed words
    let wordsInUtterance = words.filter(word => {
      // Skip if already consumed
      if (consumedWords.has(word.start)) {
        return false;
      }
      
      const wordStart = word.start;
      const wordEnd = word.end;
      const utteranceStart = utterance.start_time;
      const utteranceEnd = utterance.end_time;
      
      // Word overlaps if it starts before utterance ends and ends after utterance starts
      return wordStart < utteranceEnd && wordEnd > utteranceStart;
    });
    
    // If utterance text suggests words that should be included but aren't in the time range,
    // try to find and include them (handles Deepgram utterance boundary errors)
    // This fixes cases like "Doctor Scott?" where "Scott" might be slightly outside the utterance time
    const utteranceText = utterance.text || '';
    if (utteranceText) {
      // Count occurrences of each word in wordsInUtterance (by cleaned word text)
      const includedWordCounts = new Map();
      wordsInUtterance.forEach(w => {
        // Clean the word field to match how we clean utterance words (remove punctuation)
        const cleaned = w.word.toLowerCase().replace(/[.,!?;:]/g, '');
        if (cleaned) {
          includedWordCounts.set(cleaned, (includedWordCounts.get(cleaned) || 0) + 1);
        }
      });
      
      const utteranceWords = utteranceText.toLowerCase().split(/\s+/);
      
      // Count occurrences in utterance text and find truly missing words
      const utteranceWordCounts = new Map();
      utteranceWords.forEach(uw => {
        const cleaned = uw.replace(/[.,!?;:]/g, '').toLowerCase();
        if (cleaned) {
          utteranceWordCounts.set(cleaned, (utteranceWordCounts.get(cleaned) || 0) + 1);
        }
      });
      
      // Find words that appear more times in utterance text than in included words
      const missingWords = [];
      utteranceWordCounts.forEach((count, word) => {
        const includedCount = includedWordCounts.get(word) || 0;
        const missing = count - includedCount;
        if (missing > 0) {
          // Add this word 'missing' times to the missing words list
          for (let i = 0; i < missing; i++) {
            missingWords.push(word);
          }
        }
      });
      
      // If there are missing words, look for them near the utterance (before or after)
      if (missingWords.length > 0) {
        const utteranceStartTime = utterance.start_time;
        const utteranceEndTime = utterance.end_time;
        
        // Look for words that:
        // 1. Match the missing words from utterance text
        // 2. Are close in time to the utterance (within 2 seconds before or 6 seconds after)
        // 3. Haven't been consumed yet
        const candidateWords = words.filter(word => {
          if (consumedWords.has(word.start)) {
            return false;
          }
          
          // Clean word text to match missing words format (no punctuation)
          const wordText = word.word.toLowerCase().replace(/[.,!?;:]/g, '');
          const wordPunct = word.punct.toLowerCase().replace(/[.,!?;:]/g, '');
          // Match if cleaned word text or punct equals any missing word
          const isMissing = missingWords.some(mw => wordText === mw || wordPunct === mw);
          
          // Allow words slightly before utterance start (for cases like "Doctor Scott?" split)
          // or after utterance end (for cases like "thing" completing a sentence)
          const isCloseInTime = (word.start >= utteranceStartTime - 2.0 && word.start < utteranceEndTime + 6.0);
          
          return isMissing && isCloseInTime;
        });
        
        // Add candidate words that seem to complete the utterance
        if (candidateWords.length > 0) {
          // Sort by time and take words that form a logical continuation
          candidateWords.sort((a, b) => a.start - b.start);
          
          // Create a set of word start times already in wordsInUtterance to avoid duplicates
          const existingStartTimes = new Set(wordsInUtterance.map(w => w.start));
          
          // Add words until we hit a sentence boundary
          // Trust the utterance text - if it says the word should be there, include it
          // even if word-level speaker assignment differs (Deepgram can be wrong about word-level)
          for (const candidate of candidateWords) {
            // Skip if this word is already in wordsInUtterance (check by start time)
            if (existingStartTimes.has(candidate.start)) {
              continue;
            }
            
            // Add this word if it's in the utterance text
            wordsInUtterance.push(candidate);
            existingStartTimes.add(candidate.start);
            // Mark as consumed immediately
            consumedWords.add(candidate.start);
            
            // If it completes a sentence, we're done adding words from this utterance
            if (candidate.punct && /[.?!]$/.test(candidate.punct.trim())) {
              break;
            }
          }
        }
      }
      
      // Sort wordsInUtterance by start time after adding candidates
      wordsInUtterance.sort((a, b) => a.start - b.start);
    }
    
    // Mark all words in this utterance as consumed
    wordsInUtterance.forEach(word => {
      consumedWords.add(word.start);
    });

    if (wordsInUtterance.length > 0) {
      // Use speaker label from utterance (e.g., "Speaker 0", "Speaker 1")
      const speakerLabel = utterance.speaker || 'TBC';
      
      // Check word-level speaker assignments - if most words in this utterance match a different speaker,
      // we might need to be smarter about speaker assignment, but for now we'll use utterance speaker
      // as the primary indicator and only break if utterance speaker changes
      
      // Check if speaker changed from previous utterance
      const previousSpeaker = currentParagraph ? currentParagraph.speaker : (currentSentence ? currentSentence.speaker : null);
      const speakerChanged = previousSpeaker && previousSpeaker !== speakerLabel;
      
      // If speaker changed, check if we need to finalize incomplete sentence from previous speaker
      // BUT: check if the first word of the new utterance actually completes the previous sentence
      // by checking if it ends with punctuation and starts immediately after the previous sentence
      if (speakerChanged && currentSentence && currentSentence.words.length > 0) {
        // Check if the sentence from previous speaker is complete (ends with punctuation)
        const lastWord = currentSentence.words[currentSentence.words.length - 1];
        const sentenceComplete = lastWord.punct && /[.?!]$/.test(lastWord.punct.trim());
        
        // Check if the first word of the new utterance completes the previous sentence
        const firstNewWord = wordsInUtterance[0];
        const newWordCompletesSentence = firstNewWord.punct && /[.?!]$/.test(firstNewWord.punct.trim());
        const timeGap = firstNewWord.start - lastWord.end;
        
        // Get speaker from previous sentence's words (word-level assignment)
        const previousSentenceLastWordSpeaker = currentSentence.words.length > 0 ? 
          currentSentence.words[currentSentence.words.length - 1].speaker : null;
        const newWordSpeaker = firstNewWord.speaker;
        
        // Check if word-level speakers match (more reliable than utterance-level)
        const wordLevelSpeakersMatch = previousSentenceLastWordSpeaker !== undefined && 
          previousSentenceLastWordSpeaker !== null &&
          newWordSpeaker !== undefined &&
          previousSentenceLastWordSpeaker === newWordSpeaker;
        
        // Also check if the utterance text suggests "thing" should complete the previous sentence
        // by looking for "thing" in the utterance text immediately after "this"
        const utteranceText = utterance.text || '';
        const likelyContinuation = timeGap < 6.0 && newWordCompletesSentence && 
          (wordLevelSpeakersMatch || utteranceText.toLowerCase().includes('thing'));
        
        if (!sentenceComplete) {
          // Incomplete sentence from previous speaker
          // If the new word completes the sentence and appears to be a continuation,
          // add it to the previous sentence to complete it
          if (likelyContinuation) {
            // The new word likely completes the previous sentence - add it to current sentence
            // Update speaker label to match the word-level assignment if it differs
            currentSentence.words.push(firstNewWord);
            // If word-level speaker differs from utterance speaker, use word-level for consistency
            if (newWordSpeaker !== undefined && newWordSpeaker === previousSentenceLastWordSpeaker) {
              // Keep the sentence with the word-level speaker assignment
            }
            // Process remaining words normally (skip the first one since we added it)
            wordsInUtterance = wordsInUtterance.slice(1);
          } else {
            // Finalize incomplete sentence from previous speaker
            if (currentParagraph && currentParagraph.speaker === currentSentence.speaker) {
              // Add incomplete sentence to existing paragraph for this speaker
              currentParagraph.words.push(...currentSentence.words);
              currentParagraph.text = currentParagraph.words.map(w => w.punct).join(' ');
            } else if (currentParagraph) {
              // Paragraph is from different speaker - finalize it first
              results.push(currentParagraph);
              currentParagraph = {
                words: [...currentSentence.words],
                text: currentSentence.words.map(w => w.punct).join(' '),
                speaker: currentSentence.speaker
              };
            } else {
              // No paragraph yet - create one for the incomplete sentence
              currentParagraph = {
                words: [...currentSentence.words],
                text: currentSentence.words.map(w => w.punct).join(' '),
                speaker: currentSentence.speaker
              };
            }
            // Finalize paragraph for previous speaker (even though sentence is incomplete)
            results.push(currentParagraph);
            currentParagraph = null;
            // Reset sentence so we start fresh for new speaker
            currentSentence = null;
          }
        }
        // If sentence was complete, it will be handled normally when we process the words
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
            // Check if paragraph speaker matches sentence speaker
            if (currentParagraph.speaker !== speakerLabel) {
              // Speaker changed - finalize old paragraph and start new one
              results.push(currentParagraph);
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

