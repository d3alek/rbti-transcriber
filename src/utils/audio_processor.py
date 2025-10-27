"""Audio processing and compression using FFmpeg."""

import subprocess
import shutil
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import hashlib

from .exceptions import AudioValidationError, FileSystemError


class AudioProcessor:
    """Audio processor with FFmpeg integration for compression and analysis."""
    
    TARGET_BITRATE = 32  # Target bitrate in kbps (optimized for speech)
    
    def __init__(self, compressed_cache_dir: Path):
        self.compressed_cache_dir = Path(compressed_cache_dir)
        self.compressed_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if FFmpeg is available
        if not self._check_ffmpeg_available():
            raise FileSystemError("FFmpeg is not available. Please install FFmpeg to use audio compression.")
    
    def _check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available in the system."""
        return shutil.which('ffmpeg') is not None
    
    def _get_compressed_cache_path(self, input_file: Path) -> Path:
        """Get cache path for compressed audio file."""
        # Create hash based on file path and modification time
        file_info = f"{input_file}_{input_file.stat().st_mtime}_{input_file.stat().st_size}"
        file_hash = hashlib.md5(file_info.encode()).hexdigest()[:12]
        return self.compressed_cache_dir / f"{input_file.stem}_{file_hash}_compressed.mp3"
    
    def analyze_audio_bitrate(self, audio_file: Path) -> Dict[str, Any]:
        """Analyze audio file to get bitrate and other properties."""
        if not audio_file.exists():
            raise AudioValidationError(f"Audio file does not exist: {audio_file}")
        
        try:
            # Use ffprobe to get audio information
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(audio_file)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            
            # Extract audio stream information
            audio_streams = [s for s in probe_data.get('streams', []) if s.get('codec_type') == 'audio']
            
            if not audio_streams:
                raise AudioValidationError(f"No audio streams found in file: {audio_file}")
            
            audio_stream = audio_streams[0]  # Use first audio stream
            format_info = probe_data.get('format', {})
            
            # Extract relevant information
            bitrate = int(audio_stream.get('bit_rate', 0)) // 1000  # Convert to kbps
            if bitrate == 0:
                # Try to get bitrate from format if not available in stream
                bitrate = int(format_info.get('bit_rate', 0)) // 1000
            
            duration = float(format_info.get('duration', 0))
            file_size = int(format_info.get('size', 0))
            
            return {
                'bitrate_kbps': bitrate,
                'duration_seconds': duration,
                'file_size_bytes': file_size,
                'file_size_mb': round(file_size / (1024 * 1024), 2),
                'codec': audio_stream.get('codec_name', 'unknown'),
                'sample_rate': int(audio_stream.get('sample_rate', 0)),
                'channels': int(audio_stream.get('channels', 0))
            }
            
        except subprocess.CalledProcessError as e:
            raise AudioValidationError(f"FFprobe failed for file {audio_file}: {e.stderr}")
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            raise AudioValidationError(f"Failed to parse audio information for {audio_file}: {e}")
    
    def needs_compression(self, audio_file: Path) -> Tuple[bool, Dict[str, Any]]:
        """Check if audio file needs compression based on bitrate analysis."""
        audio_info = self.analyze_audio_bitrate(audio_file)
        current_bitrate = audio_info['bitrate_kbps']
        
        # Compress if bitrate is higher than target (more aggressive for speech)
        needs_compression = current_bitrate > self.TARGET_BITRATE
        
        return needs_compression, audio_info
    
    def compress_audio(self, input_file: Path, force: bool = False, target_size_mb: float = 20.0) -> Path:
        """Compress audio file to target bitrate and return path to compressed file."""
        if not input_file.exists():
            raise AudioValidationError(f"Input file does not exist: {input_file}")
        
        compressed_path = self._get_compressed_cache_path(input_file)
        
        # Return cached compressed file if it exists and is newer than input
        if (compressed_path.exists() and not force and 
            compressed_path.stat().st_mtime > input_file.stat().st_mtime):
            return compressed_path
        
        # Check if compression is needed
        needs_compression, audio_info = self.needs_compression(input_file)
        
        if not needs_compression and not force:
            # File doesn't need compression, return original
            return input_file
        
        try:
            # Compress using FFmpeg with aggressive speech optimization
            cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-codec:a', 'mp3',
                '-b:a', f'{self.TARGET_BITRATE}k',
                '-ar', '16000',  # 16kHz sample rate (optimal for speech)
                '-ac', '1',      # Convert to mono for speech
                    '-q:a', '9',     # Lower quality for smaller size (good for speech)
                    '-compression_level', '9',  # Maximum compression
                    '-y',            # Overwrite output file
                    str(compressed_path)
                ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if not compressed_path.exists():
                raise FileSystemError(f"FFmpeg did not create output file: {compressed_path}")
            
            # Verify compressed file
            compressed_info = self.analyze_audio_bitrate(compressed_path)
            
            # Check if file is still too large and compress further if needed
            compressed_size_mb = compressed_path.stat().st_size / (1024 * 1024)
            if compressed_size_mb > target_size_mb:
                # Try even more aggressive compression
                return self._compress_ultra_aggressive(input_file, compressed_path, target_size_mb)
            
            return compressed_path
            
        except subprocess.CalledProcessError as e:
            raise FileSystemError(f"FFmpeg compression failed for {input_file}: {e.stderr}")
    
    def get_compression_stats(self, original_file: Path, compressed_file: Path) -> Dict[str, Any]:
        """Get compression statistics comparing original and compressed files."""
        original_info = self.analyze_audio_bitrate(original_file)
        compressed_info = self.analyze_audio_bitrate(compressed_file)
        
        size_reduction = original_info['file_size_bytes'] - compressed_info['file_size_bytes']
        size_reduction_percent = (size_reduction / original_info['file_size_bytes']) * 100
        
        return {
            'original': original_info,
            'compressed': compressed_info,
            'size_reduction_bytes': size_reduction,
            'size_reduction_mb': round(size_reduction / (1024 * 1024), 2),
            'size_reduction_percent': round(size_reduction_percent, 1),
            'bitrate_reduction_kbps': original_info['bitrate_kbps'] - compressed_info['bitrate_kbps']
        }
    
    def clean_compressed_cache(self, max_age_days: int = 30) -> None:
        """Clean old compressed files from cache."""
        import time
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60
        
        for compressed_file in self.compressed_cache_dir.glob("*_compressed.mp3"):
            try:
                if current_time - compressed_file.stat().st_mtime > max_age_seconds:
                    compressed_file.unlink()
            except OSError:
                continue
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about compressed file cache."""
        compressed_files = list(self.compressed_cache_dir.glob("*_compressed.mp3"))
        total_size = sum(f.stat().st_size for f in compressed_files)
        
        return {
            'total_compressed_files': len(compressed_files),
            'total_cache_size_bytes': total_size,
            'total_cache_size_mb': round(total_size / (1024 * 1024), 2),
            'cache_directory': str(self.compressed_cache_dir)
        }
    
    def _compress_ultra_aggressive(self, input_file: Path, initial_compressed: Path, target_size_mb: float) -> Path:
        """Apply ultra-aggressive compression for very large files."""
        ultra_compressed_path = initial_compressed.with_suffix('.ultra.mp3')
        
        # Ultra-aggressive MP3 compression for speech
        cmd = [
            'ffmpeg',
            '-i', str(input_file),
            '-codec:a', 'mp3',
            '-b:a', '16k',       # Very low bitrate for speech
            '-ar', '8000',       # 8kHz sample rate (minimum for speech)
            '-ac', '1',          # Mono
            '-q:a', '9',         # Lowest quality
            '-compression_level', '9',
            '-af', 'highpass=f=80,lowpass=f=3400',  # Filter for speech frequencies
            '-y',
            str(ultra_compressed_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            if ultra_compressed_path.exists():
                # Check final size
                final_size_mb = ultra_compressed_path.stat().st_size / (1024 * 1024)
                if final_size_mb <= target_size_mb:
                    # Remove the intermediate file
                    initial_compressed.unlink()
                    return ultra_compressed_path
                else:
                    # If still too large, return the best we can do
                    return ultra_compressed_path
            else:
                # If ultra compression failed, return the initial compressed version
                return initial_compressed
                
        except subprocess.CalledProcessError:
            # If ultra compression failed, return the initial compressed version
            return initial_compressed