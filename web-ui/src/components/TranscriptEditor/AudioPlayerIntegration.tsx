import React, { useEffect, useRef, useCallback } from 'react';
import { Box, Typography, LinearProgress, Chip } from '@material-ui/core';
import { ReactTranscriptEditorData } from '../../types/transcriptEditor';

interface AudioPlayerIntegrationProps {
  mediaUrl: string;
  transcriptData: ReactTranscriptEditorData;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  fileSize?: number;
  compressedSize?: number;
}

export const AudioPlayerIntegration: React.FC<AudioPlayerIntegrationProps> = ({
  mediaUrl,
  transcriptData,
  currentTime,
  onTimeUpdate,
  fileSize,
  compressedSize,
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);

  // Format file size for display
  const formatFileSize = useCallback((bytes: number) => {
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  }, []);

  // Handle time updates from audio element
  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current) {
      onTimeUpdate(audioRef.current.currentTime);
    }
  }, [onTimeUpdate]);

  // Set up audio event listeners
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    audio.addEventListener('timeupdate', handleTimeUpdate);
    
    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
    };
  }, [handleTimeUpdate]);

  // Calculate progress percentage
  const progressPercentage = transcriptData.metadata.duration > 0 
    ? (currentTime / transcriptData.metadata.duration) * 100 
    : 0;

  // Find current word being spoken
  const currentWord = transcriptData.words.find(word => 
    currentTime >= word.start && currentTime <= word.end
  );

  return (
    <Box>
      {/* Audio Element */}
      <audio
        ref={audioRef}
        src={mediaUrl}
        controls
        style={{ width: '100%', marginBottom: '16px' }}
        preload="metadata"
      >
        Your browser does not support the audio element.
      </audio>

      {/* File Size Information */}
      <Box display="flex" alignItems="center" style={{ gap: '8px', marginBottom: '16px' }}>
        {fileSize && (
          <Chip
            label={`Original: ${formatFileSize(fileSize)}`}
            size="small"
            variant="outlined"
          />
        )}
        {compressedSize && (
          <Chip
            label={`Compressed: ${formatFileSize(compressedSize)}`}
            size="small"
            variant="outlined"
            color="primary"
          />
        )}
        {fileSize && compressedSize && (
          <Chip
            label={`${(((fileSize - compressedSize) / fileSize) * 100).toFixed(1)}% smaller`}
            size="small"
            variant="outlined"
            color="secondary"
          />
        )}
      </Box>

      {/* Playback Progress */}
      <Box marginBottom={2}>
        <Box display="flex" justifyContent="space-between" alignItems="center" marginBottom={1}>
          <Typography variant="body2" color="textSecondary">
            Playback Progress
          </Typography>
          <Typography variant="body2" color="textSecondary">
            {Math.floor(currentTime / 60)}:{(Math.floor(currentTime % 60)).toString().padStart(2, '0')} / {Math.floor(transcriptData.metadata.duration / 60)}:{(Math.floor(transcriptData.metadata.duration % 60)).toString().padStart(2, '0')}
          </Typography>
        </Box>
        <LinearProgress 
          variant="determinate" 
          value={progressPercentage} 
          style={{ height: '6px', borderRadius: '3px' }}
        />
      </Box>

      {/* Current Word Indicator */}
      {currentWord && (
        <Box 
          padding={1} 
          style={{ 
            backgroundColor: '#e3f2fd', 
            borderRadius: '4px',
            border: '1px solid #2196f3'
          }}
        >
          <Typography variant="body2" color="primary">
            <strong>Currently speaking:</strong> "{currentWord.word}" 
            {currentWord.corrected && (
              <span style={{ color: '#ff9800' }}> (edited)</span>
            )}
          </Typography>
          <Typography variant="caption" color="textSecondary">
            Confidence: {(currentWord.confidence * 100).toFixed(1)}% • 
            Speaker: {transcriptData.speaker_names?.[currentWord.speaker] || `Speaker ${currentWord.speaker}`}
          </Typography>
        </Box>
      )}
    </Box>
  );
};

export default AudioPlayerIntegration;