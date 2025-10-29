/**
 * AudioPlayer Component
 * 
 * Audio playback controls with precise timing for transcript synchronization.
 */

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Box,
  IconButton,
  Slider,
  Typography,
  Paper,
  Tooltip,
  Select,
  MenuItem,
  FormControl,
  InputLabel
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  VolumeUp as VolumeUpIcon,
  VolumeOff as VolumeOffIcon,
  Replay10 as Replay10Icon,
  Forward10 as Forward10Icon,

} from '@mui/icons-material';
import type { AudioPlayerProps } from '../types/deepgram';

interface AudioPlayerComponentProps extends AudioPlayerProps {
  onLoadedMetadata?: (duration: number) => void;
  onError?: (error: string) => void;
}

const AudioPlayer: React.FC<AudioPlayerComponentProps> = ({
  audioFile,
  currentTime,
  onTimeUpdate,
  onSeek,
  duration: propDuration,
  onLoadedMetadata,
  onError
}) => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(propDuration || 0);
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Ref to track if we're currently seeking to avoid feedback loops
  const isSeekingRef = useRef(false);
  const lastUpdateTimeRef = useRef(0);

  // Load audio when audioFile changes
  useEffect(() => {
    if (audioRef.current && audioFile) {
      setIsLoading(true);
      setError(null);
      audioRef.current.src = audioFile;
      audioRef.current.load();
    }
  }, [audioFile]);

  // Sync external currentTime with audio element
  useEffect(() => {
    if (audioRef.current && !isSeekingRef.current) {
      const audioCurrentTime = audioRef.current.currentTime;
      const timeDiff = Math.abs(audioCurrentTime - currentTime);
      
      // Only seek if there's a significant difference (> 0.5 seconds)
      if (timeDiff > 0.5) {
        isSeekingRef.current = true;
        audioRef.current.currentTime = currentTime;
        setTimeout(() => {
          isSeekingRef.current = false;
        }, 100);
      }
    }
  }, [currentTime]);

  const handleLoadedMetadata = useCallback(() => {
    if (audioRef.current) {
      const audioDuration = audioRef.current.duration;
      setDuration(audioDuration);
      setIsLoading(false);
      onLoadedMetadata?.(audioDuration);
    }
  }, [onLoadedMetadata]);

  const handleTimeUpdate = useCallback(() => {
    if (audioRef.current && !isSeekingRef.current) {
      const currentTime = audioRef.current.currentTime;
      
      // Throttle updates to avoid excessive calls
      const now = Date.now();
      if (now - lastUpdateTimeRef.current > 100) {
        onTimeUpdate(currentTime);
        lastUpdateTimeRef.current = now;
      }
    }
  }, [onTimeUpdate]);

  const handleError = useCallback(() => {
    const errorMessage = 'Failed to load audio file';
    setError(errorMessage);
    setIsLoading(false);
    onError?.(errorMessage);
  }, [onError]);

  const handlePlay = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.play()
        .then(() => setIsPlaying(true))
        .catch((err) => {
          console.error('Play failed:', err);
          setError('Failed to play audio');
        });
    }
  }, []);

  const handlePause = useCallback(() => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  }, []);

  const handlePlayPause = useCallback(() => {
    if (isPlaying) {
      handlePause();
    } else {
      handlePlay();
    }
  }, [isPlaying, handlePlay, handlePause]);

  const handleSeek = useCallback((newTime: number) => {
    if (audioRef.current) {
      isSeekingRef.current = true;
      audioRef.current.currentTime = newTime;
      onSeek(newTime);
      
      setTimeout(() => {
        isSeekingRef.current = false;
      }, 100);
    }
  }, [onSeek]);

  const handleSliderChange = useCallback((_: Event, value: number | number[]) => {
    const newTime = Array.isArray(value) ? value[0] : value;
    handleSeek(newTime);
  }, [handleSeek]);

  const handleVolumeChange = useCallback((_: Event, value: number | number[]) => {
    const newVolume = Array.isArray(value) ? value[0] : value;
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
    if (newVolume === 0) {
      setIsMuted(true);
    } else if (isMuted) {
      setIsMuted(false);
    }
  }, [isMuted]);

  const handleMuteToggle = useCallback(() => {
    if (audioRef.current) {
      if (isMuted) {
        audioRef.current.volume = volume;
        setIsMuted(false);
      } else {
        audioRef.current.volume = 0;
        setIsMuted(true);
      }
    }
  }, [isMuted, volume]);

  const handleSkip = useCallback((seconds: number) => {
    if (audioRef.current) {
      const newTime = Math.max(0, Math.min(duration, audioRef.current.currentTime + seconds));
      handleSeek(newTime);
    }
  }, [duration, handleSeek]);

  const handlePlaybackRateChange = useCallback((rate: number) => {
    setPlaybackRate(rate);
    if (audioRef.current) {
      audioRef.current.playbackRate = rate;
    }
  }, []);

  const formatTime = useCallback((time: number) => {
    const minutes = Math.floor(time / 60);
    const seconds = Math.floor(time % 60);
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }, []);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Only handle shortcuts when not typing in an input
      if (event.target instanceof HTMLInputElement || event.target instanceof HTMLTextAreaElement) {
        return;
      }

      switch (event.code) {
        case 'Space':
          event.preventDefault();
          handlePlayPause();
          break;
        case 'ArrowLeft':
          event.preventDefault();
          handleSkip(-10);
          break;
        case 'ArrowRight':
          event.preventDefault();
          handleSkip(10);
          break;
        case 'ArrowUp':
          event.preventDefault();
          handleVolumeChange(null as any, Math.min(1, volume + 0.1));
          break;
        case 'ArrowDown':
          event.preventDefault();
          handleVolumeChange(null as any, Math.max(0, volume - 0.1));
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handlePlayPause, handleSkip, handleVolumeChange, volume]);

  return (
    <Paper elevation={2} sx={{ p: 2 }}>
      <audio
        ref={audioRef}
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onError={handleError}
        onEnded={() => setIsPlaying(false)}
        preload="metadata"
      />

      <Box display="flex" alignItems="center" gap={2}>
        {/* Main Controls */}
        <Box display="flex" alignItems="center" gap={1}>
          <Tooltip title="Skip back 10s (←)">
            <IconButton onClick={() => handleSkip(-10)} disabled={isLoading}>
              <Replay10Icon />
            </IconButton>
          </Tooltip>

          <Tooltip title={isPlaying ? "Pause (Space)" : "Play (Space)"}>
            <IconButton 
              onClick={handlePlayPause} 
              disabled={isLoading || !!error}
              size="large"
              color="primary"
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </IconButton>
          </Tooltip>

          <Tooltip title="Skip forward 10s (→)">
            <IconButton onClick={() => handleSkip(10)} disabled={isLoading}>
              <Forward10Icon />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Time Display */}
        <Typography variant="body2" sx={{ minWidth: '80px' }}>
          {formatTime(currentTime)} / {formatTime(duration)}
        </Typography>

        {/* Progress Slider */}
        <Box sx={{ flex: 1, mx: 2 }}>
          <Slider
            value={currentTime}
            max={duration}
            onChange={handleSliderChange}
            disabled={isLoading || !!error}
            size="small"
            sx={{
              '& .MuiSlider-thumb': {
                width: 16,
                height: 16,
              },
            }}
          />
        </Box>

        {/* Volume Controls */}
        <Box display="flex" alignItems="center" gap={1} sx={{ minWidth: '120px' }}>
          <Tooltip title="Toggle mute">
            <IconButton onClick={handleMuteToggle} size="small">
              {isMuted || volume === 0 ? <VolumeOffIcon /> : <VolumeUpIcon />}
            </IconButton>
          </Tooltip>
          
          <Slider
            value={isMuted ? 0 : volume}
            max={1}
            step={0.1}
            onChange={handleVolumeChange}
            size="small"
            sx={{ width: 80 }}
          />
        </Box>

        {/* Playback Speed */}
        <FormControl size="small" sx={{ minWidth: 80 }}>
          <InputLabel>Speed</InputLabel>
          <Select
            value={playbackRate}
            onChange={(e) => handlePlaybackRateChange(e.target.value as number)}
            label="Speed"
          >
            <MenuItem value={0.5}>0.5x</MenuItem>
            <MenuItem value={0.75}>0.75x</MenuItem>
            <MenuItem value={1}>1x</MenuItem>
            <MenuItem value={1.25}>1.25x</MenuItem>
            <MenuItem value={1.5}>1.5x</MenuItem>
            <MenuItem value={2}>2x</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Error Display */}
      {error && (
        <Typography variant="body2" color="error" sx={{ mt: 1 }}>
          {error}
        </Typography>
      )}

      {/* Loading Display */}
      {isLoading && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Loading audio...
        </Typography>
      )}

      {/* Keyboard Shortcuts Help */}
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        Shortcuts: Space (play/pause), ← → (skip 10s), ↑ ↓ (volume)
      </Typography>
    </Paper>
  );
};

export default AudioPlayer;