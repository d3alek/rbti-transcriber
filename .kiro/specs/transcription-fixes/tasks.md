# Implementation Plan

- [x] 1. Fix config module import compatibility
  - Add load_config function to src/utils/config.py for backward compatibility
  - Ensure function returns properly configured ConfigManager instance
  - _Requirements: 1.1, 1.2_

- [x] 2. Add missing timestamp formatting method to HTML formatter
  - Implement _format_timestamp method in HTMLFormatter class
  - Format timestamps as MM:SS or HH:MM:SS based on duration
  - _Requirements: 2.4, 1.3_

- [x] 3. Improve duration extraction in Deepgram client
  - Enhance _parse_transcription_result to extract duration from metadata
  - Add fallback calculation using last segment end_time
  - Handle edge cases where no timing data is available
  - _Requirements: 3.1, 3.3, 2.1_

- [x] 4. Fix timestamp display logic in HTML formatter
  - Ensure timestamp markers appear at correct intervals
  - Fix the timestamp display logic in _build_transcript_section
  - Verify timestamps are properly formatted and displayed
  - _Requirements: 2.2, 2.3_