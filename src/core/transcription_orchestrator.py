"""Main orchestrator for the transcription workflow."""

import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import time

from ..utils.config import ConfigManager
from ..utils.file_scanner import MP3FileScanner, OutputDirectoryManager
from ..utils.cache_manager import CacheManager, ResumeManager
from ..utils.audio_processor import AudioProcessor
from ..utils.audio_validator import AudioValidator
from ..utils.progress_tracker import ProgressTracker
from ..utils.error_handler import ErrorHandler, handle_file_processing_error, handle_service_unavailable
from ..services.service_factory import TranscriptionServiceFactory
from ..services.transcription_client import TranscriptionConfig
from ..formatters.formatter_factory import FormatterFactory
from ..utils.exceptions import TranscriptionSystemError


class TranscriptionOrchestrator:
    """Main orchestrator that coordinates all transcription workflow components."""
    
    def __init__(self, config_manager: ConfigManager, output_dir: Path, 
                 verbose: bool = False, fail_fast: bool = True):
        self.config_manager = config_manager
        self.output_dir = Path(output_dir)
        self.verbose = verbose
        self.fail_fast = fail_fast
        
        # Initialize core components
        # Note: output_manager is now created per-file in the new structure
        self.cache_manager = CacheManager(self.output_dir / "cache")  # Keep global cache for now
        self.service_factory = TranscriptionServiceFactory(config_manager)
        self.error_handler = ErrorHandler(
            log_file=self.output_dir / "transcription.log",
            verbose=verbose
        )
        
        # Create a simplified resume manager that works with the new structure
        from ..utils.cache_manager import ResumeManager
        self.resume_manager = ResumeManager(self.cache_manager, None)  # We'll handle resume logic differently
        
        # Optional components
        self.audio_processor: Optional[AudioProcessor] = None
        self.audio_validator: Optional[AudioValidator] = None
        self.progress_tracker: Optional[ProgressTracker] = None
    
    def setup_audio_processing(self, enable_compression: bool = False) -> None:
        """Set up audio processing components."""
        if enable_compression:
            # Use a temporary directory for audio processing, files will be moved to correct locations
            self.audio_processor = AudioProcessor(self.output_dir / "temp_compressed")
        
        self.audio_validator = AudioValidator(self.audio_processor)
    
    async def run_transcription_workflow(
        self, 
        audio_directory: Path,
        service: str,
        output_formats: List[str],
        glossary_files: Optional[List[Path]] = None,
        compress_audio: bool = False
    ) -> Dict[str, Any]:
        """Run the complete transcription workflow."""
        
        workflow_result = {
            'success': False,
            'total_files': 0,
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0,
            'skipped_files': 0,
            'errors': [],
            'output_directory': str(self.output_dir),
            'processing_time': 0.0
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Setup and validation
            self.setup_audio_processing(compress_audio)
            
            # Step 2: Scan for MP3 files
            if self.verbose:
                print("🔍 Scanning for MP3 files...")
            
            file_scanner = MP3FileScanner(audio_directory)
            mp3_files = file_scanner.scan_mp3_files()
            
            if not mp3_files:
                workflow_result['errors'].append("No MP3 files found in directory")
                return workflow_result
            
            workflow_result['total_files'] = len(mp3_files)
            
            if self.verbose:
                print(f"📁 Found {len(mp3_files)} MP3 files")
            
            # Step 3: Validate audio files
            if self.audio_validator:
                if self.verbose:
                    print("🔍 Validating audio files...")
                
                validation_results = self.audio_validator.validate_batch(mp3_files, self.fail_fast)
                
                if validation_results['summary']['invalid_count'] > 0:
                    error_msg = f"Found {validation_results['summary']['invalid_count']} invalid files"
                    workflow_result['errors'].append(error_msg)
                    
                    if self.fail_fast:
                        return workflow_result
                
                mp3_files = validation_results['valid_files']
                if self.verbose:
                    print(f"✅ {len(mp3_files)} files passed validation")
            
            # Step 4: Check resume status (simplified for new structure)
            transcription_config = self._build_transcription_config()
            files_to_process = []
            skipped_count = 0
            
            for audio_file in mp3_files:
                # Check if transcription already exists in new structure
                output_manager = OutputDirectoryManager(audio_file)
                if output_manager.transcription_exists():
                    skipped_count += 1
                    if self.verbose:
                        print(f"⏭️  Skipping {audio_file.name} (already transcribed)")
                else:
                    files_to_process.append(audio_file)
            
            workflow_result['skipped_files'] = skipped_count
            
            if not files_to_process:
                if self.verbose:
                    print("✅ All files already processed!")
                workflow_result['success'] = True
                return workflow_result
            
            # Step 5: Initialize progress tracking
            self.progress_tracker = ProgressTracker(len(files_to_process), self.output_dir)
            
            if self.verbose:
                print(f"🎯 Processing {len(files_to_process)} files...")
            
            # Step 6: Create transcription client
            try:
                client = self.service_factory.create_client(service, glossary_files)
                if self.verbose and glossary_files:
                    glossary_stats = self.service_factory.get_glossary_stats()
                    print(f"📚 Loaded {glossary_stats['total_terms']} glossary terms")
            
            except Exception as e:
                handle_service_unavailable(service, e, self.error_handler)
                workflow_result['errors'].append(f"Service setup failed: {str(e)}")
                return workflow_result
            
            # Step 7: Process files
            workflow_result.update(await self._process_files_batch(
                files_to_process, client, service, transcription_config, output_formats
            ))
            
            # Step 8: Finalize
            if self.progress_tracker:
                self.progress_tracker.finish_batch()
                
                # Export progress report
                report_path = self.output_dir / "transcription_report.json"
                self.progress_tracker.export_report(report_path)
            
            workflow_result['success'] = workflow_result['failed_files'] == 0 or not self.fail_fast
            workflow_result['processing_time'] = time.time() - start_time
            
        except Exception as e:
            self.error_handler.handle_error(e, {'operation': 'transcription_workflow'})
            workflow_result['errors'].append(f"Workflow error: {str(e)}")
        
        return workflow_result
    
    async def _process_files_batch(
        self,
        files_to_process: List[Path],
        client,
        service: str,
        transcription_config: TranscriptionConfig,
        output_formats: List[str]
    ) -> Dict[str, Any]:
        """Process a batch of files for transcription."""
        
        batch_result = {
            'processed_files': 0,
            'successful_files': 0,
            'failed_files': 0
        }
        
        for audio_file in files_to_process:
            try:
                # Start tracking this file
                if self.progress_tracker:
                    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
                    self.progress_tracker.start_file(audio_file, file_size_mb)
                
                # Process single file
                file_result = await self._process_single_file(
                    audio_file, client, service, transcription_config, output_formats
                )
                
                batch_result['processed_files'] += 1
                
                if file_result['success']:
                    batch_result['successful_files'] += 1
                    if self.progress_tracker:
                        self.progress_tracker.complete_file(
                            audio_file, 
                            list(file_result.get('formatted_files', {}).keys()),
                            file_result.get('processing_time', 0.0)
                        )
                    
                    if self.verbose:
                        formats = ', '.join(file_result.get('formatted_files', {}).keys())
                        print(f"✅ {audio_file.name} -> {formats}")
                
                else:
                    batch_result['failed_files'] += 1
                    error_msg = '; '.join(file_result.get('errors', ['Unknown error']))
                    
                    if self.progress_tracker:
                        self.progress_tracker.fail_file(audio_file, error_msg)
                    
                    if self.verbose:
                        print(f"❌ {audio_file.name}: {error_msg}")
                    
                    if self.fail_fast:
                        break
            
            except Exception as e:
                batch_result['failed_files'] += 1
                
                if not handle_file_processing_error(audio_file, e, self.error_handler, self.fail_fast):
                    break
                
                if self.progress_tracker:
                    self.progress_tracker.fail_file(audio_file, str(e))
        
        return batch_result
    
    async def _process_single_file(
        self,
        audio_file: Path,
        client,
        service: str,
        transcription_config: TranscriptionConfig,
        output_formats: List[str]  # Ignored in new structure
    ) -> Dict[str, Any]:
        """Process a single audio file through the simplified workflow."""
        
        file_result = {
            'success': False,
            'audio_file': str(audio_file),
            'transcription_file': None,
            'compressed_file': None,
            'errors': [],
            'processing_time': 0.0
        }
        
        start_time = time.time()
        
        try:
            # Create output manager for this specific audio file
            output_manager = OutputDirectoryManager(audio_file)
            output_manager.create_output_structure()
            
            # Get original file size
            original_size_mb = audio_file.stat().st_size / (1024 * 1024)
            
            if self.verbose:
                print(f"📄 Processing {audio_file.name} ({original_size_mb:.1f} MB)")
                print(f"📁 Output: {output_manager.seminar_group_dir.name}/")
            
            # Step 1: Determine which file to use for transcription (compress if needed)
            file_to_transcribe = audio_file
            compressed_audio_path = output_manager.get_compressed_audio_path()
            
            if self.audio_processor:
                try:
                    if self.verbose:
                        print(f"🗜️  Compressing audio for transcription and storage...")
                    
                    # Always compress for transcription to save bandwidth
                    compressed_file = self.audio_processor.compress_audio(audio_file, force=True)
                    
                    # Move compressed file to correct location
                    import shutil
                    shutil.move(str(compressed_file), str(compressed_audio_path))
                    
                    # Use compressed file for transcription
                    file_to_transcribe = compressed_audio_path
                    
                    compressed_size_mb = compressed_audio_path.stat().st_size / (1024 * 1024)
                    compression_ratio = (1 - compressed_size_mb / original_size_mb) * 100
                    
                    if self.verbose:
                        print(f"✅ Compressed: {original_size_mb:.1f} MB → {compressed_size_mb:.1f} MB ({compression_ratio:.1f}% reduction)")
                        print(f"💾 Saved: {compressed_audio_path.relative_to(audio_file.parent)}")
                        print(f"📤 Will upload compressed file to save bandwidth")
                    
                    file_result['compressed_file'] = str(compressed_audio_path)
                    
                except Exception as compression_error:
                    if self.verbose:
                        print(f"⚠️  Compression failed: {compression_error}")
                        print(f"📤 Will upload original file instead")
                    # Fall back to original file if compression fails
                    file_to_transcribe = audio_file
            else:
                if self.verbose:
                    print(f"ℹ️  Audio compression disabled")
            
            # Step 2: Upload and transcribe (use compressed file if available)
            upload_size_mb = file_to_transcribe.stat().st_size / (1024 * 1024)
            
            if self.verbose:
                print(f"📤 Uploading to {service.upper()} ({upload_size_mb:.1f} MB)...")
            
            upload_start = time.time()
            
            # Use Deepgram for transcription
            result = await client.transcribe_file(file_to_transcribe, transcription_config)
            
            upload_time = time.time() - upload_start
            
            if self.verbose:
                print(f"✅ Transcription completed in {upload_time:.1f}s")
                print(f"📊 Confidence: {result.confidence:.1%}, Duration: {result.audio_duration:.1f}s")
                print(f"👥 Found {len(set(s.speaker for s in result.speakers))} speakers, {len(result.speakers)} segments")
            
            # Step 3: Save raw Deepgram response to correct location
            transcription_path = output_manager.get_transcription_path()
            
            try:
                import json
                
                # Create the complete response structure matching the cache format
                transcription_data = {
                    "audio_file": str(audio_file),
                    "service": service,
                    "config": transcription_config.__dict__,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                    "result": {
                        "text": result.text,
                        "speakers": [
                            {
                                "speaker": segment.speaker,
                                "start_time": segment.start_time,
                                "end_time": segment.end_time,
                                "text": segment.text,
                                "confidence": segment.confidence
                            }
                            for segment in result.speakers
                        ],
                        "confidence": result.confidence,
                        "audio_duration": result.audio_duration,
                        "processing_time": result.processing_time,
                        "raw_response": result.raw_response  # Include the complete raw Deepgram response
                    }
                }
                
                with open(transcription_path, 'w', encoding='utf-8') as f:
                    json.dump(transcription_data, f, indent=2, ensure_ascii=False)
                
                file_result['transcription_file'] = str(transcription_path)
                file_result['success'] = True
                
                if self.verbose:
                    transcription_size_kb = transcription_path.stat().st_size / 1024
                    print(f"💾 Saved transcription: {transcription_path.relative_to(audio_file.parent)} ({transcription_size_kb:.1f} KB)")
                
            except Exception as save_error:
                error_msg = f"Failed to save transcription: {save_error}"
                file_result['errors'].append(error_msg)
                if self.verbose:
                    print(f"❌ {error_msg}")
            
            file_result['processing_time'] = time.time() - start_time
        
        except Exception as e:
            if self.verbose:
                print(f"❌ Error processing {audio_file.name}: {str(e)}")
            file_result['errors'].append(str(e))
            file_result['processing_time'] = time.time() - start_time
        
        return file_result
    
    def _build_transcription_config(self) -> TranscriptionConfig:
        """Build transcription configuration from config manager."""
        return TranscriptionConfig(
            speaker_labels=self.config_manager.get('transcription.speaker_diarization', True),
            max_speakers=self.config_manager.get('transcription.max_speakers', 3),
            punctuate=True,
            format_text=True,
            language_code='en'
        )
    
    async def run_format_only_workflow(
        self,
        audio_directory: Path,
        service: str,
        output_formats: List[str],
        glossary_files: Optional[List[Path]] = None
    ) -> Dict[str, Any]:
        """Run format-only workflow using cached transcription results."""
        
        workflow_result = {
            'success': False,
            'total_files': 0,
            'files_with_cache': 0,
            'files_without_cache': 0,
            'successful_files': 0,
            'failed_files': 0,
            'errors': [],
            'output_directory': str(self.output_dir),
            'processing_time': 0.0
        }
        
        start_time = time.time()
        
        try:
            # Step 1: Setup
            self.output_manager.create_output_structure()
            
            # Step 2: Scan for MP3 files
            if self.verbose:
                print("🔍 Scanning for MP3 files...")
            
            file_scanner = MP3FileScanner(audio_directory)
            mp3_files = file_scanner.scan_mp3_files()
            
            if not mp3_files:
                workflow_result['errors'].append("No MP3 files found in directory")
                return workflow_result
            
            workflow_result['total_files'] = len(mp3_files)
            
            if self.verbose:
                print(f"📁 Found {len(mp3_files)} MP3 files")
            
            # Step 3: Check cache status
            transcription_config = self._build_transcription_config()
            cache_status = self.formatter_factory.get_cache_formatting_status(
                mp3_files, service, transcription_config.__dict__
            )
            
            files_with_cache = cache_status['files_with_cache']
            files_without_cache = cache_status['files_without_cache']
            
            workflow_result['files_with_cache'] = len(files_with_cache)
            workflow_result['files_without_cache'] = len(files_without_cache)
            
            if self.verbose:
                print(f"💾 Cache status: {len(files_with_cache)}/{len(mp3_files)} files have cached results")
            
            if not files_with_cache:
                workflow_result['errors'].append("No cached transcription results found")
                return workflow_result
            
            if files_without_cache and self.verbose:
                print(f"⚠️  {len(files_without_cache)} files have no cached results and will be skipped")
            
            # Step 4: Initialize progress tracking
            self.progress_tracker = ProgressTracker(len(files_with_cache), self.output_dir)
            
            if self.verbose:
                print(f"🎨 Formatting {len(files_with_cache)} files from cache...")
            
            # Step 5: Format files from cache
            batch_result = await self._format_files_from_cache_batch(
                files_with_cache, service, transcription_config, output_formats
            )
            
            workflow_result.update(batch_result)
            
            # Step 6: Finalize
            if self.progress_tracker:
                self.progress_tracker.finish_batch()
                
                # Export progress report
                report_path = self.output_dir / "format_only_report.json"
                self.progress_tracker.export_report(report_path)
            
            workflow_result['success'] = workflow_result['failed_files'] == 0 or not self.fail_fast
            workflow_result['processing_time'] = time.time() - start_time
            
        except Exception as e:
            self.error_handler.handle_error(e, {'operation': 'format_only_workflow'})
            workflow_result['errors'].append(f"Format-only workflow error: {str(e)}")
        
        return workflow_result
    
    async def _format_files_from_cache_batch(
        self,
        files_with_cache: List[Path],
        service: str,
        transcription_config: TranscriptionConfig,
        output_formats: List[str]
    ) -> Dict[str, Any]:
        """Format a batch of files from cached results."""
        
        batch_result = {
            'successful_files': 0,
            'failed_files': 0
        }
        
        for audio_file in files_with_cache:
            try:
                # Start tracking this file
                if self.progress_tracker:
                    file_size_mb = audio_file.stat().st_size / (1024 * 1024)
                    self.progress_tracker.start_file(audio_file, file_size_mb)
                
                # Format from cache
                format_result = self.formatter_factory.format_from_cache(
                    audio_file, service, transcription_config.__dict__, 
                    output_formats, self.output_manager
                )
                
                if format_result['success']:
                    batch_result['successful_files'] += 1
                    
                    if self.progress_tracker:
                        self.progress_tracker.complete_file(
                            audio_file, 
                            list(format_result['formatted_files'].keys()),
                            0.0  # No processing time for format-only
                        )
                    
                    if self.verbose:
                        formats = ', '.join(format_result['formatted_files'].keys())
                        print(f"✅ {audio_file.name} -> {formats}")
                
                else:
                    batch_result['failed_files'] += 1
                    error_msg = '; '.join(format_result['errors'])
                    
                    if self.progress_tracker:
                        self.progress_tracker.fail_file(audio_file, error_msg)
                    
                    if self.verbose:
                        print(f"❌ {audio_file.name}: {error_msg}")
                    
                    if self.fail_fast:
                        break
            
            except Exception as e:
                batch_result['failed_files'] += 1
                
                if not handle_file_processing_error(audio_file, e, self.error_handler, self.fail_fast):
                    break
                
                if self.progress_tracker:
                    self.progress_tracker.fail_file(audio_file, str(e))
        
        return batch_result
    
    def validate_format_only_requirements(
        self,
        audio_directory: Path,
        service: str,
        output_formats: List[str]
    ) -> Dict[str, Any]:
        """Validate that format-only mode requirements are met."""
        
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'cache_status': {}
        }
        
        try:
            # Check if cache directory exists
            cache_dir = self.output_dir / "cache"
            if not cache_dir.exists():
                validation_result['is_valid'] = False
                validation_result['errors'].append("No cache directory found - run transcription first")
                return validation_result
            
            # Scan for MP3 files
            file_scanner = MP3FileScanner(audio_directory)
            mp3_files = file_scanner.scan_mp3_files()
            
            if not mp3_files:
                validation_result['is_valid'] = False
                validation_result['errors'].append("No MP3 files found in directory")
                return validation_result
            
            # Check cache status
            transcription_config = self._build_transcription_config()
            cache_status = self.formatter_factory.get_cache_formatting_status(
                mp3_files, service, transcription_config.__dict__
            )
            
            validation_result['cache_status'] = {
                'total_files': len(mp3_files),
                'files_with_cache': len(cache_status['files_with_cache']),
                'files_without_cache': len(cache_status['files_without_cache']),
                'cache_hit_rate': cache_status['cache_hit_rate']
            }
            
            if not cache_status['files_with_cache']:
                validation_result['is_valid'] = False
                validation_result['errors'].append("No cached transcription results found")
            elif cache_status['files_without_cache']:
                validation_result['warnings'].append(
                    f"{len(cache_status['files_without_cache'])} files have no cached results"
                )
            
            # Validate output formats
            for format_type in output_formats:
                format_validation = self.formatter_factory.validate_format_configuration(format_type)
                if not format_validation['is_configured']:
                    validation_result['errors'].extend(format_validation['errors'])
                validation_result['warnings'].extend(format_validation['warnings'])
        
        except Exception as e:
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
        
        return validation_result
    
    def get_workflow_summary(self) -> Dict[str, Any]:
        """Get summary of the workflow execution."""
        summary = {
            'error_summary': self.error_handler.get_error_summary(),
            'output_directory': str(self.output_dir)
        }
        
        if self.progress_tracker:
            summary['progress_summary'] = self.progress_tracker.get_summary_report()
        
        return summary