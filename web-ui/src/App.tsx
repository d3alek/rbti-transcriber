import React, { useState, useCallback } from 'react';
import { CssBaseline, Container, Box } from '@material-ui/core';
import { createTheme, ThemeProvider } from '@material-ui/core/styles';
import { FileManager } from './components/FileManager';
import { TranscriptEditor } from './components/TranscriptEditor';
import { APIClient } from './services/APIClient';
import { AudioFileInfo } from './types/api';

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
});

function App() {
  const [selectedFile, setSelectedFile] = useState<AudioFileInfo | null>(null);
  const [currentView, setCurrentView] = useState<'fileManager' | 'transcriptEditor'>('fileManager');
  
  // Initialize API client
  const apiClient = new APIClient();

  const handleFileSelect = useCallback((audioFile: AudioFileInfo) => {
    setSelectedFile(audioFile);
    setCurrentView('transcriptEditor');
  }, []);

  const handleBackToFileManager = useCallback(() => {
    setSelectedFile(null);
    setCurrentView('fileManager');
  }, []);

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Container maxWidth="xl">
        <Box style={{ padding: '24px 0' }}>
          {currentView === 'fileManager' && (
            <FileManager
              onFileSelect={handleFileSelect}
              apiClient={apiClient}
            />
          )}
          
          {currentView === 'transcriptEditor' && selectedFile && (
            <TranscriptEditor
              audioFile={selectedFile}
              onBack={handleBackToFileManager}
              apiClient={apiClient}
            />
          )}
        </Box>
      </Container>
    </ThemeProvider>
  );
}

export default App;