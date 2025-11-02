import React, { useState, useEffect, useCallback } from 'react';
import { Box, AppBar, Toolbar, IconButton, Button, CircularProgress, Snackbar, Typography } from '@material-ui/core';
import { Alert } from '@material-ui/lab';
import { ArrowBack } from '@material-ui/icons';
import TranscriptEditorComponent from '@bbc/react-transcript-editor';
import { AudioFileInfo } from '../../types/api';
import { RichWordsTranscript } from '../../types/deepgram';
import { ReactTranscriptEditorData } from '../../types/transcriptEditor';
import { DeepgramTransformer } from '../../services/DeepgramTransformer';
import { APIClient } from '../../services/APIClient';

interface TranscriptEditorProps {
  audioFile: AudioFileInfo;
  onBack: () => void;
  apiClient: APIClient;
}

export const TranscriptEditor: React.FC<TranscriptEditorProps> = ({
  audioFile,
  onBack,
  apiClient,
}) => {
  const [originalData, setOriginalData] = useState<RichWordsTranscript | null>(null);
  const [transcriptData, setTranscriptData] = useState<ReactTranscriptEditorData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [notification, setNotification] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // Construct media URL - Always use compressed WebM/Opus for optimal playback and seeking accuracy
  // WebM/Opus provides frame-accurate seeking and excellent browser support
  // REQUIRE compressed file - throw error if not available
  if (!audioFile.has_compressed_version || !audioFile.compressed_path) {
    throw new Error(`Compressed WebM audio not available for ${audioFile.filename || audioFile.path}. Please compress the audio first.`);
  }
  const mediaUrl = `/api/audio/${encodeURIComponent(audioFile.compressed_path)}`;

  const showNotification = useCallback((message: string, severity: 'success' | 'error' | 'info' = 'info') => {
    setNotification({ open: true, message, severity });
  }, []);

  const handleCloseNotification = useCallback(() => {
    setNotification(prev => ({ ...prev, open: false }));
  }, []);

  // Load transcript data on component mount
  useEffect(() => {
    const loadTranscript = async () => {
      try {
        setIsLoading(true);
        const response = await apiClient.getTranscript(audioFile.path);
        
        if (!response.success || !response.data) {
          throw new Error(response.error || 'Failed to load transcript');
        }

        // Store original data
        setOriginalData(response.data as RichWordsTranscript);
        
        // Transform to ReactTranscriptEditorData format
        const transformedData = DeepgramTransformer.transformToReactTranscriptEditor(response.data);
        setTranscriptData(transformedData);

        setIsLoading(false);
      } catch (error) {
        console.error('Error loading transcript:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
        setIsLoading(false);
        showNotification(`Failed to load transcript: ${errorMessage}`, 'error');
      }
    };

    loadTranscript();
  }, [audioFile.path, apiClient, showNotification]);

  // Handle auto-save from word corrections
  useEffect(() => {
    const handleWordSave = async (e: Event) => {
      const customEvent = e as CustomEvent;
      if (!originalData || !customEvent.detail?.data) {
        return;
      }

      try {
        console.log('Auto-saving word correction...', customEvent.detail.data);
        
        // Extract words from DraftJS blocks
        const draftJsData = customEvent.detail.data;
        const blocks = draftJsData.data?.blocks || draftJsData.blocks;
        
        if (!blocks || !Array.isArray(blocks)) {
          console.error('Invalid DraftJS data structure');
          showNotification('Failed to save word correction: invalid data', 'error');
          return;
        }
        
        // Flatten words from all blocks
        const extractedWords: any[] = [];
        blocks.forEach((block: any) => {
          if (block.data && block.data.words && Array.isArray(block.data.words)) {
            extractedWords.push(...block.data.words);
          }
        });
        
        console.log('Extracted words:', extractedWords.length);
        
        // Create updated ReactTranscriptEditorData
        const updatedTranscriptData: ReactTranscriptEditorData = {
          ...transcriptData!,
          words: extractedWords
        };
        
        // Merge corrections back into RichWordsTranscript format
        const correctedResponse = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(
          originalData,
          updatedTranscriptData
        );
        
        console.log('Merged corrections, saving to backend...');
        
        // Save via API
        const response = await apiClient.saveTranscriptCorrections(
          audioFile.path,
          correctedResponse
        );
        
        if (!response.success) {
          throw new Error(response.error || 'Failed to save corrections');
        }
        
        // Update original data to reflect the corrections
        setOriginalData(correctedResponse);
        
        showNotification('Word correction saved', 'success');
      } catch (error) {
        console.error('Error auto-saving word correction:', error);
        showNotification('Failed to save word correction', 'error');
      }
    };

    window.addEventListener('transcript-word-save', handleWordSave);
    return () => {
      window.removeEventListener('transcript-word-save', handleWordSave);
    };
  }, [originalData, transcriptData, audioFile.path, apiClient, showNotification]);

  if (isLoading) {
    return (
      <Box display="flex" flexDirection="column" alignItems="center" justifyContent="center" minHeight="400px">
        <CircularProgress size={60} />
        <Typography variant="h6" style={{ marginTop: '16px' }}>
          Loading transcript...
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
      {/* Header */}
      <AppBar position="static" color="default" elevation={1}>
        <Toolbar>
          <IconButton edge="start" onClick={onBack} aria-label="back">
            <ArrowBack />
          </IconButton>
          
          <Box flexGrow={1} marginLeft={2}>
            <Typography variant="h6" component="div">
              {audioFile.filename}
            </Typography>
          </Box>
        </Toolbar>
      </AppBar>

      {/* Transcript Editor */}
      <Box style={{ height: 'calc(100vh - 64px)' }}>
        <TranscriptEditorComponent
          transcriptData={transcriptData}
          mediaUrl={mediaUrl}
          isEditable={false}
          sttJsonType="deepgram"
          autoSaveContentType="draftjs"
          title={audioFile.filename}
          fileName={audioFile.filename}
          mediaType="audio"
          spellCheck={true}
        />
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

export default TranscriptEditor;

