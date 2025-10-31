import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  Button,
  CircularProgress,
  Snackbar,
  AppBar,
  Toolbar,
  IconButton,
  Chip,
  Drawer,
} from '@material-ui/core';
import { Alert } from '@material-ui/lab';
import { ArrowBack, Save, Publish, Edit } from '@material-ui/icons';
import { AudioFileInfo } from '../../types/api';
import { CorrectedDeepgramResponse } from '../../types/deepgram';
import { ReactTranscriptEditorData } from '../../types/transcriptEditor';
import { DeepgramTransformer } from '../../services/DeepgramTransformer';
import { APIClient } from '../../services/APIClient';
import { AudioPlayerIntegration } from './AudioPlayerIntegration';
import { ManualEditManager } from './ManualEditManager';

// Import the react-transcript-editor component from npm package
import TranscriptEditor from '@bbc/react-transcript-editor';

interface TranscriptEditorWrapperProps {
  audioFile: AudioFileInfo;
  onBack: () => void;
  onSave?: (correctedTranscript: CorrectedDeepgramResponse) => void;
  onPublish?: () => void;
  apiClient: APIClient;
}

interface LoadingState {
  isLoading: boolean;
  message: string;
}

interface NotificationState {
  open: boolean;
  message: string;
  severity: 'success' | 'error' | 'info' | 'warning';
}

export const TranscriptEditorWrapper: React.FC<TranscriptEditorWrapperProps> = ({
  audioFile,
  onBack,
  onSave,
  onPublish,
  apiClient,
}) => {
  const [originalData, setOriginalData] = useState<CorrectedDeepgramResponse | null>(null);
  const [transcriptData, setTranscriptData] = useState<ReactTranscriptEditorData | null>(null);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [editPanelOpen, setEditPanelOpen] = useState<boolean>(false);
  const [loadingState, setLoadingState] = useState<LoadingState>({
    isLoading: true,
    message: 'Loading transcript...',
  });
  const [notification, setNotification] = useState<NotificationState>({
    open: false,
    message: '',
    severity: 'info',
  });

  // Construct media URL for compressed audio (always use compressed for web performance)
  const mediaUrl = useMemo(() => {
    if (audioFile.has_compressed_version) {
      // Use compressed audio for better web performance
      return `/api/audio/compressed/${encodeURIComponent(audioFile.path)}`;
    }
    // Fallback to original audio file
    return `/api/audio/${encodeURIComponent(audioFile.path)}`;
  }, [audioFile]);

  const showNotification = useCallback((
    message: string, 
    severity: 'success' | 'error' | 'info' | 'warning' = 'info'
  ) => {
    setNotification({
      open: true,
      message,
      severity,
    });
  }, []);

  const handleCloseNotification = useCallback(() => {
    setNotification(prev => ({ ...prev, open: false }));
  }, []);

  // Load transcript data on component mount
  useEffect(() => {
    const loadTranscript = async () => {
      try {
        console.log('🔄 Starting transcript load for:', audioFile.path);
        setLoadingState({
          isLoading: true,
          message: 'Loading transcript data...',
        });

        console.log('📡 Making API request to getTranscript...');
        const response = await apiClient.getTranscript(audioFile.path);
        console.log('📡 API response received:', response);
        
        if (!response.success || !response.data) {
          console.error('❌ API response failed:', response);
          throw new Error(response.error || 'Failed to load transcript');
        }

        console.log('✅ Raw transcript data received, size:', JSON.stringify(response.data).length, 'chars');
        const correctedResponse = response.data as CorrectedDeepgramResponse;
        console.log('📊 Corrected response structure:', {
          hasText: !!correctedResponse.text,
          hasSpeakers: !!correctedResponse.speakers,
          speakersCount: correctedResponse.speakers?.length || 0,
          hasRawResponse: !!correctedResponse.raw_response,
          hasWords: !!correctedResponse.raw_response?.results?.channels?.[0]?.alternatives?.[0]?.words,
          wordsCount: correctedResponse.raw_response?.results?.channels?.[0]?.alternatives?.[0]?.words?.length || 0
        });
        
        setOriginalData(correctedResponse);

        // Transform to ReactTranscriptEditorData format
        console.log('🔄 Starting data transformation...');
        const transformedData = DeepgramTransformer.transformToReactTranscriptEditor(correctedResponse);
        console.log('✅ Data transformation complete:', {
          wordsCount: transformedData.words?.length || 0,
          speakersCount: transformedData.speakers?.length || 0,
          hasTranscript: !!transformedData.transcript,
          transcriptLength: transformedData.transcript?.length || 0
        });
        
        setTranscriptData(transformedData);

        setLoadingState({
          isLoading: false,
          message: '',
        });

        console.log('🎉 Transcript loaded successfully!');
        showNotification('Transcript loaded successfully', 'success');
      } catch (error) {
        console.error('💥 Error loading transcript:', error);
        console.error('💥 Error stack:', error instanceof Error ? error.stack : 'No stack trace');
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        setLoadingState({
          isLoading: false,
          message: '',
        });
        showNotification(`Failed to load transcript: ${errorMessage}`, 'error');
      }
    };

    loadTranscript();
  }, [audioFile.path, apiClient, showNotification]);

  // Handle auto-save changes from the transcript editor
  const handleAutoSaveChanges = useCallback((data: ReactTranscriptEditorData) => {
    setTranscriptData(data);
    setHasUnsavedChanges(true);
  }, []);

  // Handle time updates from audio player
  const handleTimeUpdate = useCallback((time: number) => {
    setCurrentTime(time);
  }, []);

  // Handle transcript updates from manual edit manager
  const handleTranscriptUpdate = useCallback((updatedData: ReactTranscriptEditorData) => {
    setTranscriptData(updatedData);
    setHasUnsavedChanges(true);
  }, []);

  // Toggle edit panel
  const handleToggleEditPanel = useCallback(() => {
    setEditPanelOpen(prev => !prev);
  }, []);

  // Handle manual save
  const handleSave = useCallback(async () => {
    if (!originalData || !transcriptData) {
      showNotification('No data to save', 'warning');
      return;
    }

    try {
      setLoadingState({
        isLoading: true,
        message: 'Saving changes...',
      });

      // Merge corrections back into Deepgram response format
      const correctedResponse = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(
        originalData,
        transcriptData
      );

      // Save via API
      const response = await apiClient.saveTranscriptCorrections(
        audioFile.path,
        correctedResponse
      );

      if (!response.success) {
        throw new Error(response.error || 'Failed to save corrections');
      }

      // Update original data and clear unsaved changes flag
      setOriginalData(correctedResponse);
      setHasUnsavedChanges(false);

      setLoadingState({
        isLoading: false,
        message: '',
      });

      showNotification('Changes saved successfully', 'success');

      // Call optional onSave callback
      if (onSave) {
        onSave(correctedResponse);
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setLoadingState({
        isLoading: false,
        message: '',
      });
      showNotification(`Failed to save changes: ${errorMessage}`, 'error');
    }
  }, [originalData, transcriptData, audioFile.path, apiClient, showNotification, onSave]);

  // Handle publish action
  const handlePublish = useCallback(() => {
    if (hasUnsavedChanges) {
      showNotification('Please save your changes before publishing', 'warning');
      return;
    }

    if (onPublish) {
      onPublish();
    }
  }, [hasUnsavedChanges, onPublish, showNotification]);

  // Format file size for display
  const formatFileSize = useCallback((bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  }, []);

  // Format duration for display
  const formatDuration = useCallback((seconds?: number) => {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  }, []);

  if (loadingState.isLoading) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="400px">
        <CircularProgress size={60} />
        <Typography variant="h6" style={{ marginTop: '16px' }}>
          {loadingState.message}
        </Typography>
      </Box>
    );
  }

  if (!transcriptData) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="400px">
        <Typography variant="h6" color="error">
          Failed to load transcript data
        </Typography>
        <Button
          variant="contained"
          color="primary"
          onClick={onBack}
          style={{ marginTop: '16px' }}
        >
          Back to File Manager
        </Button>
      </Box>
    );
  }

  return (
    <Box>
      {/* Header with navigation and actions */}
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <IconButton edge="start" onClick={onBack} aria-label="back">
            <ArrowBack />
          </IconButton>
          
          <Box flexGrow={1} marginLeft={2}>
            <Typography variant="h6" component="div">
              {audioFile.filename}
            </Typography>
            <Box display="flex" alignItems="center" style={{ gap: '8px', marginTop: '4px' }}>
              <Typography variant="body2" color="textSecondary">
                {audioFile.seminar_group}
              </Typography>
              <Chip
                label={`${formatFileSize(audioFile.size)}`}
                size="small"
                variant="outlined"
              />
              {audioFile.has_compressed_version && audioFile.compressed_size && (
                <Chip
                  label={`Compressed: ${formatFileSize(audioFile.compressed_size)}`}
                  size="small"
                  variant="outlined"
                  color="primary"
                />
              )}
              {audioFile.duration && (
                <Chip
                  label={`Duration: ${formatDuration(audioFile.duration)}`}
                  size="small"
                  variant="outlined"
                />
              )}
            </Box>
          </Box>

          <Box display="flex" alignItems="center" style={{ gap: '8px' }}>
            {hasUnsavedChanges && (
              <Chip
                label="Unsaved Changes"
                size="small"
                color="secondary"
              />
            )}
            
            <Button
              variant="outlined"
              color="primary"
              startIcon={<Edit />}
              onClick={handleToggleEditPanel}
            >
              Manual Edits
            </Button>
            
            <Button
              variant="contained"
              color="primary"
              startIcon={<Save />}
              onClick={handleSave}
              disabled={!hasUnsavedChanges || loadingState.isLoading}
            >
              Save Edits
            </Button>
            
            {onPublish && (
              <Button
                variant="outlined"
                color="primary"
                startIcon={<Publish />}
                onClick={handlePublish}
                disabled={hasUnsavedChanges}
              >
                Publish
              </Button>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {/* Main Content Area */}
      <Box display="flex" style={{ height: 'calc(100vh - 64px)' }}>
        {/* Primary Content */}
        <Box flexGrow={1} display="flex" flexDirection="column">
          {/* Audio Player Integration */}
          <Box style={{ padding: '16px', backgroundColor: '#f5f5f5', borderBottom: '1px solid #e0e0e0' }}>
            <AudioPlayerIntegration
              mediaUrl={mediaUrl}
              transcriptData={transcriptData}
              currentTime={currentTime}
              onTimeUpdate={handleTimeUpdate}
              fileSize={audioFile.size}
              compressedSize={audioFile.compressed_size}
            />
          </Box>

          {/* Transcript Editor */}
          <Box flexGrow={1} style={{ overflow: 'hidden' }}>
            <TranscriptEditor
              transcriptData={transcriptData}
              mediaUrl={mediaUrl}
              isEditable={true}
              sttJsonType="deepgram"
              handleAutoSaveChanges={handleAutoSaveChanges}
              autoSaveContentType="draftjs"
              title={audioFile.filename}
              fileName={audioFile.filename}
              mediaType="audio"
              spellCheck={true}
              handleAnalyticsEvents={(event: any) => {
                console.log('📊 Transcript Editor Analytics:', event);
              }}
            />
          </Box>
        </Box>

        {/* Manual Edit Panel */}
        <Drawer
          anchor="right"
          open={editPanelOpen}
          onClose={handleToggleEditPanel}
          variant="persistent"
          style={{ zIndex: 1200 }}
          PaperProps={{
            style: {
              width: '400px',
              position: 'relative',
              height: 'calc(100vh - 64px)',
              top: '64px',
            }
          }}
        >
          <Box padding={2} style={{ height: '100%', overflow: 'auto' }}>
            <Typography variant="h6" gutterBottom>
              Manual Corrections
            </Typography>
            <ManualEditManager
              transcriptData={transcriptData}
              onTranscriptUpdate={handleTranscriptUpdate}
              currentTime={currentTime}
            />
          </Box>
        </Drawer>
      </Box>

      {/* Notifications */}
      <Snackbar
        open={notification.open}
        autoHideDuration={6000}
        onClose={handleCloseNotification}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      >
        <Alert onClose={handleCloseNotification} severity={notification.severity}>
          {notification.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default TranscriptEditorWrapper;