import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, AppBar, Toolbar, IconButton, Button, CircularProgress, Snackbar, Typography } from '@material-ui/core';
import { Alert } from '@material-ui/lab';
import { ArrowBack, Save } from '@material-ui/icons';
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
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const transcriptEditorRef = useRef<any>(null);
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

  // Extract words and speaker names from DraftJS blocks
  const extractWordsFromDraftJS = useCallback((draftJsBlocks: any): ReactTranscriptEditorData | null => {
    if (!draftJsBlocks || !transcriptData) {
      return null;
    }
    
    const blocks = draftJsBlocks.data?.blocks || draftJsBlocks.blocks;
    
    if (!blocks || !Array.isArray(blocks)) {
      return null;
    }
    
    const words: any[] = [];
    const speakerNamesMap: { [speakerIndex: number]: string } = {};
    
    blocks.forEach((block: any) => {
      if (block.data && block.data.words && Array.isArray(block.data.words)) {
        const blockWords = block.data.words.map((word: any, wordIndex: number) => {
          const isFirstInBlock = wordIndex === 0;
          const isLastInBlock = wordIndex === block.data.words.length - 1;
          return {
            ...word,
            paragraph_start: isFirstInBlock,
            paragraph_end: isLastInBlock
          };
        });
        words.push(...blockWords);
        
        if (block.data.speaker) {
          speakerNamesMap[block.data.speaker] = block.data.speaker;
        }
      }
    });
    
    if (words.length === 0) {
      return null;
    }
    
    const customSpeakerNames: { [speakerIndex: number]: string } = {};
    for (const [indexStr, name] of Object.entries(speakerNamesMap)) {
      const speakerIndex = parseInt(indexStr);
      if (!name.match(/^Speaker \d+$/)) {
        customSpeakerNames[speakerIndex] = name;
      }
    }
    
    const mergedSpeakerNames = {
      ...(transcriptData.speaker_names || {}),
      ...customSpeakerNames
    };
    
    const finalSpeakerNames = Object.keys(mergedSpeakerNames).length > 0 ? mergedSpeakerNames : undefined;
    
    return {
      ...transcriptData,
      words: words,
      speaker_names: finalSpeakerNames
    };
  }, [transcriptData]);

  // Handle manual save
  const handleSave = useCallback(async () => {
    if (!originalData || !transcriptData) {
      showNotification('No data to save', 'error');
      return;
    }

    try {
      setIsSaving(true);

      let updatedTranscriptData = transcriptData;
      if (transcriptEditorRef.current) {
        const currentDraftJsData = transcriptEditorRef.current.getEditorContent('draftjs');
        if (currentDraftJsData) {
          const extracted = extractWordsFromDraftJS(currentDraftJsData);
          if (extracted) {
            updatedTranscriptData = extracted;
          }
        }
      }

      const correctedResponse = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(
        originalData,
        updatedTranscriptData
      );

      const response = await apiClient.saveTranscriptCorrections(
        audioFile.path,
        correctedResponse
      );

      if (!response.success) {
        throw new Error(response.error || 'Failed to save corrections');
      }

      setOriginalData(correctedResponse);
      setIsSaving(false);

      showNotification('Changes saved successfully', 'success');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      setIsSaving(false);
      showNotification(`Failed to save changes: ${errorMessage}`, 'error');
    }
  }, [originalData, transcriptData, extractWordsFromDraftJS, audioFile.path, apiClient, showNotification]);

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
          
          <Button
            variant="contained"
            color="primary"
            startIcon={<Save />}
            onClick={handleSave}
            disabled={isSaving}
          >
            {isSaving ? 'Saving...' : 'Save Corrections'}
          </Button>
        </Toolbar>
      </AppBar>

      {/* Transcript Editor */}
      <Box style={{ height: 'calc(100vh - 64px)' }}>
        <TranscriptEditorComponent
          ref={transcriptEditorRef}
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

