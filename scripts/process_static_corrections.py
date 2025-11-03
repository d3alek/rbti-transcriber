#!/usr/bin/env python3
"""
Process corrections from static HTML app back into backend format.

Takes a JSON file downloaded from the static transcript editor and converts it
to the RichWordsTranscript format that the backend uses.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime


def extract_words_from_draftjs(draftjs_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract words from DraftJS format.
    
    DraftJS format has:
    - blocks: array of paragraph blocks
      - text: the paragraph text
      - data: metadata including words array
      - entityRanges: array mapping text positions to entities
    - entityMap: maps entity keys to word data
    """
    blocks = draftjs_data.get('blocks', [])
    entity_map = draftjs_data.get('entityMap', {})
    
    all_words = []
    
    for block in blocks:
        block_data = block.get('data', {})
        block_words = block_data.get('words', [])
        
        if block_words:
            # Add words from this block
            for i, word in enumerate(block_words):
                word_copy = word.copy()
                # Set paragraph_start/paragraph_end based on position in block
                word_copy['paragraph_start'] = (i == 0)
                word_copy['paragraph_end'] = (i == len(block_words) - 1)
                all_words.append(word_copy)
    
    return all_words


def extract_speaker_names_from_draftjs(draftjs_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract speaker names from DraftJS format.
    Speaker names are stored in block.data.speaker as display labels like "Speaker 0" or custom names.
    We need to map these back to numeric indices.
    
    Returns a mapping of display name -> numeric index.
    """
    blocks = draftjs_data.get('blocks', [])
    speaker_name_to_index = {}
    
    for block in blocks:
        block_data = block.get('data', {})
        display_name = block_data.get('speaker')
        
        if display_name:
            # Get the speaker index from the first word in the block
            block_words = block_data.get('words', [])
            if block_words and 'speaker' in block_words[0]:
                speaker_index = block_words[0]['speaker']
                if display_name not in speaker_name_to_index:
                    speaker_name_to_index[display_name] = speaker_index
    
    return speaker_name_to_index


def process_static_corrections(input_file: Path, output_file: Path, original_file: Path):
    """
    Process corrections from static app into backend format.
    
    Args:
        input_file: DraftJS JSON file from static app
        output_file: Path to save the corrected RichWordsTranscript
        original_file: Original transcript to merge corrections into
    """
    print(f"📂 Loading original transcript from: {original_file}")
    with open(original_file, 'r') as f:
        original_data = json.load(f)
    
    print(f"📂 Loading corrections from: {input_file}")
    with open(input_file, 'r') as f:
        draftjs_data = json.load(f)
    
    # Extract words from DraftJS format
    print("🔄 Extracting words from DraftJS format...")
    corrected_words = extract_words_from_draftjs(draftjs_data)
    print(f"   Found {len(corrected_words)} words")
    
    # Extract speaker names
    print("🎤 Extracting speaker names...")
    speaker_mapping = extract_speaker_names_from_draftjs(draftjs_data)
    print(f"   Speaker mapping: {speaker_mapping}")
    
    # Build speaker_names dict (only custom names, not "Speaker X" format)
    speaker_names = {}
    for display_name, speaker_index in speaker_mapping.items():
        if not display_name.startswith('Speaker ') or not display_name.split(' ')[1].isdigit():
            speaker_names[str(speaker_index)] = display_name
    
    # Merge corrections into original data
    print("🔧 Merging corrections...")
    original_words = original_data.get('words', [])
    
    if len(corrected_words) != len(original_words):
        print(f"⚠️  Warning: Word count mismatch! Original: {len(original_words)}, Corrected: {len(corrected_words)}")
    
    # Update words with corrections
    correction_count = 0
    for i, corrected_word in enumerate(corrected_words):
        if i >= len(original_words):
            break
        
        original_word = original_words[i]
        
        # Check if word was modified
        word_changed = corrected_word.get('word') != original_word.get('word')
        punct_changed = corrected_word.get('punct') != original_word.get('punctuated_word')
        
        if word_changed or punct_changed:
            correction_count += 1
            
            # Mark as corrected and preserve original values
            original_word['corrected'] = True
            original_word['original_word'] = original_word.get('original_word', original_word.get('word'))
            original_word['original_punct'] = original_word.get('original_punct', original_word.get('punctuated_word'))
            
            # Update with corrected values
            original_word['word'] = corrected_word.get('word')
            original_word['punctuated_word'] = corrected_word.get('punct')
    
    print(f"   Found {correction_count} word corrections")
    
    # Update corrections metadata
    corrections_version = original_data.get('corrections', {}).get('version', 0) + 1
    
    corrected_output = {
        **original_data,
        'words': original_words,
        'corrections': {
            'version': corrections_version,
            'timestamp': datetime.now().isoformat(),
            'speaker_names': speaker_names if speaker_names else None
        }
    }
    
    # Remove None from speaker_names if empty
    if not speaker_names:
        corrected_output['corrections'].pop('speaker_names', None)
    
    # Save output
    print(f"💾 Saving corrected transcript to: {output_file}")
    with open(output_file, 'w') as f:
        json.dump(corrected_output, f, indent=2)
    
    print("✅ Done!")
    print(f"   Corrections applied: {correction_count} words")
    if speaker_names:
        print(f"   Speaker names updated: {speaker_names}")


def main():
    """Main entry point."""
    if len(sys.argv) < 3:
        print("Usage: process_static_corrections.py <input_draftjs.json> <original_transcript.json> [output.json]")
        print()
        print("Converts corrections from static app into backend RichWordsTranscript format.")
        print()
        print("Arguments:")
        print("  input_draftjs.json: JSON file downloaded from static transcript editor")
        print("  original_transcript.json: Original transcript file to merge corrections into")
        print("  output.json: (optional) Output file path (default: appends '_corrected.json' to original)")
        sys.exit(1)
    
    input_file = Path(sys.argv[1])
    original_file = Path(sys.argv[2])
    
    if len(sys.argv) >= 4:
        output_file = Path(sys.argv[3])
    else:
        # Default: append '_corrected' to original filename
        output_file = original_file.with_name(f"{original_file.stem}_corrected{original_file.suffix}")
    
    if not input_file.exists():
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)
    
    if not original_file.exists():
        print(f"❌ Error: Original file not found: {original_file}")
        sys.exit(1)
    
    process_static_corrections(input_file, output_file, original_file)


if __name__ == '__main__':
    main()

