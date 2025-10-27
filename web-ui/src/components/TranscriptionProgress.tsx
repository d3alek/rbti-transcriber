/**
 * Transcription Progress component for real-time job monitoring.
 */

import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  LinearProgress,
  Alert,
  Chip,
  List,
  ListItem,
  ListItemText,
  ListItemIcon,
  Divider,
} from '@mui/material';
import {
  CheckCircle as CompletedIcon,
  Error as ErrorIcon,
  HourglassEmpty as ProcessingIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';

import type { TranscriptionJob } from '../types';
import { apiService } from '../services/api';

interface TranscriptionProgressProps {
  open: boolean;
  jobs: TranscriptionJob[];
  onClose: () => void;
  onJobComplete: (jobId: string) => void;
}

export const TranscriptionProgress: React.FC<TranscriptionProgressProps> = ({
  open,
  jobs,
  onClose,
  onJobComplete,
}) => {
  const [websockets, setWebsockets] = useState<Map<string, WebSocket>>(new Map());
  const [jobStatuses, setJobStatuses] = useState<Map<string, TranscriptionJob>>(new Map());

  useEffect(() => {
    // Initialize job statuses
    const statusMap = new Map();
    jobs.forEach(job => statusMap.set(job.id, job));
    setJobStatuses(statusMap);

    // Create WebSocket connections for each job
    const wsMap = new Map();
    jobs.forEach(job => {
      if (job.status === 'processing') {
        const ws = apiService.createTranscriptionWebSocket(job.id);
        
        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            setJobStatuses(prev => {
              const updated = new Map(prev);
              updated.set(job.id, {
                id: data.job_id,
                status: data.status,
                progress: data.progress,
                message: data.message,
                error: data.error,
              });
              return updated;
            });

            // Notify parent when job completes
            if (data.status === 'completed' || data.status === 'error') {
              onJobComplete(job.id);
            }
          } catch (err) {
            console.error('WebSocket message error:', err);
          }
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log(`WebSocket closed for job ${job.id}`);
        };

        wsMap.set(job.id, ws);
      }
    });

    setWebsockets(wsMap);

    // Cleanup on unmount
    return () => {
      wsMap.forEach(ws => ws.close());
    };
  }, [jobs, onJobComplete]);

  const handleCancelJob = async (jobId: string) => {
    try {
      await apiService.cancelTranscription(jobId);
      
      // Close WebSocket for cancelled job
      const ws = websockets.get(jobId);
      if (ws) {
        ws.close();
        setWebsockets(prev => {
          const updated = new Map(prev);
          updated.delete(jobId);
          return updated;
        });
      }

      // Update job status
      setJobStatuses(prev => {
        const updated = new Map(prev);
        const job = updated.get(jobId);
        if (job) {
          updated.set(jobId, {
            ...job,
            status: 'error',
            message: 'Cancelled by user',
          });
        }
        return updated;
      });
    } catch (err) {
      console.error('Failed to cancel job:', err);
    }
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
        return 'primary';
      default:
        return 'default';
    }
  };

  const activeJobs = Array.from(jobStatuses.values());
  const hasActiveJobs = activeJobs.some(job => job.status === 'processing');

  return (
    <Dialog 
      open={open} 
      onClose={onClose} 
      maxWidth="md" 
      fullWidth
      disableEscapeKeyDown={hasActiveJobs}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Transcription Progress</Typography>
          <Chip 
            label={`${activeJobs.length} job${activeJobs.length !== 1 ? 's' : ''}`}
            size="small"
            color="primary"
          />
        </Box>
      </DialogTitle>
      
      <DialogContent>
        {activeJobs.length === 0 ? (
          <Alert severity="info">No transcription jobs to display.</Alert>
        ) : (
          <List>
            {activeJobs.map((job, index) => (
              <React.Fragment key={job.id}>
                <ListItem>
                  <ListItemIcon>
                    {getStatusIcon(job.status)}
                  </ListItemIcon>
                  <ListItemText
                    primary={
                      <Box display="flex" justifyContent="space-between" alignItems="center">
                        <Typography variant="subtitle1">
                          Job {job.id.substring(0, 8)}...
                        </Typography>
                        <Box display="flex" gap={1} alignItems="center">
                          <Chip 
                            label={job.status.toUpperCase()} 
                            size="small"
                            color={getStatusColor(job.status) as any}
                          />
                          {job.status === 'processing' && (
                            <Button
                              size="small"
                              variant="outlined"
                              color="error"
                              startIcon={<CancelIcon />}
                              onClick={() => handleCancelJob(job.id)}
                            >
                              Cancel
                            </Button>
                          )}
                        </Box>
                      </Box>
                    }
                    secondary={
                      <Box sx={{ mt: 1 }}>
                        <Typography variant="body2" color="text.secondary" gutterBottom>
                          {job.message}
                        </Typography>
                        {job.status === 'processing' && (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                            <LinearProgress 
                              variant="determinate" 
                              value={job.progress} 
                              sx={{ flexGrow: 1 }}
                            />
                            <Typography variant="caption">
                              {Math.round(job.progress)}%
                            </Typography>
                          </Box>
                        )}
                        {job.error && (
                          <Alert severity="error" sx={{ mt: 1 }}>
                            {job.error}
                          </Alert>
                        )}
                      </Box>
                    }
                  />
                </ListItem>
                {index < activeJobs.length - 1 && <Divider />}
              </React.Fragment>
            ))}
          </List>
        )}
      </DialogContent>
      
      <DialogActions>
        <Button 
          onClick={onClose}
          disabled={hasActiveJobs}
        >
          {hasActiveJobs ? 'Jobs Running...' : 'Close'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};