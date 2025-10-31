import React, { useState, useCallback, useMemo } from 'react';
import {
  Box,
  Typography,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Button,
  Chip,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  TextField,
  InputAdornment,
} from '@material-ui/core';
import {
  ExpandMore,
  PlayArrow,
  CheckCircle,
  Error,
  HourglassEmpty,
  Search,
} from '@material-ui/icons';
import { AudioFileInfo, DirectoryScanResult, APIResponse, TranscriptionResult } from '../../types/api';

interface AudioFileListProps {
  scanResult: DirectoryScanResult;
  onFileSelect: (audioFile: AudioFileInfo) => void;
  onTranscriptionStart: (audioFile: AudioFileInfo) => void;
  apiClient: {
    startTranscription: (audioFile: string) => Promise<APIResponse<TranscriptionResult>>;
  };
}

type FilterType = 'all' | 'transcribed' | 'not-transcribed' | 'failed';

export const AudioFileList: React.FC<AudioFileListProps> = ({
  scanResult,
  onFileSelect,
  onTranscriptionStart,
  apiClient,
}) => {
  const [filter, setFilter] = useState<FilterType>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [processingFiles, setProcessingFiles] = useState<Set<string>>(new Set());

  // Use the groups_detail from the API response directly
  const groupedFiles = useMemo(() => {
    return scanResult.groups_detail || {};
  }, [scanResult.groups_detail]);

  // Filter files based on current filter and search term
  const filteredGroupedFiles = useMemo(() => {
    const filtered: { [key: string]: AudioFileInfo[] } = {};

    Object.entries(groupedFiles).forEach(([groupName, files]) => {
      const filteredFiles = files.filter(file => {
        // Apply status filter
        const statusMatch = (() => {
          switch (filter) {
            case 'transcribed':
              return file.transcription_status === 'completed';
            case 'not-transcribed':
              return file.transcription_status === 'none';
            case 'failed':
              return file.transcription_status === 'failed';
            default:
              return true;
          }
        })();

        // Apply search filter
        const searchMatch = searchTerm === '' || 
          file.filename.toLowerCase().includes(searchTerm.toLowerCase()) ||
          file.seminar_group.toLowerCase().includes(searchTerm.toLowerCase());

        return statusMatch && searchMatch;
      });

      if (filteredFiles.length > 0) {
        filtered[groupName] = filteredFiles;
      }
    });

    return filtered;
  }, [groupedFiles, filter, searchTerm]);

  const handleGroupToggle = useCallback((groupName: string) => {
    setExpandedGroups(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupName)) {
        newSet.delete(groupName);
      } else {
        newSet.add(groupName);
      }
      return newSet;
    });
  }, []);

  const handleStartTranscription = useCallback(async (audioFile: AudioFileInfo) => {
    setProcessingFiles(prev => new Set(prev).add(audioFile.path));
    
    try {
      const response = await apiClient.startTranscription(audioFile.path);
      
      if (response.success) {
        onTranscriptionStart(audioFile);
      } else {
        console.error('Transcription failed:', response.error);
        // TODO: Show error notification
      }
    } catch (error) {
      console.error('Transcription request failed:', error);
      // TODO: Show error notification
    } finally {
      setProcessingFiles(prev => {
        const newSet = new Set(prev);
        newSet.delete(audioFile.path);
        return newSet;
      });
    }
  }, [apiClient, onTranscriptionStart]);

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle style={{ color: '#4caf50' }} />;
      case 'failed':
        return <Error style={{ color: '#f44336' }} />;
      default:
        return <HourglassEmpty style={{ color: '#ff9800' }} />;
    }
  };

  const getStatusText = (file: AudioFileInfo) => {
    if (processingFiles.has(file.path)) {
      return 'Processing...';
    }
    
    switch (file.transcription_status) {
      case 'completed':
        return 'Transcribed';
      case 'failed':
        return `Failed${file.transcription_error ? `: ${file.transcription_error}` : ''}`;
      default:
        return 'Not transcribed';
    }
  };

  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Box>
      <Typography variant="h5" component="h2" gutterBottom>
        Audio Files ({scanResult.total_files} total)
      </Typography>

      {/* Filters and Search */}
      <Box display="flex" marginBottom={3} alignItems="center" flexWrap="wrap" style={{ gap: '16px' }}>
        <FormControl variant="outlined" size="small" style={{ minWidth: 150 }}>
          <InputLabel>Filter by Status</InputLabel>
          <Select
            value={filter}
            onChange={(e) => setFilter(e.target.value as FilterType)}
            label="Filter by Status"
          >
            <MenuItem value="all">All Files</MenuItem>
            <MenuItem value="transcribed">Transcribed</MenuItem>
            <MenuItem value="not-transcribed">Not Transcribed</MenuItem>
            <MenuItem value="failed">Failed</MenuItem>
          </Select>
        </FormControl>

        <TextField
          variant="outlined"
          size="small"
          placeholder="Search files..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
          style={{ minWidth: 200 }}
        />

        <Typography variant="body2" color="textSecondary">
          Showing {Object.values(filteredGroupedFiles).flat().length} of {scanResult.total_files} files
        </Typography>
      </Box>

      {/* File Groups */}
      {Object.entries(filteredGroupedFiles).map(([groupName, files]) => (
        <Accordion
          key={groupName}
          expanded={expandedGroups.has(groupName)}
          onChange={() => handleGroupToggle(groupName)}
          style={{ marginBottom: '8px' }}
        >
          <AccordionSummary expandIcon={<ExpandMore />}>
            <Box display="flex" alignItems="center" width="100%" style={{ gap: '16px' }}>
              <Typography variant="h6">{groupName}</Typography>
              <Chip
                label={`${files.length} files`}
                size="small"
                color="primary"
                variant="outlined"
              />
              <Chip
                label={`${files.filter(f => f.transcription_status === 'completed').length} transcribed`}
                size="small"
                color="secondary"
                variant="outlined"
              />
            </Box>
          </AccordionSummary>
          
          <AccordionDetails style={{ padding: 0 }}>
            <List style={{ width: '100%' }}>
              {files.map((file) => {
                const isClickable = file.transcription_status === 'completed';
                
                const ListItemComponent = isClickable ? 
                  (props: any) => <ListItem {...props} button onClick={() => onFileSelect(file)} /> :
                  (props: any) => <ListItem {...props} />;
                
                return (
                  <ListItemComponent
                    key={file.path}
                    divider
                    style={{
                      backgroundColor: isClickable ? '#f5f5f5' : 'transparent',
                    }}
                  >
                    <Box display="flex" alignItems="center" marginRight={2}>
                      {getStatusIcon(file.transcription_status)}
                    </Box>
                  
                  <ListItemText
                    primary={
                      <Box display="flex" alignItems="center" style={{ gap: '8px' }}>
                        <Typography variant="body1">{file.filename}</Typography>
                        {file.transcription_status === 'completed' && (
                          <PlayArrow style={{ color: '#1976d2', fontSize: '1rem' }} />
                        )}
                      </Box>
                    }
                    secondary={
                      <div>
                        <Typography variant="body2" color="textSecondary" component="div">
                          Status: {getStatusText(file)}
                        </Typography>
                        <Typography variant="body2" color="textSecondary" component="div">
                          Size: {formatFileSize(file.size)}
                          {file.has_compressed_version && file.compressed_size && (
                            <> (Compressed: {formatFileSize(file.compressed_size)})</>
                          )}
                          {file.duration && <> • Duration: {formatDuration(file.duration)}</>}
                        </Typography>
                        {file.last_transcription_attempt && (
                          <Typography variant="body2" color="textSecondary" component="div">
                            Last attempt: {new Date(file.last_transcription_attempt).toLocaleString()}
                          </Typography>
                        )}
                      </div>
                    }
                  />
                  
                  <ListItemSecondaryAction>
                    {file.transcription_status === 'none' && (
                      <Button
                        variant="contained"
                        color="primary"
                        size="small"
                        onClick={() => handleStartTranscription(file)}
                        disabled={processingFiles.has(file.path)}
                        startIcon={processingFiles.has(file.path) ? <HourglassEmpty /> : undefined}
                      >
                        {processingFiles.has(file.path) ? 'Starting...' : 'Start Transcription'}
                      </Button>
                    )}
                    
                    {file.transcription_status === 'failed' && (
                      <Button
                        variant="outlined"
                        color="primary"
                        size="small"
                        onClick={() => handleStartTranscription(file)}
                        disabled={processingFiles.has(file.path)}
                      >
                        Retry
                      </Button>
                    )}
                    
                    {file.transcription_status === 'completed' && (
                      <Button
                        variant="outlined"
                        color="primary"
                        size="small"
                        onClick={() => onFileSelect(file)}
                      >
                        Edit Transcript
                      </Button>
                    )}
                  </ListItemSecondaryAction>
                  </ListItemComponent>
                );
              })}
            </List>
          </AccordionDetails>
        </Accordion>
      ))}

      {Object.keys(filteredGroupedFiles).length === 0 && (
        <Typography variant="body1" color="textSecondary" style={{ textAlign: 'center', padding: '32px' }}>
          No files match the current filter criteria.
        </Typography>
      )}
    </Box>
  );
};

export default AudioFileList;