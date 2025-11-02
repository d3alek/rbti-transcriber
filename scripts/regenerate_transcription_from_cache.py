#!/usr/bin/env python3
"""
Regenerate transcription JSON file from Deepgram raw cache.
This applies the latest paragraph marker logic without re-transcribing.
"""

import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import from src
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.transcription_service import TranscriptionService
from api.config import Settings
from src.utils.file_scanner import OutputDirectoryManager


def regenerate_from_cache(audio_file_path: Path, settings: Settings = None):
    """Regenerate transcription JSON from raw Deepgram cache."""
    if not audio_file_path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file_path}")
    
    # Initialize transcription service
    if settings is None:
        settings = Settings()
    service = TranscriptionService(settings)
    
    # Get output manager
    output_manager = OutputDirectoryManager(audio_file_path)
    transcription_path = output_manager.get_transcription_path()
    cache_path = output_manager.transcriptions_dir / "cache" / f"{audio_file_path.stem}_raw.json"
    
    if not cache_path.exists():
        raise FileNotFoundError(
            f"Cache file not found: {cache_path}\n"
            f"Expected cache file at: {cache_path}"
        )
    
    print(f"📂 Loading cache file: {cache_path}")
    
    # Load raw response from cache
    with open(cache_path, 'r', encoding='utf-8') as f:
        cache_data = json.load(f)
    
    raw_response = cache_data.get('raw_response')
    if not raw_response:
        raise ValueError(f"Cache file does not contain raw_response: {cache_path}")
    
    print(f"🔄 Converting to RichWordsTranscript format...")
    
    # Convert using the transcription service's conversion method
    rich_words_transcript = service._convert_to_rich_words_transcript(raw_response)
    
    # Preserve existing corrections and metadata if they exist
    existing_transcription_path = transcription_path
    if existing_transcription_path.exists():
        try:
            with open(existing_transcription_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            # Preserve corrections if they exist
            if 'corrections' in existing_data:
                rich_words_transcript['corrections'] = existing_data['corrections']
                print(f"✅ Preserved existing corrections")
            # Preserve _metadata if it exists (but update timestamp)
            if '_metadata' in existing_data:
                rich_words_transcript['_metadata'] = existing_data['_metadata']
                rich_words_transcript['_metadata']['regenerated_at'] = datetime.now().isoformat()
        except Exception as e:
            print(f"⚠️  Could not preserve existing data: {e}")
    
    # Ensure _metadata exists
    if '_metadata' not in rich_words_transcript:
        rich_words_transcript['_metadata'] = {
            'audio_file': str(audio_file_path),
            'service': 'deepgram',
            'regenerated_at': datetime.now().isoformat(),
            'raw_response_cache': str(cache_path)
        }
    
    # Ensure output directory exists
    transcription_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Save regenerated transcription
    print(f"💾 Saving transcription to: {transcription_path}")
    with open(transcription_path, 'w', encoding='utf-8') as f:
        json.dump(rich_words_transcript, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Successfully regenerated transcription JSON")
    print(f"   Words: {len(rich_words_transcript.get('words', []))}")
    
    # Count paragraph boundaries
    para_starts = sum(1 for w in rich_words_transcript.get('words', []) if w.get('paragraph_start'))
    para_ends = sum(1 for w in rich_words_transcript.get('words', []) if w.get('paragraph_end'))
    print(f"   Paragraph starts: {para_starts}, Paragraph ends: {para_ends}")
    
    return transcription_path


def main():
    parser = argparse.ArgumentParser(
        description="Regenerate transcription JSON from Deepgram raw cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Regenerate a specific file
  python scripts/regenerate_transcription_from_cache.py test_audio/RBTI-Animal-Husbandry-T01.mp3
  
  # Regenerate all files in a directory
  python scripts/regenerate_transcription_from_cache.py test_audio/*.mp3
        """
    )
    parser.add_argument(
        'audio_files',
        nargs='+',
        type=Path,
        help='Audio file(s) to regenerate transcription for'
    )
    parser.add_argument(
        '--audio-dir',
        type=Path,
        help='Base audio directory (default: from settings)'
    )
    
    args = parser.parse_args()
    
    # Initialize settings
    settings = Settings()
    if args.audio_dir:
        settings.audio_directory = args.audio_dir
    
    # Process each file
    success_count = 0
    error_count = 0
    
    for audio_file in args.audio_files:
        try:
            print(f"\n{'='*60}")
            print(f"Processing: {audio_file}")
            print(f"{'='*60}")
            regenerate_from_cache(audio_file, settings)
            success_count += 1
        except Exception as e:
            print(f"❌ Error processing {audio_file}: {e}")
            error_count += 1
    
    print(f"\n{'='*60}")
    print(f"Summary: {success_count} succeeded, {error_count} failed")
    print(f"{'='*60}")


if __name__ == '__main__':
    main()

