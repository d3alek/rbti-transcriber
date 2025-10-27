/**
 * Job Manager component for monitoring all transcription jobs.
 */

import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
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
  LinearProgress,
  Alert,
  Tooltip,
} from '@mui/material';
import {
  Refresh as RefreshIcon,
  Cancel as CancelIcon,
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  HourglassEmpty as ProcessingIcon,
  Queue as QueueIcon,
} from '@mui/icons-material';

import type { TranscriptionJob } from '../types';
import { apiService } from '../services/api';

export const JobManager: React.FC = () => {
  const [jobs, setJobs] = useState<Record<string, TranscriptionJob>>({});
  const [queueStatus, setQueueStatus] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadJobs();
    loadQueueStatus();
    
    // Refresh every 5 seconds
    const interval = setInterval(() => {
      loadJobs();
      loadQueueStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  const loadJobs = async () => {
    try {
      setError(null);
      const jobList = await apiService.listActiveJobs();
      setJobs(jobList);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const loadQueueStatus = async () => {
    try {
      const status = await apiService.getQueueStatus();
      setQueueStatus(status);
    } catch (err) {
      console.error('Failed to load queue status:', err);
    }
  };

  const handleCancelJob = async (jobId: string) => {
    try {
      await apiService.cancelTranscription(jobId);
      await loadJobs(); // Refresh job list
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    loadJobs();
    loadQueueStatus();
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CompletedIcon color="success" />;
      case 'error':
        return <ErrorIcon color="error" />;
      case 'processing':
        return <ProcessingIcon color="primary" />;
      default:
        return <ProcessingIcon />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'error':
        return 'error';
      case 'processing':
        return 'warning';
      default:
        return 'default';
    }
  };

  const formatJobId = (jobId: string) => {
    return jobId.substring(0, 8) + '...';
  };

  const jobList = Object.values(jobs);

  return (
    <Box>
      {/* Header */}
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h4" component="h1">
          Transcription Jobs
        </Typography>
        <Button
          variant="outlined"
          startIcon={<RefreshIcon />}
          onClick={handleRefresh}
          disabled={loading}
        >
          Refresh
        </Button>
      </Box>

      {/* Queue Status Cards */}
      {queueStatus && (
        <Box sx={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: 2, 
          mb: 3 
        }}>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <QueueIcon color="primary" />
                <Box>
                  <Typography variant="h6">{queueStatus.queue_size}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Queued Jobs
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <ProcessingIcon color="warning" />
                <Box>
                  <Typography variant="h6">{queueStatus.processing_jobs}</Typography>
                  <Typography variant="body2" color="text.secondary">
                    Processing
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h6" color="primary">
                  {queueStatus.max_concurrent}
                </Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Max Concurrent
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
          <Card>
            <CardContent>
              <Box display="flex" alignItems="center" gap={1}>
                <Typography variant="h6">{queueStatus.active_jobs}</Typography>
                <Box>
                  <Typography variant="body2" color="text.secondary">
                    Total Active
                  </Typography>
                </Box>
              </Box>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* Error Display */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }}>
          {error}
        </Alert>
      )}

      {/* Jobs Table */}
      {jobList.length === 0 ? (
        <Alert severity="info">
          No active transcription jobs.
        </Alert>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Job ID</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Progress</TableCell>
                <TableCell>Message</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {jobList.map((job) => (
                <TableRow key={job.id} hover>
                  <TableCell>
                    <Box display="flex" alignItems="center" gap={1}>
                      {getStatusIcon(job.status)}
                      <Typography variant="body2" fontFamily="monospace">
                        {formatJobId(job.id)}
                      </Typography>
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={job.status.toUpperCase()}
                      color={getStatusColor(job.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Box sx={{ minWidth: 120 }}>
                      {job.status === 'processing' ? (
                        <Box>
                          <LinearProgress 
                            variant="determinate" 
                            value={job.progress} 
                            sx={{ mb: 0.5 }}
                          />
                          <Typography variant="caption">
                            {Math.round(job.progress)}%
                          </Typography>
                        </Box>
                      ) : (
                        <Typography variant="body2">
                          {job.status === 'completed' ? '100%' : '-'}
                        </Typography>
                      )}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {job.message}
                    </Typography>
                    {job.error && (
                      <Typography variant="caption" color="error">
                        Error: {job.error}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    {job.status === 'processing' && (
                      <Tooltip title="Cancel Job">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleCancelJob(job.id)}
                        >
                          <CancelIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};