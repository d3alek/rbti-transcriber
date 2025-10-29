"""
Transcript Processor Service

Handles processing of Deepgram responses for paragraph extraction,
text updates, and word-time synchronization.
"""

import re
import uuid
from typing import List, Optional, Dict, Any, Tuple
from bisect import bisect_left

from ..models import (
    DeepgramResponse, ParagraphData, SentenceData, WordData,
    DeepgramAlternative, DeepgramChannel
)


class TranscriptProcessor:
    """Processes Deepgram responses for enhanced transcript editing."""
    
    def __init__(self):
        """Initialize the transcript processor."""
        pass
    
    def extract_paragraphs(self, response: DeepgramResponse) -> List[ParagraphData]:
        """
        Extract paragraph data from raw Deepgram response.
        
        Args:
            response: Raw Deepgram API response
            
        Returns:
            List of ParagraphData objects
        """
        if not response.results.channels:
            return []
        
        # Get the first channel's first alternative
        channel = response.results.channels[0]
        if not channel.alternatives:
            return []
        
        alternative = channel.alternatives[0]
        
        # Check if paragraphs structure exists
        if alternative.paragraphs and "paragraphs" in alternative.paragraphs:
            return self._extract_from_paragraphs_structure(alternative)
        else:
            # Fallback: create paragraphs from words
            return self._create_paragraphs_from_words(alternative)
    
    def _extract_from_paragraphs_structure(self, alternative: DeepgramAlternative) -> List[ParagraphData]:
        """
        Extract paragraphs from Deepgram's paragraph structure.
        
        Args:
            alternative: Deepgram alternative with paragraphs
            
        Returns:
            List of ParagraphData objects
        """
        paragraphs = []
        word_index = 0
        
        for para_idx, paragraph in enumerate(alternative.paragraphs["paragraphs"]):
            sentences = []
            paragraph_words = []
            paragraph_text = ""
            paragraph_start = float('inf')
            paragraph_end = 0.0
            paragraph_speakers = set()
            total_confidence = 0.0
            confidence_count = 0
            
            for sent_idx, sentence in enumerate(paragraph["sentences"]):
                sentence_words = []
                sentence_start = float('inf')
                sentence_end = 0.0
                sentence_speaker = None
                
                # Process words in sentence
                for word_data in sentence["words"]:
                    word = WordData(
                        word=word_data["word"],
                        start=word_data["start"],
                        end=word_data["end"],
                        confidence=word_data["confidence"],
                        speaker=word_data.get("speaker", 0),
                        speaker_confidence=word_data.get("speaker_confidence", 1.0),
                        punctuated_word=word_data.get("punctuated_word", word_data["word"]),
                        index=word_index
                    )
                    
                    sentence_words.append(word)
                    paragraph_words.append(word)
                    
                    # Update timing and speaker info
                    sentence_start = min(sentence_start, word.start)
                    sentence_end = max(sentence_end, word.end)
                    paragraph_start = min(paragraph_start, word.start)
                    paragraph_end = max(paragraph_end, word.end)
                    
                    if sentence_speaker is None:
                        sentence_speaker = word.speaker
                    
                    paragraph_speakers.add(word.speaker)
                    total_confidence += word.confidence
                    confidence_count += 1
                    word_index += 1
                
                # Create sentence data
                sentence_data = SentenceData(
                    id=sentence.get("id", f"sent_{para_idx}_{sent_idx}"),
                    text=sentence["text"],
                    start=sentence_start if sentence_start != float('inf') else 0.0,
                    end=sentence_end,
                    words=sentence_words,
                    speaker=sentence_speaker or 0
                )
                
                sentences.append(sentence_data)
                paragraph_text += sentence["text"] + " "
            
            # Determine primary speaker (most common in paragraph)
            if paragraph_speakers:
                speaker_counts = {}
                for word in paragraph_words:
                    speaker_counts[word.speaker] = speaker_counts.get(word.speaker, 0) + 1
                primary_speaker = max(speaker_counts, key=speaker_counts.get)
            else:
                primary_speaker = 0
            
            # Calculate average confidence
            avg_confidence = total_confidence / confidence_count if confidence_count > 0 else 0.0
            
            # Create paragraph data
            paragraph_data = ParagraphData(
                id=f"para_{para_idx}",
                text=paragraph_text.strip(),
                start_time=paragraph_start if paragraph_start != float('inf') else 0.0,
                end_time=paragraph_end,
                speaker=primary_speaker,
                sentences=sentences,
                words=paragraph_words,
                confidence=avg_confidence
            )
            
            paragraphs.append(paragraph_data)
        
        return paragraphs
    
    def _create_paragraphs_from_words(self, alternative: DeepgramAlternative) -> List[ParagraphData]:
        """
        Create paragraphs from word list when paragraph structure is not available.
        
        Args:
            alternative: Deepgram alternative with words
            
        Returns:
            List of ParagraphData objects
        """
        if not alternative.words:
            return []
        
        paragraphs = []
        current_paragraph_words = []
        current_speaker = alternative.words[0].speaker
        paragraph_start_time = alternative.words[0].start
        word_index = 0
        
        # Group words into paragraphs based on speaker changes and pauses
        for word in alternative.words:
            word.index = word_index
            word_index += 1
            
            # Check for paragraph break conditions
            should_break = False
            
            # Speaker change
            if word.speaker != current_speaker and current_paragraph_words:
                should_break = True
            
            # Long pause (more than 2 seconds)
            if (current_paragraph_words and 
                word.start - current_paragraph_words[-1].end > 2.0):
                should_break = True
            
            # Maximum paragraph length (100 words)
            if len(current_paragraph_words) >= 100:
                should_break = True
            
            if should_break and current_paragraph_words:
                # Create paragraph from current words
                paragraph = self._create_paragraph_from_words(
                    current_paragraph_words, 
                    len(paragraphs),
                    paragraph_start_time
                )
                paragraphs.append(paragraph)
                
                # Start new paragraph
                current_paragraph_words = [word]
                current_speaker = word.speaker
                paragraph_start_time = word.start
            else:
                current_paragraph_words.append(word)
                if not current_paragraph_words or len(current_paragraph_words) == 1:
                    current_speaker = word.speaker
                    paragraph_start_time = word.start
        
        # Add final paragraph
        if current_paragraph_words:
            paragraph = self._create_paragraph_from_words(
                current_paragraph_words, 
                len(paragraphs),
                paragraph_start_time
            )
            paragraphs.append(paragraph)
        
        return paragraphs
    
    def _create_paragraph_from_words(self, words: List[WordData], 
                                   paragraph_index: int,
                                   start_time: float) -> ParagraphData:
        """
        Create a ParagraphData object from a list of words.
        
        Args:
            words: List of WordData objects
            paragraph_index: Index of the paragraph
            start_time: Start time of the paragraph
            
        Returns:
            ParagraphData object
        """
        if not words:
            return ParagraphData(
                id=f"para_{paragraph_index}",
                text="",
                start_time=start_time,
                end_time=start_time,
                speaker=0,
                sentences=[],
                words=[],
                confidence=0.0
            )
        
        # Calculate paragraph metrics
        end_time = words[-1].end
        total_confidence = sum(word.confidence for word in words)
        avg_confidence = total_confidence / len(words)
        
        # Determine primary speaker
        speaker_counts = {}
        for word in words:
            speaker_counts[word.speaker] = speaker_counts.get(word.speaker, 0) + 1
        primary_speaker = max(speaker_counts, key=speaker_counts.get)
        
        # Create text from punctuated words
        text_parts = []
        for word in words:
            text_parts.append(word.punctuated_word)
        text = " ".join(text_parts)
        
        # Create a single sentence for the paragraph (simplified)
        sentence = SentenceData(
            id=f"sent_{paragraph_index}_0",
            text=text,
            start=start_time,
            end=end_time,
            words=words,
            speaker=primary_speaker
        )
        
        return ParagraphData(
            id=f"para_{paragraph_index}",
            text=text,
            start_time=start_time,
            end_time=end_time,
            speaker=primary_speaker,
            sentences=[sentence],
            words=words,
            confidence=avg_confidence
        )
    
    def update_paragraph_text(self, response: DeepgramResponse, 
                            paragraph_id: str, new_text: str) -> DeepgramResponse:
        """
        Update paragraph text in a Deepgram response.
        
        Args:
            response: Original Deepgram response
            paragraph_id: ID of paragraph to update
            new_text: New text content
            
        Returns:
            Updated Deepgram response
        """
        # Extract current paragraphs
        paragraphs = self.extract_paragraphs(response)
        
        # Find the paragraph to update
        target_paragraph = None
        for paragraph in paragraphs:
            if paragraph.id == paragraph_id:
                target_paragraph = paragraph
                break
        
        if not target_paragraph:
            raise ValueError(f"Paragraph {paragraph_id} not found")
        
        # Calculate timing adjustments
        adjusted_words = self.calculate_timing_adjustments(
            target_paragraph.text, 
            new_text, 
            target_paragraph.words
        )
        
        # Update the response structure
        updated_response = self._update_response_with_new_words(
            response, target_paragraph, adjusted_words, new_text
        )
        
        return updated_response
    
    def calculate_timing_adjustments(self, original_text: str, 
                                   new_text: str, 
                                   original_words: List[WordData]) -> List[WordData]:
        """
        Calculate timing adjustments for edited text.
        
        Args:
            original_text: Original paragraph text
            new_text: New paragraph text
            original_words: Original word timing data
            
        Returns:
            Adjusted word timing data
        """
        # Simple implementation: preserve timing for unchanged words,
        # interpolate timing for new words
        
        original_tokens = original_text.split()
        new_tokens = new_text.split()
        
        if not original_words:
            return []
        
        # If text is identical, return original words
        if original_text.strip() == new_text.strip():
            return original_words
        
        adjusted_words = []
        
        # Calculate time per character for interpolation
        total_duration = original_words[-1].end - original_words[0].start
        original_char_count = len(original_text)
        time_per_char = total_duration / original_char_count if original_char_count > 0 else 0
        
        # Start timing from original start
        current_time = original_words[0].start
        
        for i, token in enumerate(new_tokens):
            # Try to find matching word in original
            matching_word = None
            if i < len(original_words):
                # Simple matching by position
                matching_word = original_words[i]
            
            if matching_word and matching_word.word.lower() == token.lower():
                # Use original timing for unchanged words
                word_data = WordData(
                    word=token,
                    start=matching_word.start,
                    end=matching_word.end,
                    confidence=matching_word.confidence,
                    speaker=matching_word.speaker,
                    speaker_confidence=matching_word.speaker_confidence,
                    punctuated_word=token,
                    index=i
                )
                current_time = matching_word.end
            else:
                # Interpolate timing for new/changed words
                word_duration = len(token) * time_per_char
                word_data = WordData(
                    word=token,
                    start=current_time,
                    end=current_time + word_duration,
                    confidence=0.8,  # Lower confidence for edited words
                    speaker=original_words[0].speaker,  # Use paragraph speaker
                    speaker_confidence=0.8,
                    punctuated_word=token,
                    index=i
                )
                current_time += word_duration + 0.1  # Small gap between words
            
            adjusted_words.append(word_data)
        
        return adjusted_words
    
    def _update_response_with_new_words(self, response: DeepgramResponse,
                                      target_paragraph: ParagraphData,
                                      new_words: List[WordData],
                                      new_text: str) -> DeepgramResponse:
        """
        Update the Deepgram response with new word data.
        
        Args:
            response: Original response
            target_paragraph: Paragraph being updated
            new_words: New word timing data
            new_text: New paragraph text
            
        Returns:
            Updated Deepgram response
        """
        # Create a deep copy of the response
        import copy
        updated_response = copy.deepcopy(response)
        
        # Update the words list in the first alternative
        if (updated_response.results.channels and 
            updated_response.results.channels[0].alternatives):
            
            alternative = updated_response.results.channels[0].alternatives[0]
            
            # Find and replace words for this paragraph
            original_word_indices = [word.index for word in target_paragraph.words]
            
            if original_word_indices:
                start_idx = min(original_word_indices)
                end_idx = max(original_word_indices) + 1
                
                # Replace words in the range
                new_word_list = (
                    alternative.words[:start_idx] + 
                    new_words + 
                    alternative.words[end_idx:]
                )
                
                # Update indices for words after the edit
                for i, word in enumerate(new_word_list):
                    word.index = i
                
                alternative.words = new_word_list
            
            # Update transcript text
            all_words = [word.punctuated_word for word in alternative.words]
            alternative.transcript = " ".join(all_words)
        
        return updated_response
    
    def find_word_at_time(self, response: DeepgramResponse, 
                         time: float) -> Optional[WordData]:
        """
        Find the word being spoken at a specific time.
        
        Args:
            response: Deepgram response
            time: Time in seconds
            
        Returns:
            WordData object or None if no word found
        """
        if not response.results.channels:
            return None
        
        channel = response.results.channels[0]
        if not channel.alternatives:
            return None
        
        words = channel.alternatives[0].words
        
        # Binary search for efficiency
        word_starts = [word.start for word in words]
        
        # Find the word that contains this time
        idx = bisect_left(word_starts, time)
        
        # Check current and previous word
        for check_idx in [idx - 1, idx]:
            if 0 <= check_idx < len(words):
                word = words[check_idx]
                if word.start <= time <= word.end:
                    return word
        
        return None
    
    def get_words_in_time_range(self, response: DeepgramResponse,
                               start_time: float, end_time: float) -> List[WordData]:
        """
        Get all words within a specific time range.
        
        Args:
            response: Deepgram response
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            List of WordData objects in the time range
        """
        if not response.results.channels:
            return []
        
        channel = response.results.channels[0]
        if not channel.alternatives:
            return []
        
        words = channel.alternatives[0].words
        result_words = []
        
        for word in words:
            # Word overlaps with time range
            if (word.start <= end_time and word.end >= start_time):
                result_words.append(word)
        
        return result_words
    
    def validate_response_structure(self, response: Dict[str, Any]) -> bool:
        """
        Validate that a dictionary has the expected Deepgram response structure.
        
        Args:
            response: Response dictionary to validate
            
        Returns:
            True if structure is valid, False otherwise
        """
        try:
            # Check required top-level fields
            if not isinstance(response, dict):
                return False
            
            if "metadata" not in response or "results" not in response:
                return False
            
            # Check metadata structure
            metadata = response["metadata"]
            required_metadata_fields = ["request_id", "created", "duration", "channels"]
            for field in required_metadata_fields:
                if field not in metadata:
                    return False
            
            # Check results structure
            results = response["results"]
            if "channels" not in results or not isinstance(results["channels"], list):
                return False
            
            if not results["channels"]:
                return True  # Empty channels is valid
            
            # Check first channel structure
            channel = results["channels"][0]
            if "alternatives" not in channel or not isinstance(channel["alternatives"], list):
                return False
            
            if not channel["alternatives"]:
                return True  # Empty alternatives is valid
            
            # Check first alternative structure
            alternative = channel["alternatives"][0]
            if "transcript" not in alternative:
                return False
            
            # Words are optional but if present should be a list
            if "words" in alternative and not isinstance(alternative["words"], list):
                return False
            
            return True
            
        except (KeyError, TypeError, IndexError):
            return False