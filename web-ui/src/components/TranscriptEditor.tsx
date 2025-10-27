/**
 * Transcript Editor component using BBC react-transcript-editor.
 */

import React, { useState, useEffect, useRef } from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  CircularProgress,
  Alert,
  AppBar,
  Toolbar,
  IconButton,

} from '@mui/material';
import {
  ArrowBack as BackIcon,
  Save as SaveIcon,
  GetApp as ExportIcon,
  Public as PublishIcon,

} from '@mui/icons-material';

import type { AudioFile, TranscriptionData } from '../types';
import { apiService } from '../services/api';
import { BBCTranscriptEditor } from './BBCTranscriptEditor';
import { AudioPlayer, type AudioPlayerRef } from './AudioPlayer';

interface TranscriptEditorProps {
  file: AudioFile;
  onBack: () => void;
}

export const TranscriptEditor: React.FC<TranscriptEditorProps> = ({ file, onBack }) => {
  const [transcriptionData, setTranscriptionData] = useState<TranscriptionData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [isPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [editedTranscription, setEditedTranscription] = useState<TranscriptionData | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioPlayerRef = useRef<AudioPlayerRef>(null);

  useEffect(() => {
    loadTranscription();
    // Set up audio URL - proxy will route to FastAPI backend
    setAudioUrl(`/api/files/${file.id}/audio`);
  }, [file.id]);

  // Auto-save effect
  useEffect(() => {
    if (hasUnsavedChanges && editedTranscription) {
      const autoSaveTimer = setTimeout(() => {
        handleAutoSave();
      }, 2000); // Auto-save after 2 seconds of inactivity

      return () => clearTimeout(autoSaveTimer);
    }
  }, [hasUnsavedChanges, editedTranscription]);

  const loadTranscription = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiService.getTranscription(file.id);
      setTranscriptionData(data);
      setEditedTranscription(data); // Initialize edited version
      setHasUnsavedChanges(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transcription');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!editedTranscription) return;
    
    setSaving(true);
    try {
      await apiService.saveTranscription(file.id, editedTranscription);
      setTranscriptionData(editedTranscription);
      setHasUnsavedChanges(false);
      console.log('Transcription saved successfully');
    } catch (err) {
      console.error('Failed to save:', err);
      setError(err instanceof Error ? err.message : 'Failed to save transcription');
    } finally {
      setSaving(false);
    }
  };

  const handleAutoSave = async () => {
    if (!editedTranscription || saving) return;
    
    try {
      await apiService.saveTranscription(file.id, editedTranscription);
      setTranscriptionData(editedTranscription);
      setHasUnsavedChanges(false);
      console.log('Auto-saved transcription');
    } catch (err) {
      console.error('Auto-save failed:', err);
    }
  };



  const handleExport = async (format: 'html' | 'markdown' | 'txt') => {
    try {
      const response = await apiService.exportTranscription(file.id, format);
      console.log('Export created:', response);
      // TODO: Handle download
    } catch (err) {
      console.error('Export failed:', err);
    }
  };

  const handlePublish = async () => {
    try {
      const response = await apiService.publishTranscription(file.id, {
        file_id: file.id,
        title: file.name.replace('.mp3', ''),
        description: `Transcription of ${file.name}`,
        tags: [],
      });
      console.log('Published:', response);
    } catch (err) {
      console.error('Publish failed:', err);
    }
  };



  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds: number): string => {
    if (seconds === 0) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <AppBar position="static" color="default" elevation={1}>
          <Toolbar>
            <IconButton edge="start" onClick={onBack}>
              <BackIcon />
            </IconButton>
            <Typography variant="h6" sx={{ flexGrow: 1 }}>
              {file.name}
            </Typography>
          </Toolbar>
        </AppBar>
        <Box p={3}>
          <Alert severity="error">{error}</Alert>
        </Box>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header */}
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <IconButton edge="start" onClick={onBack}>
            <BackIcon />
          </IconButton>
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{file.name}</Typography>
            <Typography variant="caption" color="text.secondary">
              {formatFileSize(file.size)} • {formatDuration(file.duration)}
              {transcriptionData && (
                <> • Confidence: {Math.round((transcriptionData.confidence || 0) * 100)}%</>
              )}
              {hasUnsavedChanges && (
                <> • <span style={{ color: '#ff9800' }}>Unsaved changes</span></>
              )}
            </Typography>
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="outlined"
              startIcon={<ExportIcon />}
              onClick={() => handleExport('html')}
            >
              Export
            </Button>
            <Button
              variant="outlined"
              startIcon={<PublishIcon />}
              onClick={handlePublish}
            >
              Publish
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              onClick={handleSave}
              disabled={saving || !hasUnsavedChanges}
              color={hasUnsavedChanges ? 'warning' : 'primary'}
            >
              {saving ? 'Saving...' : hasUnsavedChanges ? 'Save Changes' : 'Saved'}
            </Button>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Content */}
      <Box p={3}>
        {transcriptionData ? (
          <Box>
            {/* Audio Player Section */}
            <Box sx={{ mb: 3 }}>
              <Typography variant="h6" gutterBottom>
                Audio Player
              </Typography>
              {audioUrl ? (
                <AudioPlayer
                  ref={audioPlayerRef}
                  audioFile={audioUrl}
                  currentTime={currentTime}
                  onTimeUpdate={setCurrentTime}
                  onSeek={setCurrentTime}
                  duration={file.duration}
                />
              ) : (
                <Paper sx={{ p: 2 }}>
                  <Typography color="text.secondary">
                    Audio file not available for playback
                  </Typography>
                </Paper>
              )}
            </Box>

            {/* Transcript Content */}
            <Paper sx={{ p: 2 }}>
              <Typography variant="h6" gutterBottom>
                Transcript
              </Typography>
              
              {/* Enhanced Transcript Editor */}
              {editedTranscription?.speakers && editedTranscription.speakers.length > 0 ? (
                <BBCTranscriptEditor
                  transcriptionData={editedTranscription}
                  onTranscriptChange={(updatedData) => {
                    setEditedTranscription(updatedData);
                    setHasUnsavedChanges(true);
                  }}
                  currentTime={currentTime}
                  onSeek={setCurrentTime}
                  onPlaySegment={(startTime, endTime) => {
                    // Play specific segment using the audio player
                    if (audioPlayerRef.current) {
                      audioPlayerRef.current.playSegment(startTime, endTime);
                    }
                  }}
                  isPlaying={isPlaying}
                />
              ) : (
                <Box sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="body1" color="text.secondary">
                    {editedTranscription?.text || 'No transcription content available'}
                  </Typography>
                </Box>
              )}
            </Paper>
          </Box>
        ) : (
          <Alert severity="info">
            No transcription data available for this file.
          </Alert>
        )}
      </Box>
    </Box>
  );
};