#!/usr/bin/env python3
"""
Glossary Term Extractor for RBTI Seminars

Extracts ~1000 glossary terms from transcribed RBTI seminar text.
Aims for 50% single words, 50% 2-3 word phrases, organized by categories.

Usage:
    python extract_glossary.py input_transcript.txt output_glossary.txt
"""

import sys
import re
import nltk
from collections import Counter, defaultdict
from pathlib import Path
from typing import List, Dict, Set, Tuple
import string

# Download required NLTK data
try:
    nltk.data.find('tokenizers/punkt_tab')
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
    nltk.data.find('corpora/stopwords')
except LookupError:
    print("Downloading required NLTK data...")
    nltk.download('punkt_tab', quiet=True)
    nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    nltk.download('stopwords', quiet=True)

from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from nltk.tag import pos_tag


class RBTIGlossaryExtractor:
    """Extracts RBTI-specific glossary terms from transcription text."""
    
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.stop_words.update(['um', 'uh', 'ah', 'okay', 'yeah', 'yes', 'no', 'well', 'so', 'like'])
        
        # RBTI-specific seed terms for context detection
        self.rbti_seeds = {
            'rbti', 'reams', 'carey', 'biological', 'ionization', 'ph', 'urine', 'saliva',
            'conductivity', 'brix', 'refractometer', 'energy', 'mineral', 'calcium',
            'magnesium', 'potassium', 'phosphorus', 'zone', 'range', 'reading'
        }
        
        # Common English words to exclude even if frequent
        self.common_excludes = {
            'people', 'person', 'time', 'way', 'day', 'year', 'thing', 'man', 'woman',
            'life', 'work', 'world', 'hand', 'part', 'place', 'case', 'point', 'group',
            'problem', 'fact', 'question', 'right', 'water', 'food', 'money', 'story',
            'example', 'lot', 'state', 'business', 'night', 'area', 'book', 'eye',
            'job', 'word', 'side', 'kind', 'head', 'house', 'service', 'friend',
            'father', 'power', 'hour', 'game', 'line', 'end', 'member', 'law',
            'car', 'city', 'community', 'name', 'president', 'team', 'minute',
            'idea', 'kid', 'body', 'information', 'back', 'parent', 'face', 'others',
            'level', 'office', 'door', 'health', 'person', 'art', 'war', 'history'
        }
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize the input text."""
        # Remove speaker labels and timestamps
        text = re.sub(r'Speaker \d+:', '', text)
        text = re.sub(r'\[\d+:\d+\]', '', text)
        text = re.sub(r'\*\*\[\d+:\d+ - \d+:\d+\]\*\*', '', text)
        
        # Remove markdown formatting
        text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # Bold
        text = re.sub(r'\*([^*]+)\*', r'\1', text)      # Italic
        text = re.sub(r'`([^`]+)`', r'\1', text)        # Code
        text = re.sub(r'#+\s*', '', text)               # Headers
        text = re.sub(r'>\s*', '', text)                # Blockquotes
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_single_words(self, text: str) -> List[Tuple[str, float]]:
        """Extract and score single-word terms."""
        words = word_tokenize(text.lower())
        
        # Filter words
        filtered_words = []
        for word in words:
            if (len(word) >= 3 and 
                word.isalpha() and 
                word not in self.stop_words and 
                word not in self.common_excludes):
                filtered_words.append(word)
        
        # Count frequency
        word_freq = Counter(filtered_words)
        
        # Score words
        scored_words = []
        for word, freq in word_freq.items():
            score = self._score_single_word(word, freq, text)
            if score > 0:
                scored_words.append((word, score))
        
        return sorted(scored_words, key=lambda x: x[1], reverse=True)
    
    def extract_phrases(self, text: str) -> List[Tuple[str, float]]:
        """Extract and score 2-3 word phrases."""
        sentences = sent_tokenize(text)
        phrases = []
        
        for sentence in sentences:
            words = word_tokenize(sentence.lower())
            tagged = pos_tag(words)
            
            # Extract 2-word phrases
            for i in range(len(tagged) - 1):
                phrase = self._extract_phrase(tagged[i:i+2])
                if phrase:
                    phrases.append(phrase)
            
            # Extract 3-word phrases
            for i in range(len(tagged) - 2):
                phrase = self._extract_phrase(tagged[i:i+3])
                if phrase:
                    phrases.append(phrase)
        
        # Count and score phrases
        phrase_freq = Counter(phrases)
        scored_phrases = []
        
        for phrase, freq in phrase_freq.items():
            score = self._score_phrase(phrase, freq, text)
            if score > 0:
                scored_phrases.append((phrase, score))
        
        return sorted(scored_phrases, key=lambda x: x[1], reverse=True)
    
    def _extract_phrase(self, tagged_words: List[Tuple[str, str]]) -> str:
        """Extract valid phrase from tagged words."""
        words = [word.lower() for word, tag in tagged_words]
        tags = [tag for word, tag in tagged_words]
        
        # Skip if contains stop words or punctuation
        if any(word in self.stop_words or not word.isalpha() for word in words):
            return None
        
        # Skip if all words are too common
        if all(word in self.common_excludes for word in words):
            return None
        
        # Prefer phrases with nouns
        if any(tag.startswith('NN') for tag in tags):
            return ' '.join(words)
        
        # Accept phrases with adjectives + nouns
        if len(words) == 2 and tags[0].startswith('JJ') and tags[1].startswith('NN'):
            return ' '.join(words)
        
        return None
    
    def _score_single_word(self, word: str, freq: int, text: str) -> float:
        """Score a single word based on RBTI relevance."""
        score = freq * 1.0
        
        # Boost RBTI-related terms
        if word in self.rbti_seeds:
            score *= 3.0
        
        # Boost technical terms
        if any(pattern in word for pattern in ['ph', 'ion', 'bio', 'mineral', 'calc', 'magn']):
            score *= 2.0
        
        # Boost capitalized terms in original text
        if re.search(rf'\b{word.capitalize()}\b', text):
            score *= 1.5
        
        # Boost measurement-related terms
        if any(context in text.lower() for context in [f'{word} reading', f'{word} level', f'{word} test']):
            score *= 1.5
        
        # Penalize very short or very long words
        if len(word) < 4:
            score *= 0.7
        elif len(word) > 12:
            score *= 0.8
        
        return score
    
    def _score_phrase(self, phrase: str, freq: int, text: str) -> float:
        """Score a phrase based on RBTI relevance."""
        score = freq * 2.0  # Phrases get base boost
        
        words = phrase.split()
        
        # Boost if contains RBTI seed terms
        if any(word in self.rbti_seeds for word in words):
            score *= 2.5
        
        # Boost measurement phrases
        if any(word in ['ph', 'reading', 'level', 'test', 'range', 'zone'] for word in words):
            score *= 2.0
        
        # Boost technical combinations
        technical_patterns = [
            'urine ph', 'saliva ph', 'energy level', 'mineral deficiency',
            'biological age', 'perfect range', 'conductivity reading',
            'brix reading', 'calcium level', 'magnesium level'
        ]
        if phrase in technical_patterns:
            score *= 3.0
        
        # Boost proper noun phrases
        if any(word[0].isupper() for word in phrase.split()):
            score *= 1.5
        
        return score
    
    def categorize_terms(self, terms: List[str]) -> Dict[str, List[str]]:
        """Categorize terms into RBTI-relevant groups."""
        categories = {
            'core_concepts': [],
            'measurements': [],
            'body_systems': [],
            'minerals': [],
            'ranges_zones': [],
            'equipment': [],
            'names_places': [],
            'health_conditions': [],
            'general_terms': []
        }
        
        for term in terms:
            term_lower = term.lower()
            categorized = False
            
            # Core RBTI concepts
            if any(word in term_lower for word in ['rbti', 'reams', 'biological', 'ionization', 'theory']):
                categories['core_concepts'].append(term)
                categorized = True
            
            # Measurements and tests
            elif any(word in term_lower for word in ['ph', 'conductivity', 'brix', 'reading', 'test', 'level', 'measurement']):
                categories['measurements'].append(term)
                categorized = True
            
            # Body systems
            elif any(word in term_lower for word in ['urine', 'saliva', 'blood', 'liver', 'kidney', 'cellular', 'body']):
                categories['body_systems'].append(term)
                categorized = True
            
            # Minerals and nutrients
            elif any(word in term_lower for word in ['calcium', 'magnesium', 'potassium', 'phosphorus', 'mineral', 'vitamin', 'iron', 'manganese']):
                categories['minerals'].append(term)
                categorized = True
            
            # Ranges and zones
            elif any(word in term_lower for word in ['range', 'zone', 'perfect', 'ideal', 'normal', 'optimal']):
                categories['ranges_zones'].append(term)
                categorized = True
            
            # Equipment and tools
            elif any(word in term_lower for word in ['refractometer', 'meter', 'machine', 'equipment', 'instrument']):
                categories['equipment'].append(term)
                categorized = True
            
            # Names and places
            elif any(word in term_lower for word in ['carey', 'reams', 'institute', 'doctor', 'dr']):
                categories['names_places'].append(term)
                categorized = True
            
            # Health conditions
            elif any(word in term_lower for word in ['disease', 'condition', 'deficiency', 'problem', 'issue', 'symptom']):
                categories['health_conditions'].append(term)
                categorized = True
            
            # General terms
            if not categorized:
                categories['general_terms'].append(term)
        
        return categories
    
    def extract_glossary(self, text: str, target_count: int = 1000) -> List[str]:
        """Extract glossary terms from text."""
        print("Cleaning text...")
        clean_text = self.clean_text(text)
        
        print("Extracting single words...")
        single_words = self.extract_single_words(clean_text)
        
        print("Extracting phrases...")
        phrases = self.extract_phrases(clean_text)
        
        # Target: 50% single words, 50% phrases
        target_singles = target_count // 2
        target_phrases = target_count - target_singles
        
        # Select top terms
        selected_singles = [word for word, score in single_words[:target_singles]]
        selected_phrases = [phrase for phrase, score in phrases[:target_phrases]]
        
        # Combine and deduplicate
        all_terms = selected_singles + selected_phrases
        unique_terms = []
        seen = set()
        
        for term in all_terms:
            if term.lower() not in seen:
                unique_terms.append(term)
                seen.add(term.lower())
        
        return unique_terms[:target_count]
    
    def write_glossary(self, terms: List[str], output_path: Path):
        """Write glossary to file with categories."""
        categories = self.categorize_terms(terms)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# RBTI Glossary - Extracted from Transcription\n")
            f.write("# One term per line, lines starting with # are comments\n\n")
            
            category_headers = {
                'core_concepts': '# Core RBTI Concepts',
                'measurements': '# Measurements and Tests',
                'body_systems': '# Body Systems and Functions',
                'minerals': '# Minerals and Nutrients',
                'ranges_zones': '# Ranges and Zones',
                'equipment': '# Equipment and Tools',
                'names_places': '# Names and Places',
                'health_conditions': '# Health Conditions',
                'general_terms': '# General Terms'
            }
            
            for category, header in category_headers.items():
                if categories[category]:
                    f.write(f"{header}\n")
                    for term in sorted(categories[category]):
                        f.write(f"{term}\n")
                    f.write("\n")
        
        print(f"Glossary written to {output_path}")
        print(f"Total terms: {len(terms)}")
        for category, header in category_headers.items():
            if categories[category]:
                print(f"  {header}: {len(categories[category])} terms")


def main():
    if len(sys.argv) != 3:
        print("Usage: python extract_glossary.py input_transcript.txt output_glossary.txt")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    output_file = Path(sys.argv[2])
    
    if not input_file.exists():
        print(f"Error: Input file {input_file} does not exist")
        sys.exit(1)
    
    print(f"Reading transcript from {input_file}...")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            text = f.read()
    except Exception as e:
        print(f"Error reading input file: {e}")
        sys.exit(1)
    
    print("Extracting glossary terms...")
    extractor = RBTIGlossaryExtractor()
    terms = extractor.extract_glossary(text, target_count=1000)
    
    print(f"Writing glossary to {output_file}...")
    extractor.write_glossary(terms, output_file)
    
    print("Done!")


if __name__ == "__main__":
    main()