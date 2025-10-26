"""Main CLI entry point for the Audio Transcription System."""

import click
from pathlib import Path
from typing import Optional

from ..utils.config import ConfigManager


@click.command()
@click.argument('audio_directory', type=click.Path(exists=True, path_type=Path))
@click.option('--service', 
              type=click.Choice(['assemblyai', 'deepgram']), 
              default='assemblyai', 
              help='Transcription service to use')
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
              help='Compress audio files before upload to reduce upload time')
@click.option('--glossary', 
              type=click.Path(exists=True, path_type=Path), 
              help='Path to custom glossary file')
@click.option('--api-key', 
              help='Transcription service API key')
@click.option('--config', 
              type=click.Path(path_type=Path), 
              help='Path to configuration file')
def transcribe(
    audio_directory: Path,
    service: str,
    mode: str,
    output_format: str,
    compress_audio: bool,
    glossary: Optional[Path],
    api_key: Optional[str],
    config: Optional[Path]
) -> None:
    """Transcribe MP3 files in the specified directory."""
    
    # Initialize configuration
    config_manager = ConfigManager(config)
    
    # Placeholder for main transcription logic
    click.echo(f"Audio Transcription System")
    click.echo(f"Directory: {audio_directory}")
    click.echo(f"Service: {service}")
    click.echo(f"Mode: {mode}")
    click.echo(f"Output Format: {output_format}")
    
    if compress_audio:
        click.echo("Audio compression enabled")
    
    if glossary:
        click.echo(f"Custom glossary: {glossary}")
    
    # TODO: Implement main transcription workflow


def main():
    """Entry point for console script."""
    transcribe()


if __name__ == '__main__':
    main()