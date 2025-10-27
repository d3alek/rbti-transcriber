"""Web transcription manager service."""

import uuid
import asyncio
from typing import Dict, Optional
from datetime import datetime
from pathlib import Path
from fastapi import BackgroundTasks

# Import from existing transcription system
import sys
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.core.transcription_orchestrator import TranscriptionOrchestrator
from src.utils.config import ConfigManager
from src.services.transcription_client import TranscriptionConfig

from ..models import TranscriptionRequest, TranscriptionProgress, TranscriptionStatus
from ..config import Settings
from .websocket_manager import WebSocketManager


class WebTranscriptionManager:
    """Manages transcription jobs for the web interface."""
    
    def __init__(self, settings: Settings, websocket_manager: Optional[WebSocketManager] = None):
        self.settings = settings
        self.config_manager = ConfigManager(settings.config_file)
        self.active_jobs: Dict[str, TranscriptionProgress] = {}
        self.websocket_manager = websocket_manager
        self.max_concurrent_jobs = 3  # Limit concurrent transcriptions
        self.job_queue = asyncio.Queue()
        self.processing_jobs = set()
        
        # Initialize orchestrator
        self.orchestrator = TranscriptionOrchestrator(
            config_manager=self.config_manager,
            output_dir=settings.audio_directory / "transcriptions",
            verbose=True,
            fail_fast=False
        )
        
        # Start job processor
        asyncio.create_task(self._process_job_queue())
    
    async def start_transcription(self, request: TranscriptionRequest, background_tasks: BackgroundTasks) -> str:
        """Start a new transcription job."""
        job_id = str(uuid.uuid4())
        
        # Create initial job status
        job_status = TranscriptionProgress(
            job_id=job_id,
            status=TranscriptionStatus.PROCESSING,
            progress=0.0,
            message="Queued for transcription..."
        )
        
        self.active_jobs[job_id] = job_status
        
        # Add to job queue
        await self.job_queue.put((job_id, request))
        await self._broadcast_progress(job_id)
        
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[TranscriptionProgress]:
        """Get the status of a transcription job."""
        return self.active_jobs.get(job_id)
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a transcription job."""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job.status == TranscriptionStatus.PROCESSING:
                job.status = TranscriptionStatus.ERROR
                job.message = "Job cancelled by user"
                return True
        return False
    
    async def list_active_jobs(self) -> Dict[str, TranscriptionProgress]:
        """List all active transcription jobs."""
        return self.active_jobs.copy()
    
    async def get_queue_status(self) -> dict:
        """Get transcription queue status."""
        return {
            "queue_size": self.job_queue.qsize(),
            "processing_jobs": len(self.processing_jobs),
            "max_concurrent": self.max_concurrent_jobs,
            "active_jobs": len(self.active_jobs)
        }
    
    async def _process_job_queue(self):
        """Process jobs from the queue with concurrency limits."""
        while True:
            try:
                # Wait for a job to be available
                job_id, request = await self.job_queue.get()
                
                # Wait if we're at max concurrent jobs
                while len(self.processing_jobs) >= self.max_concurrent_jobs:
                    await asyncio.sleep(1)
                
                # Start processing the job
                self.processing_jobs.add(job_id)
                asyncio.create_task(self._run_transcription_with_cleanup(job_id, request))
                
            except Exception as e:
                print(f"❌ Error in job queue processor: {e}")
                await asyncio.sleep(5)  # Wait before retrying
    
    async def _run_transcription_with_cleanup(self, job_id: str, request: TranscriptionRequest):
        """Run transcription and clean up processing set."""
        try:
            await self._run_transcription(job_id, request)
        finally:
            self.processing_jobs.discard(job_id)
    
    async def _broadcast_progress(self, job_id: str):
        """Broadcast job progress via WebSocket."""
        if self.websocket_manager and job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            progress_data = {
                "job_id": job.job_id,
                "status": job.status.value,
                "progress": job.progress,
                "message": job.message,
                "error": job.error
            }
            await self.websocket_manager.broadcast_transcription_progress(job_id, progress_data)
    
    async def _run_transcription(self, job_id: str, request: TranscriptionRequest):
        """Run the actual transcription process."""
        try:
            job = self.active_jobs[job_id]
            
            # Update progress: Starting
            job.message = "Starting transcription..."
            job.progress = 5.0
            await self._broadcast_progress(job_id)
            
            # Update progress: Preparing
            job.message = "Preparing transcription..."
            job.progress = 10.0
            await self._broadcast_progress(job_id)
            
            # Find the audio file
            audio_file = None
            for file_path in Path(self.settings.audio_directory).glob("*.mp3"):
                if self._generate_file_id(file_path) == request.file_id:
                    audio_file = file_path
                    break
            
            if not audio_file:
                raise Exception(f"Audio file not found for ID: {request.file_id}")
            
            # Update progress: Starting transcription
            job.message = f"Transcribing with {request.service}..."
            job.progress = 20.0
            await self._broadcast_progress(job_id)
            
            # Update progress: Processing audio
            job.message = "Processing audio file..."
            job.progress = 30.0
            await self._broadcast_progress(job_id)
            
            # Run transcription using existing orchestrator
            # Note: This is a synchronous call, so we'll simulate progress updates
            asyncio.create_task(self._simulate_progress_updates(job_id))
            
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                self.orchestrator.run_transcription_workflow,
                audio_file.parent,
                request.service,
                request.output_formats,
                [],  # glossary_files
                request.compress_audio
            )
            
            if result.get('success', False):
                job.status = TranscriptionStatus.COMPLETED
                job.progress = 100.0
                job.message = "Transcription completed successfully"
            else:
                job.status = TranscriptionStatus.ERROR
                job.message = f"Transcription failed: {'; '.join(result.get('errors', ['Unknown error']))}"
            
            await self._broadcast_progress(job_id)
            
        except Exception as e:
            job = self.active_jobs.get(job_id)
            if job:
                job.status = TranscriptionStatus.ERROR
                job.message = f"Transcription error: {str(e)}"
                job.error = str(e)
                await self._broadcast_progress(job_id)
    
    async def _simulate_progress_updates(self, job_id: str):
        """Simulate progress updates during transcription."""
        if job_id not in self.active_jobs:
            return
        
        job = self.active_jobs[job_id]
        progress_steps = [
            (40.0, "Uploading audio to transcription service..."),
            (50.0, "Transcription in progress..."),
            (70.0, "Processing speaker diarization..."),
            (85.0, "Generating output formats..."),
            (95.0, "Finalizing transcription...")
        ]
        
        for progress, message in progress_steps:
            if job.status != TranscriptionStatus.PROCESSING:
                break
            
            await asyncio.sleep(2)  # Wait 2 seconds between updates
            
            if job_id in self.active_jobs and job.status == TranscriptionStatus.PROCESSING:
                job.progress = progress
                job.message = message
                await self._broadcast_progress(job_id)
    
    def _generate_file_id(self, file_path: Path) -> str:
        """Generate file ID matching the file manager."""
        import hashlib
        file_info = f"{file_path}_{file_path.stat().st_mtime}_{file_path.stat().st_size}"
        return hashlib.md5(file_info.encode()).hexdigest()[:12]