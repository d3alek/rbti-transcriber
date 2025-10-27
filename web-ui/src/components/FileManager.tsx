/**
 * File Manager component for browsing and managing audio files.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  TextField,
  InputAdornment,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  FormControlLabel,
  Checkbox,
} from '@mui/material';
import {
  Search as SearchIcon,
  Refresh as RefreshIcon,
  Edit as EditIcon,
  CloudUpload as TranscribeIcon,
  Public as PublishIcon,
  ViewList as TableViewIcon,
  ViewModule as GridViewIcon,
  GetApp as DownloadIcon,
} from '@mui/icons-material';

import type { AudioFile, TranscriptionRequest, TranscriptionJob } from '../types';
import { apiService } from '../services/api';
import { TranscriptionProgress } from './TranscriptionProgress';

interface FileManagerProps {
  onFileSelect: (file: AudioFile) => void;
  onTranscriptionStart: (request: TranscriptionRequest) => void;
}

export const FileManager: React.FC<FileManagerProps> = ({ onFileSelect, onTranscriptionStart }) => {
  const [files, setFiles] = useState<AudioFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [transcribeDialogOpen, setTranscribeDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<AudioFile | null>(null);
  const [transcriptionService, setTranscriptionService] = useState<'assemblyai' | 'deepgram'>('deepgram');
  const [viewMode, setViewMode] = useState<'table' | 'grid'>('table');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [sortBy, setSortBy] = useState<'name' | 'size' | 'duration' | 'modified'>('name');
  const [sortOrder] = useState<'asc' | 'desc'>('asc');
  const [compressAudio, setCompressAudio] = useState(true);
  const [outputFormats, setOutputFormats] = useState<string[]>(['html', 'markdown']);
  const [activeJobs, setActiveJobs] = useState<TranscriptionJob[]>([]);
  const [progressDialogOpen, setProgressDialogOpen] = useState(false);

  useEffect(() => {
    loadFiles();
  }, []);

  const loadFiles = async () => {
    try {
      setLoading(true);
      setError(null);
      const fileList = await apiService.listFiles();
      setFiles(fileList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    await apiService.scanFiles();
    await loadFiles();
  };

  const handleTranscribeClick = (file: AudioFile) => {
    setSelectedFile(file);
    setTranscribeDialogOpen(true);
  };

  const handleTranscribeConfirm = async () => {
    if (selectedFile) {
      try {
        const request: TranscriptionRequest = {
          file_id: selectedFile.id,
          service: transcriptionService,
          compress_audio: compressAudio,
          output_formats: outputFormats,
        };
        
        // Start transcription
        const response = await apiService.startTranscription(request);
        
        if (response.success && response.data?.job_id) {
          // Create job object for progress tracking
          const job: TranscriptionJob = {
            id: response.data.job_id,
            status: 'processing',
            progress: 0,
            message: 'Starting transcription...',
          };
          
          setActiveJobs(prev => [...prev, job]);
          setProgressDialogOpen(true);
        }
        
        onTranscriptionStart(request);
        setTranscribeDialogOpen(false);
        setSelectedFile(null);
      } catch (err) {
        console.error('Failed to start transcription:', err);
        // TODO: Show error message to user
      }
    }
  };

  const handleJobComplete = (jobId: string) => {
    // Remove completed job from active jobs
    setActiveJobs(prev => prev.filter(job => job.id !== jobId));
    
    // Refresh file list to show updated transcription status
    loadFiles();
  };

  const handleProgressDialogClose = () => {
    // Only close if no jobs are still processing
    const hasProcessingJobs = activeJobs.some(job => job.status === 'processing');
    if (!hasProcessingJobs) {
      setProgressDialogOpen(false);
      setActiveJobs([]);
    }
  };

  const formatFileSize = (bytes: number): string => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const formatDuration = (seconds: number): string => {
    if (seconds === 0) return 'Unknown';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const formatDate = (dateString: string): string => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const getStatusChip = (status: string) => {
    const statusConfig = {
      completed: { color: 'success' as const, label: 'Completed' },
      processing: { color: 'warning' as const, label: 'Processing' },
      error: { color: 'error' as const, label: 'Error' },
      none: { color: 'default' as const, label: 'Not Transcribed' },
    };
    
    const config = statusConfig[status as keyof typeof statusConfig] || statusConfig.none;
    return <Chip color={config.color} label={config.label} size="small" />;
  };

  const filteredAndSortedFiles = files
    .filter(file => {
      const matchesSearch = file.name.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesStatus = statusFilter === 'all' || file.transcription_status === statusFilter;
      return matchesSearch && matchesStatus;
    })
    .sort((a, b) => {
      let comparison = 0;
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name);
          break;
        case 'size':
          comparison = a.size - b.size;
          break;
        case 'duration':
          comparison = a.duration - b.duration;
          break;
        case 'modified':
          comparison = new Date(a.last_modified).getTime() - new Date(b.last_modified).getTime();
          break;
      }
      return sortOrder === 'asc' ? comparison : -comparison;
    });

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const renderGridView = () => (
    <Box sx={{ 
      display: 'grid', 
      gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', 
      gap: 2 
    }}>
      {filteredAndSortedFiles.map((file) => (
        <Card key={file.id} sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <CardContent sx={{ flexGrow: 1 }}>
            <Typography variant="h6" component="div" noWrap title={file.name}>
              {file.name}
            </Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
              {formatFileSize(file.size)} • {formatDuration(file.duration)}
            </Typography>
            <Box sx={{ mb: 2 }}>
              {getStatusChip(file.transcription_status)}
            </Box>
            <Typography variant="caption" display="block" gutterBottom>
              Modified: {formatDate(file.last_modified)}
            </Typography>
          </CardContent>
          <Box sx={{ p: 2, pt: 0 }}>
            {file.has_transcription ? (
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  size="small"
                  variant="contained"
                  startIcon={<EditIcon />}
                  onClick={() => onFileSelect(file)}
                  fullWidth
                >
                  Edit
                </Button>
                <Tooltip title="Download">
                  <IconButton size="small" color="secondary">
                    <DownloadIcon />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Publish">
                  <IconButton size="small" color="primary">
                    <PublishIcon />
                  </IconButton>
                </Tooltip>
              </Box>
            ) : (
              <Button
                size="small"
                variant="contained"
                startIcon={<TranscribeIcon />}
                onClick={() => handleTranscribeClick(file)}
                fullWidth
              >
                Transcribe
              </Button>
            )}
          </Box>
        </Card>
      ))}
    </Box>
  );

  const renderTableView = () => (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Name</TableCell>
            <TableCell>Size</TableCell>
            <TableCell>Duration</TableCell>
            <TableCell>Status</TableCell>
            <TableCell>Last Modified</TableCell>
            <TableCell>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {filteredAndSortedFiles.map((file) => (
            <TableRow key={file.id} hover>
              <TableCell>
                <Typography variant="body2" fontWeight="medium">
                  {file.name}
                </Typography>
              </TableCell>
              <TableCell>{formatFileSize(file.size)}</TableCell>
              <TableCell>{formatDuration(file.duration)}</TableCell>
              <TableCell>{getStatusChip(file.transcription_status)}</TableCell>
              <TableCell>{formatDate(file.last_modified)}</TableCell>
              <TableCell>
                <Box display="flex" gap={1}>
                  {file.has_transcription ? (
                    <>
                      <Tooltip title="Edit Transcription">
                        <IconButton
                          size="small"
                          color="primary"
                          onClick={() => onFileSelect(file)}
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Download">
                        <IconButton size="small" color="secondary">
                          <DownloadIcon />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Publish">
                        <IconButton size="small" color="primary">
                          <PublishIcon />
                        </IconButton>
                      </Tooltip>
                    </>
                  ) : (
                    <Tooltip title="Start Transcription">
                      <IconButton
                        size="small"
                        color="primary"
                        onClick={() => handleTranscribeClick(file)}
                      >
                        <TranscribeIcon />
                      </IconButton>
                    </Tooltip>
                  )}
                </Box>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );

  return (
    <Box>
      {/* Debug Info */}
      <Alert severity="info" sx={{ mb: 2 }}>
        FileManager loaded. Loading: {loading.toString()}, Files: {files.length}, Error: {error || 'none'}
      </Alert>
      
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Audio Files
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
        >
          Refresh
        </Button>
      </Box>

      {/* Controls */}
      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
        {/* Search */}
        <TextField
          placeholder="Search files..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
          sx={{ minWidth: 300 }}
        />

        {/* Status Filter */}
        <FormControl sx={{ minWidth: 150 }}>
          <InputLabel>Status</InputLabel>
          <Select
            value={statusFilter}
            label="Status"
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="completed">Completed</MenuItem>
            <MenuItem value="processing">Processing</MenuItem>
            <MenuItem value="error">Error</MenuItem>
            <MenuItem value="none">Not Transcribed</MenuItem>
          </Select>
        </FormControl>

        {/* Sort By */}
        <FormControl sx={{ minWidth: 120 }}>
          <InputLabel>Sort By</InputLabel>
          <Select
            value={sortBy}
            label="Sort By"
            onChange={(e) => setSortBy(e.target.value as any)}
          >
            <MenuItem value="name">Name</MenuItem>
            <MenuItem value="size">Size</MenuItem>
            <MenuItem value="duration">Duration</MenuItem>
            <MenuItem value="modified">Modified</MenuItem>
          </Select>
        </FormControl>

        {/* View Mode Toggle */}
        <ToggleButtonGroup
          value={viewMode}
          exclusive
          onChange={(_, newMode) => newMode && setViewMode(newMode)}
          aria-label="view mode"
        >
          <ToggleButton value="table" aria-label="table view">
            <TableViewIcon />
          </ToggleButton>
          <ToggleButton value="grid" aria-label="grid view">
            <GridViewIcon />
          </ToggleButton>
        </ToggleButtonGroup>

        {/* File Count */}
        <Typography variant="body2" color="text.secondary" sx={{ ml: 'auto' }}>
          {filteredAndSortedFiles.length} of {files.length} files
        </Typography>
      </Box>

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* File List */}
      {filteredAndSortedFiles.length === 0 ? (
        <Alert severity="info">
          {searchTerm || statusFilter !== 'all' ? 'No files match your filters.' : 'No audio files found.'}
        </Alert>
      ) : (
        viewMode === 'table' ? renderTableView() : renderGridView()
      )}

      {/* Transcription Dialog */}
      <Dialog open={transcribeDialogOpen} onClose={() => setTranscribeDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Start Transcription</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            {/* File Info */}
            <Box sx={{ mb: 3, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
              <Typography variant="h6" gutterBottom>
                {selectedFile?.name}
              </Typography>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Chip label={selectedFile ? formatFileSize(selectedFile.size) : ''} size="small" />
                <Chip label={selectedFile ? formatDuration(selectedFile.duration) : ''} size="small" />
              </Box>
            </Box>

            {/* Service Selection */}
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Transcription Service</InputLabel>
              <Select
                value={transcriptionService}
                label="Transcription Service"
                onChange={(e) => setTranscriptionService(e.target.value as 'assemblyai' | 'deepgram')}
              >
                <MenuItem value="deepgram">Deepgram (Recommended)</MenuItem>
                <MenuItem value="assemblyai">AssemblyAI</MenuItem>
              </Select>
            </FormControl>

            {/* Audio Compression */}
            <FormControlLabel
              control={
                <Checkbox
                  checked={compressAudio}
                  onChange={(e) => setCompressAudio(e.target.checked)}
                />
              }
              label="Compress audio before upload (recommended)"
              sx={{ mb: 2 }}
            />

            {/* Output Formats */}
            <Typography variant="subtitle2" gutterBottom>
              Output Formats:
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              {['html', 'markdown', 'txt'].map((format) => (
                <FormControlLabel
                  key={format}
                  control={
                    <Checkbox
                      checked={outputFormats.includes(format)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setOutputFormats([...outputFormats, format]);
                        } else {
                          setOutputFormats(outputFormats.filter(f => f !== format));
                        }
                      }}
                    />
                  }
                  label={format.toUpperCase()}
                />
              ))}
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setTranscribeDialogOpen(false)}>Cancel</Button>
          <Button 
            onClick={handleTranscribeConfirm} 
            variant="contained"
            disabled={outputFormats.length === 0}
          >
            Start Transcription
          </Button>
        </DialogActions>
      </Dialog>

      {/* Transcription Progress Dialog */}
      <TranscriptionProgress
        open={progressDialogOpen}
        jobs={activeJobs}
        onClose={handleProgressDialogClose}
        onJobComplete={handleJobComplete}
      />
    </Box>
  );
};