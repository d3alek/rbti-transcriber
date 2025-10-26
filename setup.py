"""Setup script for Audio Transcription System."""

from setuptools import setup, find_packages

with open("requirements.txt", "r") as f:
    requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="audio-transcription-system",
    version="0.1.0",
    description="Automated transcription system for MP3 audio files with speaker identification",
    packages=find_packages(),
    install_requires=requirements,
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "transcribe=src.cli.main:main",
        ],
    },
)