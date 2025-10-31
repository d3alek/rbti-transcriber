import React from 'react';
import {
  Box,
  Chip,
  Tooltip,
  Typography,
  LinearProgress,
} from '@material-ui/core';
import {
  CheckCircle,
  Error,
  HourglassEmpty,
  Warning,
  Info,
} from '@material-ui/icons';
import { AudioFileInfo } from '../../types/api';

interface StatusIndicatorProps {
  file: AudioFileInfo;
  isProcessing?: boolean;
  showDetails?: boolean;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  file,
  isProcessing = false,
  showDetails = false,
}) => {
  const getStatusConfig = () => {
    if (isProcessing) {
      return {
        icon: <HourglassEmpty />,
        color: '#ff9800' as const,
        label: 'Processing',
        chipColor: 'default' as const,
      };
    }

    switch (file.transcription_status) {
      case 'completed':
        return {
          icon: <CheckCircle />,
          color: '#4caf50' as const,
          label: 'Completed',
          chipColor: 'primary' as const,
        };
      case 'failed':
        return {
          icon: <Error />,
          color: '#f44336' as const,
          label: 'Failed',
          chipColor: 'secondary' as const,
        };
      default:
        return {
          icon: <Info />,
          color: '#2196f3' as const,
          label: 'Not Transcribed',
          chipColor: 'default' as const,
        };
    }
  };

  const config = getStatusConfig();

  const getTooltipContent = () => {
    if (isProcessing) {
      return 'Transcription is currently being processed...';
    }

    switch (file.transcription_status) {
      case 'completed':
        return `Transcription completed${file.last_transcription_attempt ? ` on ${new Date(file.last_transcription_attempt).toLocaleString()}` : ''}`;
      case 'failed':
        return `Transcription failed${file.transcription_error ? `: ${file.transcription_error}` : ''}${file.last_transcription_attempt ? ` (${new Date(file.last_transcription_attempt).toLocaleString()})` : ''}`;
      default:
        return 'No transcription available for this file';
    }
  };

  if (showDetails) {
    return (
      <Box display="flex" flexDirection="column" style={{ gap: '8px' }}>
        <Box display="flex" alignItems="center" style={{ gap: '8px' }}>
          <Box style={{ color: config.color }}>
            {config.icon}
          </Box>
          <Typography variant="body2" style={{ color: config.color }}>
            {config.label}
          </Typography>
        </Box>
        
        {isProcessing && (
          <LinearProgress 
            variant="indeterminate" 
            style={{ width: '100%', height: '4px' }}
          />
        )}
        
        {file.transcription_error && (
          <Typography variant="caption" color="error">
            {file.transcription_error}
          </Typography>
        )}
        
        {file.last_transcription_attempt && (
          <Typography variant="caption" color="textSecondary">
            Last attempt: {new Date(file.last_transcription_attempt).toLocaleString()}
          </Typography>
        )}
      </Box>
    );
  }

  return (
    <Tooltip title={getTooltipContent()}>
      <Chip
        icon={React.cloneElement(config.icon, { style: { color: config.color } })}
        label={config.label}
        color={config.chipColor}
        variant="outlined"
        size="small"
      />
    </Tooltip>
  );
};

interface FileSizeDisplayProps {
  file: AudioFileInfo;
  showCompressed?: boolean;
}

export const FileSizeDisplay: React.FC<FileSizeDisplayProps> = ({
  file,
  showCompressed = true,
}) => {
  const formatFileSize = (bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  const getCompressionRatio = () => {
    if (!file.has_compressed_version || !file.compressed_size) return null;
    return ((file.size - file.compressed_size) / file.size * 100).toFixed(1);
  };

  const compressionRatio = getCompressionRatio();

  return (
    <Box display="flex" flexDirection="column" style={{ gap: '4px' }}>
      <Typography variant="body2" color="textSecondary">
        Original: {formatFileSize(file.size)}
      </Typography>
      
      {showCompressed && file.has_compressed_version && file.compressed_size && (
        <Box display="flex" alignItems="center" style={{ gap: '8px' }}>
          <Typography variant="body2" color="textSecondary">
            Compressed: {formatFileSize(file.compressed_size)}
          </Typography>
          {compressionRatio && (
            <Chip
              label={`${compressionRatio}% smaller`}
              size="small"
              color="primary"
              variant="outlined"
              style={{ fontSize: '0.7rem', height: '20px' }}
            />
          )}
        </Box>
      )}
      
      {showCompressed && !file.has_compressed_version && (
        <Typography variant="caption" color="textSecondary">
          No compressed version available
        </Typography>
      )}
    </Box>
  );
};

interface DurationDisplayProps {
  duration?: number;
  showIcon?: boolean;
}

export const DurationDisplay: React.FC<DurationDisplayProps> = ({
  duration,
  showIcon = false,
}) => {
  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  if (!duration) {
    return (
      <Typography variant="body2" color="textSecondary">
        Duration: Unknown
      </Typography>
    );
  }

  return (
    <Box display="flex" alignItems="center" style={{ gap: '4px' }}>
      {showIcon && <Info style={{ fontSize: '1rem', color: '#666' }} />}
      <Typography variant="body2" color="textSecondary">
        Duration: {formatDuration(duration)}
      </Typography>
    </Box>
  );
};

interface TranscriptionProgressProps {
  totalFiles: number;
  transcribedFiles: number;
  failedFiles: number;
  showDetails?: boolean;
}

export const TranscriptionProgress: React.FC<TranscriptionProgressProps> = ({
  totalFiles,
  transcribedFiles,
  failedFiles,
  showDetails = false,
}) => {
  const completionPercentage = totalFiles > 0 ? (transcribedFiles / totalFiles) * 100 : 0;
  const pendingFiles = totalFiles - transcribedFiles - failedFiles;

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" marginBottom={1}>
        <Typography variant="body2" color="textSecondary">
          Transcription Progress
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {transcribedFiles}/{totalFiles} ({completionPercentage.toFixed(1)}%)
        </Typography>
      </Box>
      
      <LinearProgress
        variant="determinate"
        value={completionPercentage}
        style={{ height: '8px', borderRadius: '4px' }}
      />
      
      {showDetails && (
        <Box display="flex" marginTop={1} style={{ gap: '16px' }}>
          <Box display="flex" alignItems="center" style={{ gap: '4px' }}>
            <CheckCircle style={{ fontSize: '1rem', color: '#4caf50' }} />
            <Typography variant="caption">
              {transcribedFiles} completed
            </Typography>
          </Box>
          
          <Box display="flex" alignItems="center" style={{ gap: '4px' }}>
            <Error style={{ fontSize: '1rem', color: '#f44336' }} />
            <Typography variant="caption">
              {failedFiles} failed
            </Typography>
          </Box>
          
          <Box display="flex" alignItems="center" style={{ gap: '4px' }}>
            <Warning style={{ fontSize: '1rem', color: '#ff9800' }} />
            <Typography variant="caption">
              {pendingFiles} pending
            </Typography>
          </Box>
        </Box>
      )}
    </Box>
  );
};

export default {
  StatusIndicator,
  FileSizeDisplay,
  DurationDisplay,
  TranscriptionProgress,
};