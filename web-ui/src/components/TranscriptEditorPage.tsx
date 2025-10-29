/**
 * TranscriptEditorPage Component
 * 
 * Main page component that integrates the enhanced transcript editor
 * with audio file selection and routing.
 */

import React, { useState } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Alert, 
  CircularProgress,
  Paper,
  Button
} from '@mui/material';
import { ArrowBack as ArrowBackIcon } from '@mui/icons-material';
import TranscriptEditor from './TranscriptEditor';

interface TranscriptEditorPageProps {
  audioHash?: string;
  audioFile?: string;
  onBack?: () => void;
}

const TranscriptEditorPage: React.FC<TranscriptEditorPageProps> = ({
  audioHash,
  audioFile,
  onBack
}) => {
  const [error, setError] = useState<string | null>(null);
  const [loading] = useState(false);

  // Generate audio hash from file path if not provided
  const getAudioHash = (filePath: string): string => {
    // Simple hash generation - in production, this should match the backend logic
    return btoa(filePath).replace(/[^a-zA-Z0-9]/g, '').substring(0, 16);
  };

  const currentAudioHash = audioHash || (audioFile ? getAudioHash(audioFile) : '');
  const currentAudioFile = audioFile || 'test_audio/RBTI-Animal-Husbandry-T01.mp3';

  const handleError = (errorMessage: string) => {
    setError(errorMessage);
  };

  const handleClearError = () => {
    setError(null);
  };

  if (!currentAudioHash) {
    return (
      <Container maxWidth="lg">
        <Alert severity="error" sx={{ mt: 2 }}>
          No audio file specified. Please select an audio file to edit its transcript.
        </Alert>
      </Container>
    );
  }

  return (
    <Box sx={{ minHeight: '100vh', backgroundColor: 'background.default' }}>
      {/* Header */}
      <Paper sx={{ p: 2, mb: 2 }} elevation={1}>
        <Container maxWidth="xl">
          <Box display="flex" alignItems="center" gap={2}>
            {onBack && (
              <Button
                startIcon={<ArrowBackIcon />}
                onClick={onBack}
                variant="outlined"
              >
                Back
              </Button>
            )}
            <Box>
              <Typography variant="h4" component="h1">
                Enhanced Transcript Editor
              </Typography>
              <Typography variant="subtitle1" color="text.secondary">
                Edit transcripts with real-time audio synchronization and version management
              </Typography>
            </Box>
          </Box>
        </Container>
      </Paper>

      {/* Error Display */}
      {error && (
        <Container maxWidth="xl">
          <Alert 
            severity="error" 
            sx={{ mb: 2 }}
            onClose={handleClearError}
          >
            {error}
          </Alert>
        </Container>
      )}

      {/* Loading State */}
      {loading && (
        <Container maxWidth="xl">
          <Box display="flex" justifyContent="center" alignItems="center" py={4}>
            <CircularProgress />
            <Typography variant="body1" sx={{ ml: 2 }}>
              Loading transcript editor...
            </Typography>
          </Box>
        </Container>
      )}

      {/* Main Editor */}
      {!loading && (
        <TranscriptEditor
          file={{ path: currentAudioFile, name: currentAudioFile, hash: currentAudioHash }}
          onError={handleError}
        />
      )}
    </Box>
  );
};

export default TranscriptEditorPage;