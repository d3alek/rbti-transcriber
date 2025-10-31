import React, { useState, useCallback } from 'react';
import {
  Box,
  Button,
  Typography,
  Paper,
  Divider,
  Snackbar,
} from '@material-ui/core';
import { Alert } from '@material-ui/lab';
import { Refresh } from '@material-ui/icons';
import { DirectorySelector } from './DirectorySelector';
import { AudioFileList } from './AudioFileList';
import { TranscriptionProgress } from './StatusIndicators';
import { 
  DirectoryScanResult, 
  AudioFileInfo, 
  APIResponse, 
  TranscriptionResult,
  TranscriptionStatus 
} from '../../types/api';

interface FileManagerProps {
  onFileSelect: (audioFile: AudioFileInfo) => void;
  apiClient: {
    scanDirectory: (path: string) => Promise<APIResponse<DirectoryScanResult>>;
    startTranscription: (audioFile: string) => Promise<APIResponse<TranscriptionResult>>;
    getTranscriptionStatus: (audioFile: string) => Promise<APIResponse<TranscriptionStatus>>;
  };
}

export const FileManager: React.FC<FileManagerProps> = ({
  onFileSelect,
  apiClient,
}) => {
  const [scanResult, setScanResult] = useState<DirectoryScanResult | null>(null);
  const [currentDirectory, setCurrentDirectory] = useState<string>('');
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [notification, setNotification] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info' | 'warning';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  const showNotification = useCallback((message: string, severity: 'success' | 'error' | 'info' | 'warning' = 'info') => {
    setNotification({
      open: true,
      message,
      severity,
    });
  }, []);

  const handleDirectorySelected = useCallback((result: DirectoryScanResult, directoryPath?: string) => {
    setScanResult(result);
    if (directoryPath) {
      setCurrentDirectory(directoryPath);
    }
    
    showNotification(
      `Found ${result.total_files} audio files in ${result.seminar_groups.length} seminar groups`,
      'success'
    );
  }, [showNotification]);

  const handleRefreshStatus = useCallback(async () => {
    if (!scanResult || !currentDirectory) {
      showNotification('No directory selected to refresh', 'warning');
      return;
    }

    setIsRefreshing(true);
    
    try {
      // Re-scan the directory to get updated status
      const response = await apiClient.scanDirectory(currentDirectory);
      
      if (response.success && response.data) {
        setScanResult(response.data);
        
        // Check if there are any status changes
        const newTranscribed = response.data.transcribed_files;
        const oldTranscribed = scanResult.transcribed_files;
        
        if (newTranscribed > oldTranscribed) {
          showNotification(
            `Status updated: ${newTranscribed - oldTranscribed} new transcriptions completed`,
            'success'
          );
        } else {
          showNotification('File statuses refreshed', 'info');
        }
      } else {
        showNotification(response.error || 'Failed to refresh file statuses', 'error');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      showNotification(`Refresh failed: ${errorMessage}`, 'error');
    } finally {
      setIsRefreshing(false);
    }
  }, [scanResult, currentDirectory, apiClient, showNotification]);

  const handleTranscriptionStart = useCallback((audioFile: AudioFileInfo) => {
    showNotification(
      `Transcription started for ${audioFile.filename}. Refresh the page to check status.`,
      'info'
    );
  }, [showNotification]);

  const handleFileSelect = useCallback((audioFile: AudioFileInfo) => {
    onFileSelect(audioFile);
  }, [onFileSelect]);

  const handleCloseNotification = useCallback(() => {
    setNotification(prev => ({ ...prev, open: false }));
  }, []);

  // Enhanced API client that captures directory path
  const enhancedApiClient = {
    ...apiClient,
    scanDirectory: async (path: string) => {
      setCurrentDirectory(path);
      return apiClient.scanDirectory(path);
    },
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Audio File Manager
      </Typography>
      
      <DirectorySelector
        onDirectorySelected={handleDirectorySelected}
        apiClient={enhancedApiClient}
      />

      {scanResult && (
        <>
          <Paper elevation={2} style={{ padding: '16px', marginBottom: '24px' }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" marginBottom={2}>
              <Typography variant="h6">
                Directory Status
              </Typography>
              <Button
                variant="outlined"
                color="primary"
                onClick={handleRefreshStatus}
                disabled={isRefreshing}
                startIcon={<Refresh />}
              >
                {isRefreshing ? 'Refreshing...' : 'Refresh Status'}
              </Button>
            </Box>
            
            <TranscriptionProgress
              totalFiles={scanResult.total_files}
              transcribedFiles={scanResult.transcribed_files}
              failedFiles={scanResult.audio_files.filter(f => f.transcription_status === 'failed').length}
              showDetails={true}
            />
            
            <Divider style={{ margin: '16px 0' }} />
            
            <Box display="flex" style={{ gap: '32px' }}>
              <Typography variant="body2" color="textSecondary">
                <strong>Directory:</strong> {currentDirectory}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                <strong>Seminar Groups:</strong> {scanResult.seminar_groups.length}
              </Typography>
              <Typography variant="body2" color="textSecondary">
                <strong>Total Files:</strong> {scanResult.total_files}
              </Typography>
            </Box>
          </Paper>

          <AudioFileList
            scanResult={scanResult}
            onFileSelect={handleFileSelect}
            onTranscriptionStart={handleTranscriptionStart}
            apiClient={apiClient}
          />
        </>
      )}

      {!scanResult && (
        <Paper elevation={1} style={{ padding: '32px', textAlign: 'center', marginTop: '24px' }}>
          <Typography variant="h6" color="textSecondary" gutterBottom>
            No Directory Selected
          </Typography>
          <Typography variant="body1" color="textSecondary">
            Select a directory containing MP3 audio files to get started.
            The system will scan for files and organize them by seminar groups.
          </Typography>
        </Paper>
      )}

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

export default FileManager;