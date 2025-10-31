import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Tooltip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@material-ui/core';
import {
  Edit,
  Undo,
  ExpandMore,
  Person,
  RecordVoiceOver,
  History,
} from '@material-ui/icons';
import { ReactTranscriptEditorData } from '../../types/transcriptEditor';

interface ManualEditManagerProps {
  transcriptData: ReactTranscriptEditorData;
  onTranscriptUpdate: (updatedData: ReactTranscriptEditorData) => void;
  currentTime: number;
}

interface WordEditDialog {
  open: boolean;
  wordIndex: number | null;
  originalWord: string;
  editedWord: string;
  originalPunct: string;
  editedPunct: string;
}

interface SpeakerEditDialog {
  open: boolean;
  speakerIndex: number | null;
  speakerName: string;
}

export const ManualEditManager: React.FC<ManualEditManagerProps> = ({
  transcriptData,
  onTranscriptUpdate,
  currentTime,
}) => {
  const [wordEditDialog, setWordEditDialog] = useState<WordEditDialog>({
    open: false,
    wordIndex: null,
    originalWord: '',
    editedWord: '',
    originalPunct: '',
    editedPunct: '',
  });

  const [speakerEditDialog, setSpeakerEditDialog] = useState<SpeakerEditDialog>({
    open: false,
    speakerIndex: null,
    speakerName: '',
  });

  // Get corrected words for display
  const correctedWords = useMemo(() => {
    return transcriptData.words.filter(word => word.corrected);
  }, [transcriptData.words]);

  // Get unique speakers
  const speakers = useMemo(() => {
    const speakerSet = new Set(transcriptData.words.map(word => word.speaker));
    return Array.from(speakerSet).sort((a, b) => a - b);
  }, [transcriptData.words]);

  // Get current word being played
  const currentWord = useMemo(() => {
    return transcriptData.words.find(word => 
      currentTime >= word.start && currentTime <= word.end
    );
  }, [transcriptData.words, currentTime]);

  // Handle word edit dialog open
  const handleEditWord = useCallback((wordIndex: number) => {
    const word = transcriptData.words[wordIndex];
    setWordEditDialog({
      open: true,
      wordIndex,
      originalWord: word.original_word || word.word,
      editedWord: word.word,
      originalPunct: word.original_punct || word.punct,
      editedPunct: word.punct,
    });
  }, [transcriptData.words]);

  // Handle word edit save
  const handleSaveWordEdit = useCallback(() => {
    if (wordEditDialog.wordIndex === null) return;

    const updatedWords = [...transcriptData.words];
    const word = updatedWords[wordEditDialog.wordIndex];
    
    // Check if changes were made
    const wordChanged = wordEditDialog.editedWord !== (word.original_word || word.word);
    const punctChanged = wordEditDialog.editedPunct !== (word.original_punct || word.punct);
    
    if (wordChanged || punctChanged) {
      // Mark as corrected and preserve original values
      updatedWords[wordEditDialog.wordIndex] = {
        ...word,
        word: wordEditDialog.editedWord,
        punct: wordEditDialog.editedPunct,
        corrected: true,
        original_word: word.original_word || word.word,
        original_punct: word.original_punct || word.punct,
      };

      // Update transcript data
      const updatedData = {
        ...transcriptData,
        words: updatedWords,
      };

      onTranscriptUpdate(updatedData);
    }

    // Close dialog
    setWordEditDialog({
      open: false,
      wordIndex: null,
      originalWord: '',
      editedWord: '',
      originalPunct: '',
      editedPunct: '',
    });
  }, [wordEditDialog, transcriptData, onTranscriptUpdate]);

  // Handle word edit cancel
  const handleCancelWordEdit = useCallback(() => {
    setWordEditDialog({
      open: false,
      wordIndex: null,
      originalWord: '',
      editedWord: '',
      originalPunct: '',
      editedPunct: '',
    });
  }, []);

  // Handle undo word correction
  const handleUndoWordCorrection = useCallback((wordIndex: number) => {
    const updatedWords = [...transcriptData.words];
    const word = updatedWords[wordIndex];
    
    if (word.corrected && word.original_word && word.original_punct) {
      // Restore original values
      updatedWords[wordIndex] = {
        ...word,
        word: word.original_word,
        punct: word.original_punct,
        corrected: false,
        original_word: undefined,
        original_punct: undefined,
      };

      // Update transcript data
      const updatedData = {
        ...transcriptData,
        words: updatedWords,
      };

      onTranscriptUpdate(updatedData);
    }
  }, [transcriptData, onTranscriptUpdate]);

  // Handle speaker name edit dialog open
  const handleEditSpeakerName = useCallback((speakerIndex: number) => {
    const currentName = transcriptData.speaker_names?.[speakerIndex] || `Speaker ${speakerIndex}`;
    setSpeakerEditDialog({
      open: true,
      speakerIndex,
      speakerName: currentName,
    });
  }, [transcriptData.speaker_names]);

  // Handle speaker name save
  const handleSaveSpeakerName = useCallback(() => {
    if (speakerEditDialog.speakerIndex === null) return;

    const updatedSpeakerNames = {
      ...transcriptData.speaker_names,
      [speakerEditDialog.speakerIndex]: speakerEditDialog.speakerName,
    };

    // Update transcript data
    const updatedData = {
      ...transcriptData,
      speaker_names: updatedSpeakerNames,
    };

    onTranscriptUpdate(updatedData);

    // Close dialog
    setSpeakerEditDialog({
      open: false,
      speakerIndex: null,
      speakerName: '',
    });
  }, [speakerEditDialog, transcriptData, onTranscriptUpdate]);

  // Handle speaker name cancel
  const handleCancelSpeakerEdit = useCallback(() => {
    setSpeakerEditDialog({
      open: false,
      speakerIndex: null,
      speakerName: '',
    });
  }, []);

  // Format time for display
  const formatTime = useCallback((seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }, []);

  return (
    <Box>
      {/* Current Word Editor */}
      {currentWord && (
        <Box marginBottom={3}>
          <Typography variant="h6" gutterBottom>
            Current Word
          </Typography>
          <Box 
            padding={2} 
            style={{ 
              backgroundColor: '#e8f5e8', 
              borderRadius: '8px',
              border: '2px solid #4caf50'
            }}
          >
            <Box display="flex" alignItems="center" justifyContent="space-between">
              <Box>
                <Typography variant="body1">
                  <strong>"{currentWord.word}"</strong>
                  {currentWord.corrected && (
                    <Tooltip title={`Original: "${currentWord.original_word}"`}>
                      <Chip
                        label="Edited"
                        size="small"
                        color="secondary"
                        style={{ marginLeft: '8px' }}
                      />
                    </Tooltip>
                  )}
                </Typography>
                <Typography variant="body2" color="textSecondary">
                  Time: {formatTime(currentWord.start)} - {formatTime(currentWord.end)} • 
                  Confidence: {(currentWord.confidence * 100).toFixed(1)}% • 
                  Speaker: {transcriptData.speaker_names?.[currentWord.speaker] || `Speaker ${currentWord.speaker}`}
                </Typography>
              </Box>
              <Box>
                <IconButton
                  size="small"
                  onClick={() => handleEditWord(currentWord.index)}
                  color="primary"
                >
                  <Edit />
                </IconButton>
                {currentWord.corrected && (
                  <IconButton
                    size="small"
                    onClick={() => handleUndoWordCorrection(currentWord.index)}
                    color="secondary"
                  >
                    <Undo />
                  </IconButton>
                )}
              </Box>
            </Box>
          </Box>
        </Box>
      )}

      {/* Speaker Management */}
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMore />}>
          <Box display="flex" alignItems="center">
            <Person style={{ marginRight: '8px' }} />
            <Typography variant="h6">
              Speaker Names ({speakers.length} speakers)
            </Typography>
          </Box>
        </AccordionSummary>
        <AccordionDetails>
          <List style={{ width: '100%' }}>
            {speakers.map(speakerIndex => (
              <ListItem key={speakerIndex} divider>
                <ListItemText
                  primary={transcriptData.speaker_names?.[speakerIndex] || `Speaker ${speakerIndex}`}
                  secondary={`Speaker ${speakerIndex} • ${transcriptData.words.filter(w => w.speaker === speakerIndex).length} words`}
                />
                <ListItemSecondaryAction>
                  <IconButton
                    edge="end"
                    onClick={() => handleEditSpeakerName(speakerIndex)}
                    color="primary"
                  >
                    <RecordVoiceOver />
                  </IconButton>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        </AccordionDetails>
      </Accordion>

      {/* Corrected Words History */}
      {correctedWords.length > 0 && (
        <Accordion style={{ marginTop: '16px' }}>
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box display="flex" alignItems="center">
              <History style={{ marginRight: '8px' }} />
              <Typography variant="h6">
                Manual Corrections ({correctedWords.length} words)
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <List style={{ width: '100%' }}>
              {correctedWords.map((word, index) => (
                <ListItem key={`${word.index}-${index}`} divider>
                  <ListItemText
                    primary={
                      <Box>
                        <Typography component="span" style={{ textDecoration: 'line-through', color: '#999' }}>
                          "{word.original_word}"
                        </Typography>
                        <Typography component="span" style={{ marginLeft: '8px', fontWeight: 'bold' }}>
                          → "{word.word}"
                        </Typography>
                      </Box>
                    }
                    secondary={`Time: ${formatTime(word.start)} • Confidence: ${(word.confidence * 100).toFixed(1)}%`}
                  />
                  <ListItemSecondaryAction>
                    <IconButton
                      edge="end"
                      onClick={() => handleEditWord(word.index)}
                      color="primary"
                      size="small"
                    >
                      <Edit />
                    </IconButton>
                    <IconButton
                      edge="end"
                      onClick={() => handleUndoWordCorrection(word.index)}
                      color="secondary"
                      size="small"
                    >
                      <Undo />
                    </IconButton>
                  </ListItemSecondaryAction>
                </ListItem>
              ))}
            </List>
          </AccordionDetails>
        </Accordion>
      )}

      {/* Word Edit Dialog */}
      <Dialog
        open={wordEditDialog.open}
        onClose={handleCancelWordEdit}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Word</DialogTitle>
        <DialogContent>
          <Box marginBottom={2}>
            <Typography variant="body2" color="textSecondary">
              Original: "{wordEditDialog.originalWord}" → "{wordEditDialog.originalPunct}"
            </Typography>
          </Box>
          
          <TextField
            label="Word"
            value={wordEditDialog.editedWord}
            onChange={(e) => setWordEditDialog(prev => ({ ...prev, editedWord: e.target.value }))}
            fullWidth
            margin="normal"
            variant="outlined"
          />
          
          <TextField
            label="Punctuated Word"
            value={wordEditDialog.editedPunct}
            onChange={(e) => setWordEditDialog(prev => ({ ...prev, editedPunct: e.target.value }))}
            fullWidth
            margin="normal"
            variant="outlined"
            helperText="Word with proper punctuation and capitalization"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelWordEdit} color="secondary">
            Cancel
          </Button>
          <Button onClick={handleSaveWordEdit} color="primary" variant="contained">
            Save Changes
          </Button>
        </DialogActions>
      </Dialog>

      {/* Speaker Name Edit Dialog */}
      <Dialog
        open={speakerEditDialog.open}
        onClose={handleCancelSpeakerEdit}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>Edit Speaker Name</DialogTitle>
        <DialogContent>
          <TextField
            label="Speaker Name"
            value={speakerEditDialog.speakerName}
            onChange={(e) => setSpeakerEditDialog(prev => ({ ...prev, speakerName: e.target.value }))}
            fullWidth
            margin="normal"
            variant="outlined"
            placeholder="e.g., Dr. Smith, Student A, Moderator"
            helperText="Enter a descriptive name for this speaker"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelSpeakerEdit} color="secondary">
            Cancel
          </Button>
          <Button onClick={handleSaveSpeakerName} color="primary" variant="contained">
            Save Name
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ManualEditManager;