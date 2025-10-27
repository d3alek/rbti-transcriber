/**
 * Enhanced Transcript Editor with audio playback integration.
 */

import React, { useState, useRef } from 'react';
import {
  Box,
  Paper,
  IconButton,
  Typography,
  Tooltip,
  Chip,
  TextField,
  Button,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Edit as EditIcon,
  Check as SaveIcon,
  Close as CancelIcon,
} from '@mui/icons-material';
import type { TranscriptionData, SpeakerSegment } from '../types';

interface TranscriptEditorProps {
  transcriptionData: TranscriptionData;
  onTranscriptChange: (updatedData: TranscriptionData) => void;
  currentTime: number;
  onSeek: (time: number) => void;
  onPlaySegment: (startTime: number, endTime: number) => void;
  isPlaying: boolean;
}

export const BBCTranscriptEditor: React.FC<TranscriptEditorProps> = ({
  transcriptionData,
  onTranscriptChange,
  currentTime,
  onSeek,
  onPlaySegment,
  isPlaying,
}) => {
  const [editingSegment, setEditingSegment] = useState<number | null>(null);
  const [editText, setEditText] = useState('');
  const textareaRefs = useRef<(HTMLTextAreaElement | null)[]>([]);

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  const handleEditStart = (index: number, text: string) => {
    setEditingSegment(index);
    setEditText(text);
    // Focus the textarea after a brief delay to ensure it's rendered
    setTimeout(() => {
      textareaRefs.current[index]?.focus();
    }, 100);
  };

  const handleEditSave = (index: number) => {
    const updatedSegments = [...transcriptionData.speakers];
    updatedSegments[index] = { ...updatedSegments[index], text: editText };
    const updatedData = {
      ...transcriptionData,
      speakers: updatedSegments,
      text: updatedSegments.map(s => s.text).join(' '),
    };
    onTranscriptChange(updatedData);
    setEditingSegment(null);
    setEditText('');
  };

  const handleEditCancel = () => {
    setEditingSegment(null);
    setEditText('');
  };

  const isCurrentSegment = (segment: SpeakerSegment): boolean => {
    return currentTime >= segment.start_time && currentTime <= segment.end_time;
  };

  return (
    <Box>
      {transcriptionData.speakers.map((segment, index) => {
        const isCurrent = isCurrentSegment(segment);
        const isEditing = editingSegment === index;
        
        return (
          <Paper
            key={index}
            sx={{
              mb: 2,
              p: 2,
              border: isCurrent ? '2px solid #1976d2' : '1px solid #e0e0e0',
              borderRadius: 2,
              bgcolor: isCurrent ? 'rgba(25, 118, 210, 0.04)' : 'white',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                boxShadow: 2,
              },
            }}
          >
            {/* Segment Header */}
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 2, gap: 1 }}>
              {/* Speaker Label */}
              <Chip
                label={segment.speaker}
                size="small"
                color={isCurrent ? 'primary' : 'default'}
                sx={{ fontWeight: 'bold' }}
              />

              {/* Time Range */}
              <Tooltip title="Click to seek to this time">
                <Chip
                  label={`${formatTime(segment.start_time)} - ${formatTime(segment.end_time)}`}
                  size="small"
                  variant="outlined"
                  onClick={() => onSeek(segment.start_time)}
                  sx={{
                    cursor: 'pointer',
                    '&:hover': { bgcolor: 'action.hover' },
                  }}
                />
              </Tooltip>

              {/* Confidence Score */}
              <Chip
                label={`${Math.round(segment.confidence * 100)}%`}
                size="small"
                variant="outlined"
                color={segment.confidence > 0.8 ? 'success' : segment.confidence > 0.6 ? 'warning' : 'error'}
              />

              {/* Play Segment Button */}
              <Tooltip title="Play this segment">
                <IconButton
                  size="small"
                  color="primary"
                  onClick={() => onPlaySegment(segment.start_time, segment.end_time)}
                  sx={{
                    bgcolor: 'primary.light',
                    color: 'white',
                    '&:hover': { bgcolor: 'primary.main' },
                  }}
                >
                  <PlayIcon />
                </IconButton>
              </Tooltip>

              {/* Edit Button */}
              {!isEditing && (
                <Tooltip title="Edit this segment">
                  <IconButton
                    size="small"
                    onClick={() => handleEditStart(index, segment.text)}
                  >
                    <EditIcon />
                  </IconButton>
                </Tooltip>
              )}

              {/* Save/Cancel Buttons (when editing) */}
              {isEditing && (
                <Box sx={{ display: 'flex', gap: 0.5 }}>
                  <Tooltip title="Save changes">
                    <IconButton
                      size="small"
                      color="success"
                      onClick={() => handleEditSave(index)}
                    >
                      <SaveIcon />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Cancel editing">
                    <IconButton
                      size="small"
                      color="error"
                      onClick={handleEditCancel}
                    >
                      <CancelIcon />
                    </IconButton>
                  </Tooltip>
                </Box>
              )}
            </Box>

            {/* Transcript Text */}
            <Box sx={{ position: 'relative' }}>
              {isEditing ? (
                <TextField
                  multiline
                  fullWidth
                  value={editText}
                  onChange={(e) => setEditText(e.target.value)}
                  inputRef={(el) => (textareaRefs.current[index] = el)}
                  variant="outlined"
                  minRows={3}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      fontSize: '1rem',
                      lineHeight: 1.6,
                    },
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && e.ctrlKey) {
                      handleEditSave(index);
                    } else if (e.key === 'Escape') {
                      handleEditCancel();
                    }
                  }}
                />
              ) : (
                <Typography
                  variant="body1"
                  sx={{
                    fontSize: '1rem',
                    lineHeight: 1.6,
                    cursor: 'pointer',
                    p: 1,
                    borderRadius: 1,
                    '&:hover': {
                      bgcolor: 'action.hover',
                    },
                  }}
                  onClick={() => handleEditStart(index, segment.text)}
                >
                  {segment.text}
                </Typography>
              )}
            </Box>

            {/* Keyboard Shortcuts Help (when editing) */}
            {isEditing && (
              <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                Press Ctrl+Enter to save, Escape to cancel
              </Typography>
            )}
          </Paper>
        );
      })}
    </Box>
  );
};