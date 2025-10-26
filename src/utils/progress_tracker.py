"""Progress tracking and reporting for transcription operations."""

import time
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json


@dataclass
class FileProgress:
    """Progress information for a single file."""
    file_path: Path
    status: str  # 'pending', 'processing', 'completed', 'failed', 'skipped'
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error_message: Optional[str] = None
    file_size_mb: float = 0.0
    processing_time: float = 0.0
    output_formats: List[str] = field(default_factory=list)


@dataclass
class BatchProgress:
    """Progress information for a batch of files."""
    total_files: int
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    file_progress: Dict[str, FileProgress] = field(default_factory=dict)


class ProgressTracker:
    """Tracks progress of transcription operations with real-time updates."""
    
    def __init__(self, total_files: int, output_dir: Optional[Path] = None):
        self.batch_progress = BatchProgress(total_files=total_files)
        self.output_dir = output_dir
        self.progress_file = output_dir / "progress.json" if output_dir else None
    
    def start_file(self, file_path: Path, file_size_mb: float = 0.0) -> None:
        """Mark a file as started processing."""
        file_key = str(file_path)
        self.batch_progress.file_progress[file_key] = FileProgress(
            file_path=file_path,
            status='processing',
            start_time=time.time(),
            file_size_mb=file_size_mb
        )
        self._save_progress()
    
    def complete_file(self, file_path: Path, output_formats: List[str], 
                     processing_time: float = 0.0) -> None:
        """Mark a file as completed successfully."""
        file_key = str(file_path)
        if file_key in self.batch_progress.file_progress:
            file_progress = self.batch_progress.file_progress[file_key]
            file_progress.status = 'completed'
            file_progress.end_time = time.time()
            file_progress.output_formats = output_formats
            file_progress.processing_time = processing_time
            
            self.batch_progress.completed_files += 1
        
        self._save_progress()
    
    def fail_file(self, file_path: Path, error_message: str) -> None:
        """Mark a file as failed with error message."""
        file_key = str(file_path)
        if file_key in self.batch_progress.file_progress:
            file_progress = self.batch_progress.file_progress[file_key]
            file_progress.status = 'failed'
            file_progress.end_time = time.time()
            file_progress.error_message = error_message
            
            self.batch_progress.failed_files += 1
        
        self._save_progress()
    
    def skip_file(self, file_path: Path, reason: str = "Already processed") -> None:
        """Mark a file as skipped."""
        file_key = str(file_path)
        self.batch_progress.file_progress[file_key] = FileProgress(
            file_path=file_path,
            status='skipped',
            start_time=time.time(),
            end_time=time.time(),
            error_message=reason
        )
        
        self.batch_progress.skipped_files += 1
        self._save_progress()
    
    def finish_batch(self) -> None:
        """Mark the entire batch as finished."""
        self.batch_progress.end_time = time.time()
        self._save_progress()
    
    def get_progress_percentage(self) -> float:
        """Get overall progress percentage."""
        processed = (self.batch_progress.completed_files + 
                    self.batch_progress.failed_files + 
                    self.batch_progress.skipped_files)
        
        if self.batch_progress.total_files == 0:
            return 100.0
        
        return (processed / self.batch_progress.total_files) * 100.0
    
    def get_success_rate(self) -> float:
        """Get success rate percentage."""
        total_attempted = (self.batch_progress.completed_files + 
                          self.batch_progress.failed_files)
        
        if total_attempted == 0:
            return 0.0
        
        return (self.batch_progress.completed_files / total_attempted) * 100.0
    
    def get_estimated_time_remaining(self) -> Optional[float]:
        """Estimate time remaining based on current progress."""
        completed = self.batch_progress.completed_files
        if completed == 0:
            return None
        
        elapsed_time = time.time() - self.batch_progress.start_time
        avg_time_per_file = elapsed_time / completed
        remaining_files = (self.batch_progress.total_files - 
                          self.batch_progress.completed_files - 
                          self.batch_progress.failed_files - 
                          self.batch_progress.skipped_files)
        
        return remaining_files * avg_time_per_file
    
    def get_processing_speed(self) -> Dict[str, float]:
        """Get processing speed statistics."""
        completed_files = [
            fp for fp in self.batch_progress.file_progress.values()
            if fp.status == 'completed' and fp.processing_time > 0
        ]
        
        if not completed_files:
            return {'files_per_minute': 0.0, 'mb_per_minute': 0.0}
        
        total_processing_time = sum(fp.processing_time for fp in completed_files)
        total_size_mb = sum(fp.file_size_mb for fp in completed_files)
        
        if total_processing_time == 0:
            return {'files_per_minute': 0.0, 'mb_per_minute': 0.0}
        
        files_per_minute = (len(completed_files) / total_processing_time) * 60
        mb_per_minute = (total_size_mb / total_processing_time) * 60
        
        return {
            'files_per_minute': files_per_minute,
            'mb_per_minute': mb_per_minute
        }
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive summary report."""
        elapsed_time = (self.batch_progress.end_time or time.time()) - self.batch_progress.start_time
        speed_stats = self.get_processing_speed()
        
        # Calculate file size statistics
        completed_files = [
            fp for fp in self.batch_progress.file_progress.values()
            if fp.status == 'completed'
        ]
        
        total_size_mb = sum(fp.file_size_mb for fp in completed_files)
        avg_file_size = total_size_mb / len(completed_files) if completed_files else 0
        
        # Get error summary
        failed_files = [
            fp for fp in self.batch_progress.file_progress.values()
            if fp.status == 'failed'
        ]
        
        error_summary = {}
        for fp in failed_files:
            error = fp.error_message or "Unknown error"
            error_summary[error] = error_summary.get(error, 0) + 1
        
        return {
            'batch_summary': {
                'total_files': self.batch_progress.total_files,
                'completed_files': self.batch_progress.completed_files,
                'failed_files': self.batch_progress.failed_files,
                'skipped_files': self.batch_progress.skipped_files,
                'success_rate': self.get_success_rate(),
                'progress_percentage': self.get_progress_percentage()
            },
            'timing': {
                'start_time': datetime.fromtimestamp(self.batch_progress.start_time).isoformat(),
                'end_time': datetime.fromtimestamp(self.batch_progress.end_time).isoformat() if self.batch_progress.end_time else None,
                'elapsed_time_seconds': elapsed_time,
                'elapsed_time_formatted': str(timedelta(seconds=int(elapsed_time)))
            },
            'performance': {
                'files_per_minute': speed_stats['files_per_minute'],
                'mb_per_minute': speed_stats['mb_per_minute'],
                'total_size_processed_mb': total_size_mb,
                'average_file_size_mb': avg_file_size
            },
            'errors': error_summary,
            'output_formats': self._get_output_format_summary()
        }
    
    def _get_output_format_summary(self) -> Dict[str, int]:
        """Get summary of output formats generated."""
        format_counts = {}
        
        for fp in self.batch_progress.file_progress.values():
            if fp.status == 'completed':
                for format_type in fp.output_formats:
                    format_counts[format_type] = format_counts.get(format_type, 0) + 1
        
        return format_counts
    
    def _save_progress(self) -> None:
        """Save progress to JSON file if output directory is specified."""
        if not self.progress_file:
            return
        
        try:
            # Convert to serializable format
            progress_data = {
                'batch_progress': {
                    'total_files': self.batch_progress.total_files,
                    'completed_files': self.batch_progress.completed_files,
                    'failed_files': self.batch_progress.failed_files,
                    'skipped_files': self.batch_progress.skipped_files,
                    'start_time': self.batch_progress.start_time,
                    'end_time': self.batch_progress.end_time
                },
                'file_progress': {
                    str(fp.file_path): {
                        'status': fp.status,
                        'start_time': fp.start_time,
                        'end_time': fp.end_time,
                        'error_message': fp.error_message,
                        'file_size_mb': fp.file_size_mb,
                        'processing_time': fp.processing_time,
                        'output_formats': fp.output_formats
                    }
                    for fp in self.batch_progress.file_progress.values()
                },
                'last_updated': time.time()
            }
            
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2)
        
        except Exception:
            # Don't fail the main operation if progress saving fails
            pass
    
    def load_previous_progress(self) -> bool:
        """Load previous progress from file if it exists."""
        if not self.progress_file or not self.progress_file.exists():
            return False
        
        try:
            with open(self.progress_file, 'r') as f:
                progress_data = json.load(f)
            
            # Restore batch progress
            batch_data = progress_data['batch_progress']
            self.batch_progress.completed_files = batch_data['completed_files']
            self.batch_progress.failed_files = batch_data['failed_files']
            self.batch_progress.skipped_files = batch_data['skipped_files']
            self.batch_progress.start_time = batch_data['start_time']
            self.batch_progress.end_time = batch_data.get('end_time')
            
            # Restore file progress
            for file_path_str, fp_data in progress_data['file_progress'].items():
                self.batch_progress.file_progress[file_path_str] = FileProgress(
                    file_path=Path(file_path_str),
                    status=fp_data['status'],
                    start_time=fp_data.get('start_time'),
                    end_time=fp_data.get('end_time'),
                    error_message=fp_data.get('error_message'),
                    file_size_mb=fp_data.get('file_size_mb', 0.0),
                    processing_time=fp_data.get('processing_time', 0.0),
                    output_formats=fp_data.get('output_formats', [])
                )
            
            return True
        
        except Exception:
            return False
    
    def export_report(self, output_path: Path) -> None:
        """Export detailed progress report to file."""
        report = self.get_summary_report()
        
        try:
            with open(output_path, 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            raise IOError(f"Cannot export report to {output_path}: {e}")