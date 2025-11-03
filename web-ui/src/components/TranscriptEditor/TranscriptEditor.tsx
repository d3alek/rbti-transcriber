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

// Helper function to remove .mp3 extension from filename for display
const getDisplayName = (filename: string): string => {
  return filename.replace(/\.mp3$/i, '');
};

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
  // Store original speaker index to name mapping for looking up indices after name changes
  const originalSpeakerMappingRef = useRef<Map<string, number>>(new Map());
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

        // Normalize to RichWordsTranscript format first (handles raw Deepgram, etc.)
        const normalizedData = DeepgramTransformer.normalizeToSimplifiedFormat(response.data);

        // Store original data
        setOriginalData(normalizedData);
        
        // Transform to ReactTranscriptEditorData format
        const transformedData = DeepgramTransformer.transformToReactTranscriptEditor(normalizedData);
        setTranscriptData(transformedData);

        // Build original speaker mapping: "Speaker 0" -> 0, "Speaker 1" -> 1, etc.
        originalSpeakerMappingRef.current.clear();
        if (transformedData.speaker_names) {
          for (const [indexStr, name] of Object.entries(transformedData.speaker_names)) {
            originalSpeakerMappingRef.current.set(name, parseInt(indexStr));
          }
        }
        // Also add default "Speaker X" mappings if not already present
        // Use normalizedData.words since we know it's in RichWordsTranscript format
        normalizedData.words.forEach((word: any) => {
          const speakerIndex = word.speaker !== undefined ? word.speaker : 0;
          const defaultName = `Speaker ${speakerIndex}`;
          if (!originalSpeakerMappingRef.current.has(defaultName)) {
            originalSpeakerMappingRef.current.set(defaultName, speakerIndex);
          }
        });

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
    
    // First pass: collect all unique speaker names in order they first appear
    const uniqueSpeakers: string[] = [];
    blocks.forEach((block: any) => {
      if (block.data && block.data.speaker && !uniqueSpeakers.includes(block.data.speaker)) {
        uniqueSpeakers.push(block.data.speaker);
      }
    });
    
    // Get original speakers in order (by numeric index, not sorted by name)
    const originalSpeakersArray = Array.from(originalSpeakerMappingRef.current.entries())
      .sort((a, b) => a[1] - b[1]); // Sort by numeric index, not name
    
    // Build reverse mapping: speaker name -> speaker index
    // This mapping is used both for extracting words AND for building customSpeakerNames
    const speakerNameToIndexMap = new Map<string, number>();
    const speakerNamesMap: { [name: string]: string } = {};
    
    blocks.forEach((block: any) => {
      if (block.data && block.data.speaker) {
        const speakerName = block.data.speaker;
        speakerNamesMap[speakerName] = speakerName; // For building customSpeakerNames later
        
        // Check if it's "Speaker X" format
        const speakerMatch = speakerName.match(/^Speaker (\d+)$/);
      if (speakerMatch) {
        // It's a default "Speaker X" format
          speakerNameToIndexMap.set(speakerName, parseInt(speakerMatch[1]));
      } else {
          // It's a custom name - find its position in the unsorted unique list
          const positionInUniqueList = uniqueSpeakers.indexOf(speakerName);
        
        if (positionInUniqueList !== -1 && positionInUniqueList < originalSpeakersArray.length) {
          // Map to the original speaker at the same position
            const speakerIndex = originalSpeakersArray[positionInUniqueList][1]; // Get the numeric index
            speakerNameToIndexMap.set(speakerName, speakerIndex);
          }
        }
      }
    });
    
    blocks.forEach((block: any) => {
      if (block.data && block.data.words && Array.isArray(block.data.words)) {
        // Get the speaker name from the block (e.g., "Speaker 0" or "Dr. Reams")
        const blockSpeakerName = block.data.speaker;
        
        if (!blockSpeakerName || blockSpeakerName.trim() === "") {
          const errorMsg = "Speaker label is missing/empty in one of the paragraph blocks. Each paragraph must have a speaker.";
          console.error('❌ [extractWordsFromDraftJS] ' + errorMsg);
          showNotification(errorMsg, 'error');
          throw new Error(errorMsg);
        }
        
        // Map speaker name to speaker index using the pre-built mapping
        let blockSpeakerIndex: number | undefined = speakerNameToIndexMap.get(blockSpeakerName);
        
        // Fallback: if not in pre-built mapping, try other sources
        if (blockSpeakerIndex === undefined) {
          // Check if it's "Speaker X" format
          const speakerMatch = blockSpeakerName.match(/^Speaker (\d+)$/);
          if (speakerMatch) {
            blockSpeakerIndex = parseInt(speakerMatch[1]);
          } else {
            // Look it up in current speaker_names mapping
            if (transcriptData?.speaker_names) {
              for (const [indexStr, name] of Object.entries(transcriptData.speaker_names)) {
                if (name === blockSpeakerName) {
                  blockSpeakerIndex = parseInt(indexStr);
                  break;
                }
              }
            }
            
            // If still not found, look it up in the original mapping
            if (blockSpeakerIndex === undefined) {
              blockSpeakerIndex = originalSpeakerMappingRef.current.get(blockSpeakerName);
            }
          }
        }
        
        // Extract words and assign speaker index from block
        const blockWords = block.data.words.map((word: any, wordIndex: number) => {
          const isFirstInBlock = wordIndex === 0;
          const isLastInBlock = wordIndex === block.data.words.length - 1;
          return {
            ...word,
            // Assign speaker index from block - use block speaker index if available, 
            // otherwise fall back to word.speaker if it exists, otherwise 0
            speaker: blockSpeakerIndex !== undefined ? blockSpeakerIndex : (word.speaker !== undefined ? word.speaker : 0),
            paragraph_start: isFirstInBlock,
            paragraph_end: isLastInBlock
          };
        });
        words.push(...blockWords);
      }
    });
    
    if (words.length === 0) {
      return null;
    }
    
    // Build customSpeakerNames using the pre-built mapping (DRY principle)
    // Reuse speakerNameToIndexMap that we already built above
    const customSpeakerNames: { [speakerIndex: number]: string } = {};
    
    // Use the same mapping we built earlier - iterate through speakerNamesMap
    // and use speakerNameToIndexMap to get the index (no duplicate logic)
    for (const [speakerName] of Object.entries(speakerNamesMap)) {
      const speakerIndex = speakerNameToIndexMap.get(speakerName);
      
      // Only save if it's a custom name (not "Speaker X" format) and we found an index
      if (speakerIndex !== undefined && !speakerName.match(/^Speaker \d+$/)) {
        customSpeakerNames[speakerIndex] = speakerName;
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

      // Convert the edited ReactTranscriptEditorData directly to RichWordsTranscript
      const correctedResponse = DeepgramTransformer.convertReactTranscriptEditorToRichWordsTranscript(
        updatedTranscriptData,
        originalData // Pass originalData to increment version correctly
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
              {getDisplayName(audioFile.filename)}
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
          title={getDisplayName(audioFile.filename)}
          fileName={getDisplayName(audioFile.filename)}
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

