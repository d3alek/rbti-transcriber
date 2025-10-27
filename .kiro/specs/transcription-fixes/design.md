# Design Document

## Overview

This design addresses critical bugs in the transcription system that prevent proper execution and timestamp display. The fixes focus on import compatibility, timestamp formatting, and duration extraction.

## Architecture

The fixes will be implemented across three main components:
1. **Config Module**: Add backward compatibility function
2. **HTML Formatter**: Add missing timestamp formatting method
3. **Deepgram Client**: Improve duration extraction and response parsing

## Components and Interfaces

### Config Module Enhancement
- Add `load_config()` function that returns a ConfigManager instance
- Maintain existing ConfigManager class functionality
- Ensure backward compatibility with existing code

### HTML Formatter Fixes
- Add `_format_timestamp(seconds: float) -> str` method
- Fix timestamp display logic in speaker paragraphs
- Ensure duration formatting works correctly

### Deepgram Client Improvements
- Enhance `_parse_transcription_result()` to better extract duration
- Add fallback duration calculation from segment end times
- Improve handling of different Deepgram response formats

## Data Models

### Timestamp Formatting
```python
def _format_timestamp(self, seconds: float) -> str:
    """Format timestamp as MM:SS or HH:MM:SS"""
    # Convert float seconds to readable format
```

### Duration Extraction
```python
# Priority order for duration extraction:
# 1. metadata.duration (primary)
# 2. calculated from last segment end_time (fallback)
# 3. sum of all segment durations (last resort)
```

## Error Handling

- Import errors: Provide clear error messages if config cannot be loaded
- Missing timestamps: Gracefully handle segments without timing data
- Duration calculation: Use fallback methods if primary duration source fails

## Testing Strategy

- Test CLI execution without import errors
- Verify HTML output contains proper timestamps and duration
- Test with various Deepgram response formats
- Validate timestamp formatting edge cases