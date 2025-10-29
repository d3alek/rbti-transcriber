/**
 * ParagraphEditor Component
 * 
 * Individual paragraph editing interface with word-level highlighting,
 * confidence indicators, and speaker management.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  IconButton,
  Chip,
  Tooltip,
  Menu,
  MenuItem,

  useTheme
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  Person as PersonIcon,
  VolumeUp as VolumeUpIcon,

} from '@mui/icons-material';
import type { WordData, ParagraphEditorProps } from '../types/deepgram';

interface ParagraphEditorComponentProps extends ParagraphEditorProps {
  onWordClick?: (word: WordData) => void;
  onSpeakerChange?: (paragraphId: string, newSpeaker: string) => void;
}

const ParagraphEditor: React.FC<ParagraphEditorComponentProps> = ({
  paragraph,
  isEditing,
  currentPlaybackTime,
  onEdit,
  onStartEdit,
  onEndEdit,
  showConfidenceIndicators = true,
  onWordClick,
  onSpeakerChange
}) => {
  const theme = useTheme();
  const [editText, setEditText] = useState(paragraph.text);
  const [speakerMenuAnchor, setSpeakerMenuAnchor] = useState<null | HTMLElement>(null);
  const [customSpeakerName, setCustomSpeakerName] = useState<string>(`Speaker ${paragraph.speaker}`);
  const textFieldRef = useRef<HTMLInputElement>(null);

  // Update edit text when paragraph changes
  useEffect(() => {
    if (!isEditing) {
      setEditText(paragraph.text);
    }
  }, [paragraph.text, isEditing]);

  // Focus text field when editing starts
  useEffect(() => {
    if (isEditing && textFieldRef.current) {
      textFieldRef.current.focus();
    }
  }, [isEditing]);

  const handleStartEdit = useCallback(() => {
    onStartEdit(paragraph.id);
  }, [paragraph.id, onStartEdit]);

  const handleSaveEdit = useCallback(() => {
    if (editText.trim() !== paragraph.text) {
      onEdit(paragraph.id, editText.trim());
    }
    onEndEdit();
  }, [paragraph.id, editText, paragraph.text, onEdit, onEndEdit]);

  const handleCancelEdit = useCallback(() => {
    setEditText(paragraph.text);
    onEndEdit();
  }, [paragraph.text, onEndEdit]);

  const handleKeyPress = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && event.ctrlKey) {
      handleSaveEdit();
    } else if (event.key === 'Escape') {
      handleCancelEdit();
    }
  }, [handleSaveEdit, handleCancelEdit]);

  const handleWordClick = useCallback((word: WordData) => {
    onWordClick?.(word);
  }, [onWordClick]);

  const handleSpeakerMenuOpen = useCallback((event: React.MouseEvent<HTMLElement>) => {
    setSpeakerMenuAnchor(event.currentTarget);
  }, []);

  const handleSpeakerMenuClose = useCallback(() => {
    setSpeakerMenuAnchor(null);
  }, []);

  const handleSpeakerChange = useCallback((newSpeaker: string) => {
    setCustomSpeakerName(newSpeaker);
    onSpeakerChange?.(paragraph.id, newSpeaker);
    handleSpeakerMenuClose();
  }, [paragraph.id, onSpeakerChange, handleSpeakerMenuClose]);

  const getConfidenceColor = useCallback((confidence: number) => {
    if (confidence >= 0.9) return theme.palette.success.main;
    if (confidence >= 0.7) return theme.palette.warning.main;
    return theme.palette.error.main;
  }, [theme]);

  const getConfidenceLevel = useCallback((confidence: number) => {
    if (confidence >= 0.9) return 'High';
    if (confidence >= 0.7) return 'Medium';
    return 'Low';
  }, []);

  const isWordActive = useCallback((word: WordData) => {
    return currentPlaybackTime >= word.start && currentPlaybackTime <= word.end;
  }, [currentPlaybackTime]);

  const isWordInCurrentSentence = useCallback((word: WordData) => {
    // Find if any word in current sentence is active
    for (const sentence of paragraph.sentences) {
      const hasActiveWord = sentence.words.some(w => isWordActive(w));
      if (hasActiveWord && sentence.words.includes(word)) {
        return true;
      }
    }
    return false;
  }, [paragraph.sentences, isWordActive]);

  const renderWord = useCallback((word: WordData, index: number) => {
    const isActive = isWordActive(word);
    const isInActiveSentence = isWordInCurrentSentence(word);
    
    const wordStyle = {
      display: 'inline',
      cursor: 'pointer',
      padding: '2px 1px',
      borderRadius: '2px',
      backgroundColor: isActive 
        ? theme.palette.primary.main 
        : isInActiveSentence 
          ? theme.palette.primary.light + '20'
          : 'transparent',
      color: isActive ? theme.palette.primary.contrastText : 'inherit',
      borderBottom: showConfidenceIndicators 
        ? `2px solid ${getConfidenceColor(word.confidence)}` 
        : 'none',
      transition: 'all 0.2s ease-in-out',
      '&:hover': {
        backgroundColor: theme.palette.action.hover,
      }
    };

    return (
      <Tooltip
        key={`${word.index}-${index}`}
        title={showConfidenceIndicators ? 
          `Confidence: ${Math.round(word.confidence * 100)}% | ${word.start.toFixed(1)}s - ${word.end.toFixed(1)}s` : 
          `${word.start.toFixed(1)}s - ${word.end.toFixed(1)}s`
        }
        arrow
      >
        <span
          style={wordStyle}
          onClick={() => handleWordClick(word)}
        >
          {word.punctuated_word}
        </span>
      </Tooltip>
    );
  }, [
    isWordActive, 
    isWordInCurrentSentence, 
    showConfidenceIndicators, 
    getConfidenceColor, 
    handleWordClick, 
    theme
  ]);

  const renderText = useCallback(() => {
    if (paragraph.words.length === 0) {
      return <Typography variant="body1">{paragraph.text}</Typography>;
    }

    return (
      <Typography variant="body1" component="div" sx={{ lineHeight: 1.8 }}>
        {paragraph.words.map((word, index) => (
          <React.Fragment key={`${word.index}-${index}`}>
            {renderWord(word, index)}
            {index < paragraph.words.length - 1 && ' '}
          </React.Fragment>
        ))}
      </Typography>
    );
  }, [paragraph.words, paragraph.text, renderWord]);

  return (
    <Paper 
      elevation={1} 
      sx={{ 
        p: 2, 
        mb: 2, 
        border: isEditing ? `2px solid ${theme.palette.primary.main}` : '1px solid transparent',
        transition: 'border-color 0.2s ease-in-out'
      }}
    >
      {/* Header with speaker info and controls */}
      <Box display="flex" alignItems="center" justifyContent="space-between" mb={1}>
        <Box display="flex" alignItems="center" gap={1}>
          {/* Speaker Chip */}
          <Chip
            icon={<PersonIcon />}
            label={customSpeakerName}
            size="small"
            color="primary"
            variant="outlined"
            onClick={handleSpeakerMenuOpen}
            sx={{ cursor: 'pointer' }}
          />
          
          {/* Timing Info */}
          <Typography variant="caption" color="text.secondary">
            {Math.floor(paragraph.startTime / 60)}:{(paragraph.startTime % 60).toFixed(1).padStart(4, '0')} - 
            {Math.floor(paragraph.endTime / 60)}:{(paragraph.endTime % 60).toFixed(1).padStart(4, '0')}
          </Typography>

          {/* Confidence Indicator */}
          {showConfidenceIndicators && (
            <Chip
              label={`${Math.round(paragraph.confidence * 100)}% ${getConfidenceLevel(paragraph.confidence)}`}
              size="small"
              sx={{ 
                backgroundColor: getConfidenceColor(paragraph.confidence) + '20',
                color: getConfidenceColor(paragraph.confidence),
                fontWeight: 'bold'
              }}
            />
          )}
        </Box>

        {/* Action Buttons */}
        <Box display="flex" alignItems="center" gap={1}>
          {!isEditing ? (
            <>
              <Tooltip title="Play from here">
                <IconButton 
                  size="small" 
                  onClick={() => onWordClick?.(paragraph.words[0])}
                  disabled={paragraph.words.length === 0}
                >
                  <VolumeUpIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Edit paragraph">
                <IconButton size="small" onClick={handleStartEdit}>
                  <EditIcon />
                </IconButton>
              </Tooltip>
            </>
          ) : (
            <>
              <Tooltip title="Save changes (Ctrl+Enter)">
                <IconButton size="small" onClick={handleSaveEdit} color="primary">
                  <SaveIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title="Cancel editing (Esc)">
                <IconButton size="small" onClick={handleCancelEdit}>
                  <CancelIcon />
                </IconButton>
              </Tooltip>
            </>
          )}
        </Box>
      </Box>

      {/* Content */}
      {isEditing ? (
        <TextField
          ref={textFieldRef}
          fullWidth
          multiline
          minRows={2}
          maxRows={8}
          value={editText}
          onChange={(e) => setEditText(e.target.value)}
          onKeyDown={handleKeyPress}
          variant="outlined"
          placeholder="Enter paragraph text..."
          sx={{ mt: 1 }}
        />
      ) : (
        <Box sx={{ mt: 1 }}>
          {renderText()}
        </Box>
      )}

      {/* Speaker Menu */}
      <Menu
        anchorEl={speakerMenuAnchor}
        open={Boolean(speakerMenuAnchor)}
        onClose={handleSpeakerMenuClose}
      >
        <MenuItem onClick={() => handleSpeakerChange('Speaker 0')}>Speaker 0</MenuItem>
        <MenuItem onClick={() => handleSpeakerChange('Speaker 1')}>Speaker 1</MenuItem>
        <MenuItem onClick={() => handleSpeakerChange('Speaker 2')}>Speaker 2</MenuItem>
        <MenuItem onClick={() => handleSpeakerChange('Narrator')}>Narrator</MenuItem>
        <MenuItem onClick={() => handleSpeakerChange('Interviewer')}>Interviewer</MenuItem>
        <MenuItem onClick={() => handleSpeakerChange('Guest')}>Guest</MenuItem>
        <MenuItem 
          onClick={() => {
            const customName = prompt('Enter custom speaker name:', customSpeakerName);
            if (customName) {
              handleSpeakerChange(customName);
            }
          }}
        >
          Custom Name...
        </MenuItem>
      </Menu>
    </Paper>
  );
};

export default ParagraphEditor;