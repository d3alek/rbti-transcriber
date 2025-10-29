/**
 * TranscriptEditor Component
 * 
 * Main component for editing transcripts with real-time audio synchronization,
 * paragraph-based editing, and version management.
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Box, Container, Paper, Typography, Alert, CircularProgress } from '@mui/material';
import type { 
  DeepgramVersion, 
  ParagraphData, 
  TranscriptEditorState,
  WordData,
  DeepgramResponse 
} from '../types/deepgram';
import { transcriptVersionsApi } from '../services/transcriptVersionsApi';
import ParagraphEditor from './ParagraphEditor';
import AudioPlayer from './AudioPlayer';
import VersionManager from './VersionManager';

interface TranscriptEditorComponentProps {
  file: { path: string; name: string; hash?: string };
  onBack?: () => void;
  onError?: (error: string) => void;
}

const TranscriptEditor: React.FC<TranscriptEditorComponentProps> = ({
  file,
  onError
}) => {
  const audioHash = file.hash || file.name;
  const audioFile = file.path;
  // State management
  const [state, setState] = useState<TranscriptEditorState>({
    currentPlaybackTime: 0,
    activeWordIndex: -1,
    editingParagraph: null,
    paragraphs: [],
    hasUnsavedChanges: false
  });

  const [versions, setVersions] = useState<DeepgramVersion[]>([]);
  const [currentVersion, setCurrentVersion] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [audioDuration, setAudioDuration] = useState<number>(0);
  const [overallConfidence, setOverallConfidence] = useState<number>(0);

  // Refs for performance optimization
  const paragraphsRef = useRef<ParagraphData[]>([]);
  const wordsRef = useRef<WordData[]>([]);
  const currentResponseRef = useRef<DeepgramResponse | null>(null);

  // Load versions on component mount
  useEffect(() => {
    loadVersions();
  }, [audioHash]);

  // Update refs when paragraphs change
  useEffect(() => {
    paragraphsRef.current = state.paragraphs;
    
    // Flatten all words for efficient lookup
    const allWords: WordData[] = [];
    state.paragraphs.forEach(paragraph => {
      allWords.push(...paragraph.words);
    });
    wordsRef.current = allWords;
  }, [state.paragraphs]);

  const loadVersions = async () => {
    try {
      setLoading(true);
      setError(null);

      // First try to initialize from cache if no versions exist
      try {
        await transcriptVersionsApi.initializeFromCache(audioHash);
      } catch (initError) {
        // Ignore initialization errors - versions might already exist
      }

      // Load available versions
      const versionsResponse = await transcriptVersionsApi.listVersions(audioHash);
      const versionsList = versionsResponse.versions.map(v => ({
        version: v.version,
        filename: v.filename,
        timestamp: v.timestamp,
        changes: v.changes,
        response: {} as DeepgramResponse // Will be loaded when needed
      }));

      setVersions(versionsList);
      
      if (versionsList.length > 0) {
        // Load the latest version
        const latestVersion = Math.max(...versionsList.map(v => v.version));
        await loadVersion(latestVersion);
      } else {
        setError('No transcript versions found. Please ensure the audio file has been transcribed.');
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load versions';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const loadVersion = async (versionNumber: number) => {
    try {
      setLoading(true);
      
      const response = await transcriptVersionsApi.loadVersion(audioHash, versionNumber);
      
      // Update state with loaded data
      setState(prev => ({
        ...prev,
        paragraphs: response.paragraphs,
        hasUnsavedChanges: false,
        editingParagraph: null
      }));

      setCurrentVersion(versionNumber);
      setAudioDuration(response.audio_duration);
      setOverallConfidence(response.confidence);

      // Store the response for editing operations
      // Note: We would need to fetch the full response separately for editing
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load version';
      setError(errorMessage);
      onError?.(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleVersionChange = useCallback(async (version: number) => {
    if (state.hasUnsavedChanges) {
      const confirmSwitch = window.confirm(
        'You have unsaved changes. Switching versions will lose these changes. Continue?'
      );
      if (!confirmSwitch) return;
    }

    await loadVersion(version);
  }, [state.hasUnsavedChanges, audioHash]);

  const handleSaveVersion = useCallback(async () => {
    if (!currentResponseRef.current) {
      setError('No response data available for saving');
      return;
    }

    try {
      const changes = prompt('Describe the changes made in this version:');
      if (changes === null) return; // User cancelled

      await transcriptVersionsApi.saveVersion(audioHash, {
        changes: changes || 'Manual edit',
        response: currentResponseRef.current
      });

      // Reload versions to get the updated list
      await loadVersions();
      
      setState(prev => ({
        ...prev,
        hasUnsavedChanges: false
      }));

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to save version';
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, [audioHash]);

  const handleTimeUpdate = useCallback((time: number) => {
    setState(prev => ({ ...prev, currentPlaybackTime: time }));

    // Find the active word at current time
    const activeWord = wordsRef.current.find(word => 
      word.start <= time && word.end >= time
    );

    if (activeWord && activeWord.index !== undefined) {
      setState(prev => ({ ...prev, activeWordIndex: activeWord.index! }));
    }
  }, []);

  const handleSeek = useCallback((time: number) => {
    setState(prev => ({ ...prev, currentPlaybackTime: time }));
  }, []);

  const handleParagraphEdit = useCallback(async (paragraphId: string, newText: string) => {
    try {
      // Update local state immediately for responsive UI
      setState(prev => ({
        ...prev,
        paragraphs: prev.paragraphs.map(p => 
          p.id === paragraphId ? { ...p, text: newText } : p
        ),
        hasUnsavedChanges: true
      }));

      // TODO: Update the Deepgram response with new text
      // This would require calling the paragraph update API and recalculating timing
      
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to update paragraph';
      setError(errorMessage);
      onError?.(errorMessage);
    }
  }, []);

  const handleStartEdit = useCallback((paragraphId: string) => {
    setState(prev => ({ ...prev, editingParagraph: paragraphId }));
  }, []);

  const handleEndEdit = useCallback(() => {
    setState(prev => ({ ...prev, editingParagraph: null }));
  }, []);

  const handleWordClick = useCallback((word: WordData) => {
    // Seek to the word's start time
    handleSeek(word.start);
  }, [handleSeek]);

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Loading transcript...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          {error}
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        {/* Header */}
        <Paper sx={{ p: 2 }}>
          <Typography variant="h4" gutterBottom>
            Transcript Editor
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Audio: {audioFile} | Duration: {Math.round(audioDuration)}s | 
            Confidence: {Math.round(overallConfidence * 100)}%
            {state.hasUnsavedChanges && (
              <Typography component="span" color="warning.main" sx={{ ml: 1 }}>
                • Unsaved changes
              </Typography>
            )}
          </Typography>
        </Paper>

        {/* Audio Player */}
        <Paper sx={{ p: 2 }}>
          <AudioPlayer
            audioFile={audioFile}
            currentTime={state.currentPlaybackTime}
            onTimeUpdate={handleTimeUpdate}
            onSeek={handleSeek}
            duration={audioDuration}
          />
        </Paper>

        {/* Main Content */}
        <Box sx={{ display: 'flex', gap: 2, flexDirection: { xs: 'column', md: 'row' } }}>
          {/* Transcript Content */}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Paper sx={{ p: 2, maxHeight: '70vh', overflow: 'auto' }}>
              <Typography variant="h6" gutterBottom>
                Transcript
              </Typography>
              
              {state.paragraphs.map((paragraph) => (
                <ParagraphEditor
                  key={paragraph.id}
                  paragraph={paragraph}
                  isEditing={state.editingParagraph === paragraph.id}
                  currentPlaybackTime={state.currentPlaybackTime}
                  onEdit={handleParagraphEdit}
                  onStartEdit={handleStartEdit}
                  onEndEdit={handleEndEdit}
                  showConfidenceIndicators={true}
                  onWordClick={handleWordClick}
                />
              ))}

              {state.paragraphs.length === 0 && (
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  No transcript content available
                </Typography>
              )}
            </Paper>
          </Box>

          {/* Version Manager Sidebar */}
          <Box sx={{ width: { xs: '100%', md: '300px' }, flexShrink: 0 }}>
            <VersionManager
              versions={versions}
              currentVersion={currentVersion}
              onVersionSelect={handleVersionChange}
              onSaveVersion={handleSaveVersion}
              canSave={state.hasUnsavedChanges}
              isLoading={loading}
            />
          </Box>
        </Box>
      </Box>
    </Container>
  );
};

export default TranscriptEditor;
export { TranscriptEditor };