import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, AppBar, Toolbar, IconButton, Button, CircularProgress, Snackbar, Typography } from '@material-ui/core';
import { Alert } from '@material-ui/lab';
import { ArrowBack, Save } from '@material-ui/icons';
import TranscriptEditorComponent from '@bbc/react-transcript-editor';
import { AudioFileInfo } from '../../types/api';
import { CorrectedDeepgramResponse } from '../../types/deepgram';
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
  const [originalData, setOriginalData] = useState<CorrectedDeepgramResponse | null>(null);
  const [transcriptData, setTranscriptData] = useState<ReactTranscriptEditorData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  
  // Ref to access the react-transcript-editor instance to read content on demand
  const transcriptEditorRef = useRef<any>(null);
  const [notification, setNotification] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info',
  });

  // Construct media URL for compressed audio
  const mediaUrl = audioFile.has_compressed_version && audioFile.compressed_path
    ? `/api/audio/${encodeURIComponent(audioFile.compressed_path)}`
    : `/api/audio/${encodeURIComponent(audioFile.path)}`;

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

        const correctedResponse = response.data as CorrectedDeepgramResponse;
        setOriginalData(correctedResponse);

        // Transform to ReactTranscriptEditorData format
        const transformedData = DeepgramTransformer.transformToReactTranscriptEditor(correctedResponse);
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
      console.log('❌ extractWordsFromDraftJS: missing data', { hasDraftJsBlocks: !!draftJsBlocks, hasTranscriptData: !!transcriptData });
      return null;
    }
    
    // Extract the actual block data
    // react-transcript-editor with autoSaveContentType="draftjs" returns: { data: { blocks: [...], entityMap: {...} }, ext: 'json' }
    const blocks = draftJsBlocks.data?.blocks || draftJsBlocks.blocks;
    
    if (!blocks || !Array.isArray(blocks)) {
      console.log('❌ extractWordsFromDraftJS: blocks is not array', { 
        hasBlocks: !!blocks,
        isArray: Array.isArray(blocks),
        keys: draftJsBlocks && typeof draftJsBlocks === 'object' ? Object.keys(draftJsBlocks) : []
      });
      return null;
    }
    
    console.log('✅ extractWordsFromDraftJS: found blocks array', { blocksCount: blocks.length });
    
    // Flatten words from all blocks
    const words: any[] = [];
    const speakerNamesMap: { [speakerIndex: number]: string } = {};
    
    blocks.forEach((block: any, index: number) => {
      if (block.data && block.data.words && Array.isArray(block.data.words)) {
        words.push(...block.data.words);
        if (index === 0) {
          console.log('📝 First block structure:', {
            hasWords: !!block.data.words,
            wordsCount: block.data.words.length,
            sampleWord: block.data.words[0],
            sampleWordHasIndex: 'index' in (block.data.words[0] || {}),
            speaker: block.data.speaker
          });
        }
      }
      
      // Extract speaker name if it's been edited (not default "Speaker X" format)
      if (block.data && block.data.speaker) {
        const speakerMatch = block.data.speaker.match(/^Speaker (\d+)$/);
        if (!speakerMatch) {
          // This is a custom speaker name, extract the speaker index from words
          const firstWord = block.data.words && block.data.words[0];
          if (firstWord && firstWord.speaker !== undefined) {
            const speakerIndex = firstWord.speaker;
            speakerNamesMap[speakerIndex] = block.data.speaker;
          }
        }
      }
    });
    
    if (words.length === 0) {
      console.log('❌ extractWordsFromDraftJS: no words found');
      return null;
    }
    
    console.log('✅ extractWordsFromDraftJS: extracted words', { wordsCount: words.length, speakerNamesCount: Object.keys(speakerNamesMap).length });
    
    // Return updated data with extracted words and speaker names
    return {
      ...transcriptData,
      words: words,
      speaker_names: Object.keys(speakerNamesMap).length > 0 ? speakerNamesMap : transcriptData.speaker_names
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

      // Get current editor content directly from the transcript editor
      let updatedTranscriptData = transcriptData;
      if (transcriptEditorRef.current) {
        const currentDraftJsData = transcriptEditorRef.current.getEditorContent('draftjs');
        if (currentDraftJsData) {
          const extracted = extractWordsFromDraftJS(currentDraftJsData);
          if (extracted) {
            updatedTranscriptData = extracted;
            console.log('📦 Extracted data from DraftJS:', {
              wordsCount: extracted.words?.length,
              speakerNames: extracted.speaker_names,
              sampleWord: extracted.words?.[0]
            });
          } else {
            console.warn('⚠️ Failed to extract data from DraftJS');
          }
        }
      }

      console.log('💾 Before merge:', {
        originalWordsCount: originalData.raw_response?.results?.channels?.[0]?.alternatives?.[0]?.words?.length,
        editedWordsCount: updatedTranscriptData.words?.length,
        sampleOriginalWord: originalData.raw_response?.results?.channels?.[0]?.alternatives?.[0]?.words?.[0],
        sampleEditedWord: updatedTranscriptData.words?.[0]
      });

      // Merge corrections back into Deepgram response format
      const correctedResponse = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(
        originalData,
        updatedTranscriptData
      );

      console.log('✅ After merge:', {
        correctedWordsCount: correctedResponse.raw_response?.results?.channels?.[0]?.alternatives?.[0]?.words?.length,
        corrections: correctedResponse.corrections
      });

      // Save via API
      const response = await apiClient.saveTranscriptCorrections(
        audioFile.path,
        correctedResponse
      );

      if (!response.success) {
        throw new Error(response.error || 'Failed to save corrections');
      }

      // Update original data
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
            {isSaving ? 'Saving...' : 'Save Edits'}
          </Button>
        </Toolbar>
      </AppBar>

      {/* Transcript Editor */}
      <Box style={{ height: 'calc(100vh - 64px)' }}>
        <TranscriptEditorComponent
          ref={transcriptEditorRef}
          transcriptData={transcriptData}
          mediaUrl={mediaUrl}
          isEditable={true}
          sttJsonType="deepgram"
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

