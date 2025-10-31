import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  Box,
  Button,
  Typography,
  CircularProgress,
  TextField,
  Paper,
  IconButton,
} from '@material-ui/core';
import { Alert } from '@material-ui/lab';
import { FolderOpen, Refresh } from '@material-ui/icons';
import { DirectoryScanResult, APIResponse } from '../../types/api';

interface DirectorySelectorProps {
  onDirectorySelected: (scanResult: DirectoryScanResult) => void;
  apiClient: {
    scanDirectory: (path: string) => Promise<APIResponse<DirectoryScanResult>>;
  };
}

export const DirectorySelector: React.FC<DirectorySelectorProps> = ({
  onDirectorySelected,
  apiClient,
}) => {
  const [selectedPath, setSelectedPath] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastScanResult, setLastScanResult] = useState<DirectoryScanResult | null>(null);
  const isMountedRef = useRef(true);

  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  const handleDirectorySelect = useCallback(async () => {
    if (!selectedPath.trim()) {
      setError('Please enter a directory path');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await apiClient.scanDirectory(selectedPath.trim());
      
      if (!isMountedRef.current) return; // Prevent state updates on unmounted component
      
      if (response.success && response.data) {
        setLastScanResult(response.data);
        onDirectorySelected(response.data);
        setError(null);
      } else {
        setError(response.error || 'Failed to scan directory');
        setLastScanResult(null);
      }
    } catch (err) {
      if (!isMountedRef.current) return; // Prevent state updates on unmounted component
      
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      
      // Check if it's a network error (API not running)
      if (errorMessage.includes('fetch') || errorMessage.includes('NetworkError') || errorMessage.includes('Failed to fetch')) {
        setError('Cannot connect to the API server. Please make sure the backend API is running on http://localhost:8000');
      } else {
        setError(`Directory access failed: ${errorMessage}`);
      }
      setLastScanResult(null);
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [selectedPath, apiClient, onDirectorySelected]);

  const handleRefresh = useCallback(async () => {
    if (selectedPath.trim()) {
      await handleDirectorySelect();
    }
  }, [selectedPath, handleDirectorySelect]);

  const handlePathChange = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    setSelectedPath(event.target.value);
    setError(null); // Clear error when user starts typing
  }, []);

  const handleKeyPress = useCallback((event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !isLoading) {
      handleDirectorySelect();
    }
  }, [handleDirectorySelect, isLoading]);

  return (
    <Paper elevation={2} style={{ padding: '24px', marginBottom: '24px' }}>
      <Typography variant="h5" component="h2" gutterBottom>
        Select Audio Directory
      </Typography>
      
      <Box display="flex" alignItems="center" marginBottom={2} style={{ gap: '16px' }}>
        <TextField
          fullWidth
          label="Directory Path"
          placeholder="/path/to/audio/files"
          value={selectedPath}
          onChange={handlePathChange}
          onKeyPress={handleKeyPress}
          disabled={isLoading}
          variant="outlined"
          helperText="Enter the path to a directory containing MP3 audio files"
        />
        
        <Button
          variant="contained"
          color="primary"
          onClick={handleDirectorySelect}
          disabled={isLoading || !selectedPath.trim()}
          startIcon={isLoading ? <CircularProgress size={20} /> : <FolderOpen />}
          style={{ minWidth: '120px' }}
        >
          {isLoading ? 'Scanning...' : 'Scan'}
        </Button>
        
        {lastScanResult && (
          <IconButton
            onClick={handleRefresh}
            disabled={isLoading}
            title="Refresh directory scan"
            color="primary"
          >
            <Refresh />
          </IconButton>
        )}
      </Box>

      {error && (
        <Alert severity="error" style={{ marginBottom: '16px' }}>
          {error}
        </Alert>
      )}

      {lastScanResult && !error && (
        <Alert severity="success" style={{ marginBottom: '16px' }}>
          <Typography variant="body2">
            Found {lastScanResult.total_files} audio files in {lastScanResult.seminar_groups?.length || 0} seminar groups.
            {lastScanResult.transcribed_files > 0 && (
              <> {lastScanResult.transcribed_files} files already have transcriptions.</>
            )}
          </Typography>
        </Alert>
      )}

      <Typography variant="body2" color="textSecondary">
        The system will scan for MP3 files and organize them by their parent directory names as seminar groups.
        Existing transcription files will be detected automatically.
      </Typography>
    </Paper>
  );
};

export default DirectorySelector;