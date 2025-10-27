/**
 * Audio Player component with segment playback support.
 */

import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  IconButton,
  Slider,
  Typography,
  Paper,
  Tooltip,
} from '@mui/material';
import {
  PlayArrow as PlayIcon,
  Pause as PauseIcon,
  Stop as StopIcon,
  VolumeUp as VolumeIcon,
  Replay10 as Replay10Icon,
  Forward10 as Forward10Icon,
} from '@mui/icons-material';

interface AudioPlayerProps {
  audioFile: File | string;
  currentTime: number;
  onTimeUpdate: (time: number) => void;
  onSeek: (time: number) => void;
  duration: number;
  onPlaySegment?: (startTime: number, endTime: number) => void;
}

export interface AudioPlayerRef {
  playSegment: (startTime: number, endTime: number) => void;
}

export const AudioPlayer = React.forwardRef<AudioPlayerRef, AudioPlayerProps>(({
  audioFile,
  currentTime,
  onTimeUpdate,
  onSeek,
  duration,
  onPlaySegment,
}, ref) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [volume, setVolume] = useState(1);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [actualDuration, setActualDuration] = useState(duration);
  const [actualCurrentTime, setActualCurrentTime] = useState(0);

  // Create audio URL from file
  useEffect(() => {
    if (typeof audioFile === 'string') {
      setAudioUrl(audioFile);
    } else if (audioFile instanceof File) {
      const url = URL.createObjectURL(audioFile);
      setAudioUrl(url);
      return () => URL.revokeObjectURL(url);
    }
  }, [audioFile]);

  // Update audio element time when currentTime prop changes
  useEffect(() => {
    if (audioRef.current && !isDragging) {
      const audio = audioRef.current;
      if (Math.abs(audio.currentTime - currentTime) > 0.5) {
        audio.currentTime = currentTime;
        setActualCurrentTime(currentTime);
      }
    }
  }, [currentTime, isDragging]);

  // Handle audio time updates
  const handleTimeUpdate = () => {
    if (audioRef.current && !isDragging) {
      const time = audioRef.current.currentTime;
      setActualCurrentTime(time);
      onTimeUpdate(time);
    }
  };

  // Handle when audio metadata is loaded
  const handleLoadedMetadata = () => {
    if (audioRef.current) {
      const audioDuration = audioRef.current.duration;
      console.log('Audio metadata loaded, duration:', audioDuration);
      if (isFinite(audioDuration) && audioDuration > 0) {
        setActualDuration(audioDuration);
      }
      audioRef.current.volume = volume;
    }
  };

  const handlePlay = () => {
    if (audioRef.current) {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handlePause = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      setIsPlaying(false);
    }
  };

  const handleStop = () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current.currentTime = 0;
      setIsPlaying(false);
      onSeek(0);
    }
  };

  const handleSeek = (newTime: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = newTime;
      onSeek(newTime);
    }
  };

  const handleSliderChange = (_: Event, value: number | number[]) => {
    const time = Array.isArray(value) ? value[0] : value;
    setActualCurrentTime(time);
    if (!isDragging) {
      handleSeek(time);
    }
  };

  const handleSliderChangeStart = () => {
    setIsDragging(true);
  };

  const handleSliderChangeEnd = (_: any, value: number | number[]) => {
    const time = Array.isArray(value) ? value[0] : value;
    handleSeek(time);
    setIsDragging(false);
  };

  const handleVolumeChange = (_: Event, value: number | number[]) => {
    const vol = Array.isArray(value) ? value[0] : value;
    setVolume(vol);
    if (audioRef.current) {
      audioRef.current.volume = vol;
    }
  };

  const skip = (seconds: number) => {
    if (audioRef.current) {
      const newTime = Math.max(0, Math.min(actualDuration, audioRef.current.currentTime + seconds));
      handleSeek(newTime);
    }
  };

  const formatTime = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  // Play specific segment
  const playSegment = (startTime: number, endTime: number) => {
    if (audioRef.current) {
      audioRef.current.currentTime = startTime;
      audioRef.current.play();
      setIsPlaying(true);

      // Stop at end time
      const stopAtEndTime = () => {
        if (audioRef.current && audioRef.current.currentTime >= endTime) {
          audioRef.current.pause();
          setIsPlaying(false);
        } else if (audioRef.current && !audioRef.current.paused) {
          requestAnimationFrame(stopAtEndTime);
        }
      };
      requestAnimationFrame(stopAtEndTime);
    }
  };

  // Expose playSegment method to parent component
  React.useImperativeHandle(ref, () => ({
    playSegment,
  }));

  // Call onPlaySegment when playSegment is called
  useEffect(() => {
    if (onPlaySegment) {
      // Store the function for external access
      (window as any).audioPlayerPlaySegment = playSegment;
    }
  }, [onPlaySegment]);

  return (
    <Paper sx={{ p: 2 }}>
      <audio
        ref={audioRef}
        src={audioUrl || undefined}
        onTimeUpdate={handleTimeUpdate}
        onEnded={() => setIsPlaying(false)}
        onLoadedMetadata={handleLoadedMetadata}
        onLoadedData={handleLoadedMetadata}
        onError={(e) => console.error('Audio error:', e)}
        onCanPlay={() => console.log('Audio can play')}
        preload="metadata"
        crossOrigin="anonymous"
      />

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Tooltip title="Replay 10s">
          <IconButton onClick={() => skip(-10)} size="small">
            <Replay10Icon />
          </IconButton>
        </Tooltip>

        <IconButton
          onClick={isPlaying ? handlePause : handlePlay}
          color="primary"
          size="large"
        >
          {isPlaying ? <PauseIcon /> : <PlayIcon />}
        </IconButton>

        <Tooltip title="Forward 10s">
          <IconButton onClick={() => skip(10)} size="small">
            <Forward10Icon />
          </IconButton>
        </Tooltip>

        <IconButton onClick={handleStop} size="small">
          <StopIcon />
        </IconButton>

        <Typography variant="body2" sx={{ minWidth: 80 }}>
          {formatTime(actualCurrentTime)} / {formatTime(actualDuration)}
        </Typography>
      </Box>

      {/* Progress Slider */}
      <Box sx={{ mb: 2 }}>
        <Slider
          value={actualCurrentTime}
          max={actualDuration}
          onChange={handleSliderChange}
          onChangeCommitted={handleSliderChangeEnd}
          onMouseDown={handleSliderChangeStart}
          sx={{ width: '100%' }}
          disabled={actualDuration === 0}
        />
      </Box>

      {/* Volume Control */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <VolumeIcon />
        <Slider
          value={volume}
          min={0}
          max={1}
          step={0.1}
          onChange={handleVolumeChange}
          sx={{ width: 100 }}
        />
      </Box>
    </Paper>
  );
});