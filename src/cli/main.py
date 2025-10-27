"""Main CLI entry point for the Audio Transcription System."""

import click
import asyncio
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..utils.config import ConfigManager
from ..utils.file_scanner import MP3FileScanner, OutputDirectoryManager
from ..utils.cache_manager import CacheManager, ResumeManager
from ..utils.audio_processor import AudioProcessor
from ..utils.audio_validator import AudioValidator
from ..services.service_factory import TranscriptionServiceFactory
from ..formatters.formatter_factory import FormatterFactory
from ..utils.exceptions import (
    AudioValidationError, TranscriptionServiceError, 
    AuthenticationError, ConfigurationError
)


@click.command()
@click.argument('audio_directory', type=click.Path(exists=True, path_type=Path))
@click.option('--service', 
              type=click.Choice(['assemblyai', 'deepgram', 'openai']), 
              help='Transcription service to use (default from config)')
@click.option('--mode', 
              type=click.Choice(['transcribe', 'format-only']), 
              default='transcribe', 
              help='Transcribe audio or reformat cached responses')
@click.option('--output-format', 
              type=click.Choice(['html', 'markdown', 'both']), 
              default='both', 
              help='Output format for transcriptions')
@click.option('--compress-audio', 
              is_flag=True, 
              default=True,
              help='Compress audio files before upload to reduce upload time')
@click.option('--compression-format',
              type=click.Choice(['mp3', 'm4a']),
              default='m4a',
              help='Audio compression format (default: m4a for better efficiency)')
@click.option('--glossary', 
              type=click.Path(exists=True, path_type=Path), 
              multiple=True,
              help='Path to custom glossary file (can be used multiple times)')
@click.option('--api-key', 
              help='Transcription service API key (overrides environment variable)')
@click.option('--config', 
              type=click.Path(path_type=Path), 
              help='Path to configuration file')
@click.option('--output-dir',
              type=click.Path(path_type=Path),
              help='Output directory (default: audio_directory/transcriptions)')
@click.option('--fail-fast',
              is_flag=True,
              default=True,
              help='Stop on first error (default: true)')
@click.option('--verbose', '-v',
              is_flag=True,
              help='Enable verbose output')
@click.option('--force',
              is_flag=True,
              help='Force re-transcription even if cached results exist')
@click.option('--create-default-glossary',
              type=click.Path(path_type=Path),
              help='Create default RBTI glossary file and exit')
def transcribe(
    audio_directory: Path,
    service: Optional[str],
    mode: str,
    output_format: str,
    compress_audio: bool,
    compression_format: str,
    glossary: tuple,
    api_key: Optional[str],
    config: Optional[Path],
    output_dir: Optional[Path],
    fail_fast: bool,
    verbose: bool,
    force: bool,
    create_default_glossary: Optional[Path]
) -> None:
    """Transcribe MP3 files in the specified directory.
    
    AUDIO_DIRECTORY: Directory containing MP3 files to transcribe
    """
    
    try:
        # Initialize configuration
        config_manager = ConfigManager(config)
        
        # Handle special commands
        if create_default_glossary:
            service_factory = TranscriptionServiceFactory(config_manager)
            service_factory.create_default_glossary(create_default_glossary)
            click.echo(f"✅ Created default RBTI glossary at {create_default_glossary}")
            return
        
        # Set API key if provided
        if api_key and service:
            os.environ[f"{service.upper()}_API_KEY"] = api_key
        
        # Determine service to use
        if not service:
            service = config_manager.get('transcription.default_service', 'assemblyai')
        
        # Set up output directory
        if not output_dir:
            output_dir = audio_directory / "transcriptions"
        
        # Parse output formats
        output_formats = _parse_output_formats(output_format)
        
        # Convert glossary tuple to list of Paths
        glossary_files = [Path(g) for g in glossary] if glossary else []
        
        # Use extracted glossary by default if no glossary specified
        if not glossary_files:
            default_glossary = Path("extracted_rbti_glossary.txt")
            if default_glossary.exists():
                glossary_files = [default_glossary]
                if verbose:
                    click.echo(f"📚 Using default extracted glossary: {default_glossary}")
            else:
                # Fallback to example glossary
                example_glossary = Path("example_rbti_glossary.txt")
                if example_glossary.exists():
                    glossary_files = [example_glossary]
                    if verbose:
                        click.echo(f"📚 Using example glossary: {example_glossary}")
        
        if verbose:
            click.echo("🔧 Configuration:")
            click.echo(f"  Audio Directory: {audio_directory}")
            click.echo(f"  Output Directory: {output_dir}")
            click.echo(f"  Service: {service}")
            click.echo(f"  Mode: {mode}")
            click.echo(f"  Output Formats: {', '.join(output_formats)}")
            click.echo(f"  Compress Audio: {compress_audio}")
            click.echo(f"  Glossary Files: {len(glossary_files)}")
            click.echo(f"  Fail Fast: {fail_fast}")
        
        # Clear cache if force flag is used
        if force and mode == 'transcribe':
            cache_dir = output_dir / "cache"
            if cache_dir.exists():
                import shutil
                shutil.rmtree(cache_dir)
                if verbose:
                    click.echo("🗑️  Cleared cache directory (force mode)")

        # Run the appropriate workflow using orchestrator
        asyncio.run(_run_orchestrated_workflow(
            audio_directory, output_dir, service, output_formats,
            compress_audio, compression_format, glossary_files, config_manager,
            mode, fail_fast, verbose
        ))
    
    except KeyboardInterrupt:
        click.echo("\n❌ Operation cancelled by user")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Error: {str(e)}")
        if verbose:
            import traceback
            traceback.print_exc()
        raise click.Abort()





def _parse_output_formats(output_format: str) -> List[str]:
    """Parse output format option into list of formats."""
    if output_format == 'both':
        return ['html', 'markdown']
    else:
        return [output_format]


async def _run_orchestrated_workflow(
    audio_directory: Path, output_dir: Path, service: str, 
    output_formats: List[str], compress_audio: bool, compression_format: str,
    glossary_files: List[Path], config_manager: ConfigManager,
    mode: str, fail_fast: bool, verbose: bool
) -> None:
    """Run workflow using the orchestrator."""
    
    from ..core.transcription_orchestrator import TranscriptionOrchestrator
    
    orchestrator = TranscriptionOrchestrator(
        config_manager=config_manager,
        output_dir=output_dir,
        verbose=verbose,
        fail_fast=fail_fast
    )
    
    if mode == 'transcribe':
        result = await orchestrator.run_transcription_workflow(
            audio_directory=audio_directory,
            service=service,
            output_formats=output_formats,
            glossary_files=glossary_files,
            compress_audio=compress_audio,
            compression_format=compression_format
        )
    else:  # format-only
        result = await orchestrator.run_format_only_workflow(
            audio_directory=audio_directory,
            service=service,
            output_formats=output_formats,
            glossary_files=glossary_files
        )
    
    # Print final summary
    _print_workflow_summary(result, verbose)


def _print_workflow_summary(result: Dict[str, Any], verbose: bool) -> None:
    """Print workflow execution summary."""
    click.echo(f"\n📊 Final Summary:")
    click.echo(f"  📁 Total files: {result.get('total_files', 0)}")
    
    if 'successful_files' in result:
        click.echo(f"  ✅ Successful: {result['successful_files']}")
    if 'failed_files' in result:
        click.echo(f"  ❌ Failed: {result['failed_files']}")
    if 'skipped_files' in result:
        click.echo(f"  ⏭️  Skipped: {result['skipped_files']}")
    
    if result.get('processing_time'):
        minutes = int(result['processing_time'] // 60)
        seconds = int(result['processing_time'] % 60)
        click.echo(f"  ⏱️  Processing time: {minutes}m {seconds}s")
    
    click.echo(f"  📂 Output directory: {result['output_directory']}")
    
    if result.get('errors') and verbose:
        click.echo(f"\n⚠️  Errors encountered:")
        for error in result['errors'][:5]:  # Show first 5 errors
            click.echo(f"    • {error}")
        if len(result['errors']) > 5:
            click.echo(f"    ... and {len(result['errors']) - 5} more errors")
    
    if result.get('success'):
        click.echo(f"\n🎉 Workflow completed successfully!")
    else:
        click.echo(f"\n⚠️  Workflow completed with errors")


def _build_transcription_config(config_manager: ConfigManager):
    """Build transcription configuration from config manager."""
    from ..services.transcription_client import TranscriptionConfig
    
    return TranscriptionConfig(
        speaker_labels=config_manager.get('transcription.speaker_diarization', True),
        max_speakers=config_manager.get('transcription.max_speakers', 3),
        punctuate=True,
        format_text=True,
        language_code='en'
    )


def main():
    """Entry point for console script."""
    transcribe()


if __name__ == '__main__':
    main()