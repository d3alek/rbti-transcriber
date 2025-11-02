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
  
  // Ref to access the react-transcript-editor instance to read content on demand
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

        const correctedResponse = response.data as RichWordsTranscript;
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
    // Also track which words are at paragraph boundaries (first word in block = paragraph_start, last word = paragraph_end)
    const words: any[] = [];
    const speakerNamesMap: { [speakerIndex: number]: string } = {};
    
    blocks.forEach((block: any, index: number) => {
      if (block.data && block.data.words && Array.isArray(block.data.words)) {
        // Mark first word of block as paragraph_start, last word as paragraph_end
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
        if (index === 0) {
          console.log('📝 First block structure:', {
            hasWords: !!block.data.words,
            wordsCount: block.data.words.length,
            sampleWord: block.data.words[0],
            sampleWordHasIndex: 'index' in (block.data.words[0] || {}),
            speaker: block.data.speaker,
            blockDataKeys: block.data ? Object.keys(block.data) : [],
            firstWordSpeaker: block.data.words[0]?.speaker
          });
        }
      }
      
      // Extract speaker name from block - capture all speaker names, not just custom ones
      // Note: Words in DraftJS blocks don't have speaker property - it's only in block.data.speaker
      if (block.data && block.data.speaker) {
        let speakerIndex: number | null = null;
        const speakerName = block.data.speaker;
        
        // First, try parsing from "Speaker X" format
        const match = speakerName.match(/^Speaker (\d+)$/);
        if (match) {
          speakerIndex = parseInt(match[1]);
        } else {
          // It's a custom name - need to find which speaker index it corresponds to
          // We can do this by:
          // 1. Check if we already have this name mapped (from previous blocks)
          // 2. If not, use the original transcriptData to reverse-lookup
          // 3. Or, find words from original transcriptData that match this block's time range
          
          // Try reverse lookup in existing speaker_names
          if (transcriptData.speaker_names) {
            for (const [indexStr, name] of Object.entries(transcriptData.speaker_names)) {
              if (name === speakerName) {
                speakerIndex = parseInt(indexStr);
                break;
              }
            }
          }
          
          // If still not found, try to find by matching words with original transcript
          // Find words in original transcript that match this block's time range
          if (speakerIndex === null && block.data.words && block.data.words.length > 0) {
            const firstWord = block.data.words[0];
            if (firstWord && firstWord.start !== undefined && transcriptData.words) {
              // Find original word at same time position
              const originalWord = transcriptData.words.find((w: any) => 
                Math.abs(w.start - firstWord.start) < 0.01
              );
              if (originalWord && originalWord.speaker !== undefined) {
                speakerIndex = originalWord.speaker;
              }
            }
          }
        }
        
        // Store the speaker name if we found an index
        if (speakerIndex !== null) {
          speakerNamesMap[speakerIndex] = speakerName;
          if (index < 3 || Object.keys(speakerNamesMap).length <= 2) {
            console.log('🎤 Captured speaker name:', {
              blockIndex: index,
              speakerIndex,
              speakerName: speakerName,
              isCustom: !speakerName.match(/^Speaker \d+$/),
              foundByParsing: !!match,
              foundByReverseLookup: !match && speakerIndex !== null
            });
          }
        } else {
          // Couldn't determine speaker index for custom name
          console.warn('⚠️ Could not determine speaker index for custom speaker name:', {
            blockIndex: index,
            speakerName: speakerName,
            hasOriginalSpeakerNames: !!transcriptData.speaker_names,
            firstWordStart: block.data.words?.[0]?.start
          });
        }
      }
    });
    
    if (words.length === 0) {
      console.log('❌ extractWordsFromDraftJS: no words found');
      return null;
    }
    
    // Filter to only include custom speaker names (not default "Speaker X" format)
    const customSpeakerNames: { [speakerIndex: number]: string } = {};
    for (const [indexStr, name] of Object.entries(speakerNamesMap)) {
      const speakerIndex = parseInt(indexStr);
      // Only include if it's not a default "Speaker X" format
      if (!name.match(/^Speaker \d+$/)) {
        customSpeakerNames[speakerIndex] = name;
      }
    }
    
    // Merge with existing speaker_names, keeping existing custom names
    const mergedSpeakerNames = {
      ...(transcriptData.speaker_names || {}),
      ...customSpeakerNames
    };
    
    // Only include speaker_names if there are custom names
    const finalSpeakerNames = Object.keys(mergedSpeakerNames).length > 0 ? mergedSpeakerNames : undefined;
    
    console.log('✅ extractWordsFromDraftJS: extracted words', { 
      wordsCount: words.length, 
      allSpeakerNames: Object.keys(speakerNamesMap).length,
      customSpeakerNames: Object.keys(customSpeakerNames).length,
      finalSpeakerNames 
    });
    
    // Return updated data with extracted words and speaker names
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

      // Get current editor content directly from the transcript editor
      let updatedTranscriptData = transcriptData;
      if (transcriptEditorRef.current) {
        const currentDraftJsData = transcriptEditorRef.current.getEditorContent('draftjs');
        if (currentDraftJsData) {
          // Debug: log the raw structure we receive
          console.log('🔍 Raw DraftJS data structure:', {
            hasData: !!currentDraftJsData.data,
            hasBlocks: !!currentDraftJsData.data?.blocks,
            blocksCount: currentDraftJsData.data?.blocks?.length,
            firstBlockKeys: currentDraftJsData.data?.blocks?.[0] ? Object.keys(currentDraftJsData.data.blocks[0]) : [],
            firstBlockData: currentDraftJsData.data?.blocks?.[0]?.data,
            firstBlockDataKeys: currentDraftJsData.data?.blocks?.[0]?.data ? Object.keys(currentDraftJsData.data.blocks[0].data) : [],
            firstBlockSpeaker: currentDraftJsData.data?.blocks?.[0]?.data?.speaker,
            sampleBlock: currentDraftJsData.data?.blocks?.[0]
          });
          
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
        } else {
          console.warn('⚠️ getEditorContent returned null/undefined');
        }
      } else {
        console.warn('⚠️ transcriptEditorRef.current is null');
      }

      console.log('💾 Before merge:', {
        originalWordsCount: originalData.words?.length,
        editedWordsCount: updatedTranscriptData.words?.length,
        sampleOriginalWord: originalData.words?.[0],
        sampleEditedWord: updatedTranscriptData.words?.[0]
      });

      // Merge corrections back into RichWordsTranscript format
      const correctedResponse = DeepgramTransformer.mergeCorrectionsIntoDeepgramResponse(
        originalData,
        updatedTranscriptData
      );

      console.log('✅ After merge:', {
        correctedWordsCount: correctedResponse.words?.length,
        corrections: correctedResponse.corrections,
        speakerNames: correctedResponse.corrections?.speaker_names,
        paragraphStarts: correctedResponse.words?.filter(w => w.paragraph_start).length,
        paragraphEnds: correctedResponse.words?.filter(w => w.paragraph_end).length
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

