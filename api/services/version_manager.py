"""
Deepgram Version Manager Service

Handles version management for Deepgram transcript responses, including
file storage, retrieval, and metadata tracking.
"""

import json
import os
import hashlib
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from ..models import DeepgramVersion, DeepgramResponse


class DeepgramVersionManager:
    """Manages versioned storage of Deepgram transcript responses."""
    
    def __init__(self, base_path: str = "transcriptions"):
        """
        Initialize the version manager.
        
        Args:
            base_path: Base directory for storing transcription files
        """
        self.base_path = Path(base_path)
        self.versions_dir = self.base_path / "versions"
        self.cache_dir = self.base_path / "cache"
        
        # Ensure directories exist
        self.versions_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_audio_hash(self, audio_file: str) -> str:
        """
        Generate a hash for the audio file to use as identifier.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            SHA256 hash of the audio file path
        """
        return hashlib.sha256(audio_file.encode()).hexdigest()[:16]
    
    def _get_version_dir(self, audio_file: str) -> Path:
        """
        Get the version directory for a specific audio file.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Path to the version directory
        """
        audio_hash = self._get_audio_hash(audio_file)
        version_dir = self.versions_dir / audio_hash
        version_dir.mkdir(parents=True, exist_ok=True)
        return version_dir
    
    def _get_metadata_file(self, audio_file: str) -> Path:
        """
        Get the metadata file path for a specific audio file.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Path to the metadata file
        """
        version_dir = self._get_version_dir(audio_file)
        return version_dir / "metadata.json"
    
    def _load_metadata(self, audio_file: str) -> Dict[str, Any]:
        """
        Load metadata for an audio file's versions.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Metadata dictionary
        """
        metadata_file = self._get_metadata_file(audio_file)
        
        if not metadata_file.exists():
            return {
                "audio_file": audio_file,
                "versions": [],
                "next_version": 0
            }
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            # If metadata is corrupted, start fresh
            return {
                "audio_file": audio_file,
                "versions": [],
                "next_version": 0
            }
    
    def _save_metadata(self, audio_file: str, metadata: Dict[str, Any]) -> None:
        """
        Save metadata for an audio file's versions.
        
        Args:
            audio_file: Path to the audio file
            metadata: Metadata dictionary to save
        """
        metadata_file = self._get_metadata_file(audio_file)
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
        except IOError as e:
            raise RuntimeError(f"Failed to save metadata: {e}")
    
    def _get_version_file(self, audio_file: str, version: int) -> Path:
        """
        Get the file path for a specific version.
        
        Args:
            audio_file: Path to the audio file
            version: Version number
            
        Returns:
            Path to the version file
        """
        version_dir = self._get_version_dir(audio_file)
        return version_dir / f"v{version}.json"
    
    def save_version(self, audio_file: str, response: DeepgramResponse, 
                    changes: str = "") -> str:
        """
        Save a new version of a Deepgram response.
        
        Args:
            audio_file: Path to the audio file
            response: Deepgram response data
            changes: Description of changes made
            
        Returns:
            Version identifier (filename)
        """
        # Load current metadata
        metadata = self._load_metadata(audio_file)
        
        # Get next version number
        version_num = metadata["next_version"]
        
        # Create version file
        version_file = self._get_version_file(audio_file, version_num)
        
        # Prepare version data
        version_data = {
            "version": version_num,
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "audio_file": audio_file,
            "response": response
        }
        
        try:
            # Save version file
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2, ensure_ascii=False)
            
            # Update metadata
            metadata["versions"].append({
                "version": version_num,
                "filename": version_file.name,
                "timestamp": version_data["timestamp"],
                "changes": changes
            })
            metadata["next_version"] = version_num + 1
            
            # Save updated metadata
            self._save_metadata(audio_file, metadata)
            
            return version_file.name
            
        except IOError as e:
            raise RuntimeError(f"Failed to save version {version_num}: {e}")
    
    def load_versions(self, audio_file: str) -> List[DeepgramVersion]:
        """
        Load all versions for an audio file.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            List of DeepgramVersion objects
        """
        metadata = self._load_metadata(audio_file)
        versions = []
        
        for version_info in metadata["versions"]:
            try:
                version_file = self._get_version_dir(audio_file) / version_info["filename"]
                
                if version_file.exists():
                    with open(version_file, 'r', encoding='utf-8') as f:
                        version_data = json.load(f)
                    
                    versions.append(DeepgramVersion(
                        version=version_data["version"],
                        filename=version_info["filename"],
                        timestamp=version_data["timestamp"],
                        changes=version_data["changes"],
                        response=version_data["response"]
                    ))
                    
            except (json.JSONDecodeError, IOError, KeyError) as e:
                # Skip corrupted version files
                continue
        
        # Sort by version number
        versions.sort(key=lambda v: v.version)
        return versions
    
    def get_version(self, audio_file: str, version: int) -> Optional[DeepgramResponse]:
        """
        Get a specific version of a Deepgram response.
        
        Args:
            audio_file: Path to the audio file
            version: Version number to retrieve
            
        Returns:
            DeepgramResponse object or None if not found
        """
        version_file = self._get_version_file(audio_file, version)
        
        if not version_file.exists():
            return None
        
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                version_data = json.load(f)
            
            # Convert dictionary to DeepgramResponse object
            response_dict = version_data["response"]
            return DeepgramResponse(**response_dict)
            
        except (json.JSONDecodeError, IOError, KeyError):
            return None
    
    def delete_version(self, audio_file: str, version: int) -> bool:
        """
        Delete a specific version.
        
        Args:
            audio_file: Path to the audio file
            version: Version number to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        version_file = self._get_version_file(audio_file, version)
        
        if not version_file.exists():
            return False
        
        try:
            # Remove version file
            version_file.unlink()
            
            # Update metadata
            metadata = self._load_metadata(audio_file)
            metadata["versions"] = [
                v for v in metadata["versions"] 
                if v["version"] != version
            ]
            self._save_metadata(audio_file, metadata)
            
            return True
            
        except (IOError, OSError) as e:
            return False
    
    def get_latest_version(self, audio_file: str) -> Optional[DeepgramResponse]:
        """
        Get the latest version of a Deepgram response.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Latest DeepgramResponse or None if no versions exist
        """
        versions = self.load_versions(audio_file)
        
        if not versions:
            return None
        
        latest_version = max(versions, key=lambda v: v.version)
        return latest_version.response
    
    def initialize_from_cache(self, audio_file: str) -> Optional[str]:
        """
        Initialize version 0 from existing cache file if it exists.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Version filename if initialized, None otherwise
        """
        # Check if version 0 already exists
        if self.get_version(audio_file, 0) is not None:
            return None
        
        # Look for cached response by scanning all cache files
        # since the cache file names are hashed differently
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        cached_data = json.load(f)
                    
                    # Check if this cache file matches our audio file
                    if cached_data.get('audio_file') == audio_file:
                        # Extract the raw Deepgram response
                        deepgram_response = None
                        
                        if "raw_response" in cached_data:
                            deepgram_response = cached_data["raw_response"]
                        elif "result" in cached_data and cached_data.get("service") == "deepgram":
                            result = cached_data["result"]
                            
                            # Check if raw_response is nested inside result
                            if isinstance(result, dict) and "raw_response" in result:
                                deepgram_response = result["raw_response"]
                            elif isinstance(result, dict) and "metadata" in result and "results" in result:
                                deepgram_response = result
                            else:
                                # Skip this cache file as it doesn't have raw Deepgram data
                                continue
                        else:
                            continue
                        
                        if deepgram_response:
                            # Save as version 0 (original)
                            return self.save_version(
                                audio_file, 
                                deepgram_response, 
                                "Original Deepgram response from cache"
                            )
                        
                except (json.JSONDecodeError, IOError, KeyError):
                    # Skip corrupted cache files
                    continue
            
            return None
            
        except Exception:
            return None
    
    def get_version_count(self, audio_file: str) -> int:
        """
        Get the total number of versions for an audio file.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Number of versions
        """
        metadata = self._load_metadata(audio_file)
        return len(metadata["versions"])
    
    def version_exists(self, audio_file: str, version: int) -> bool:
        """
        Check if a specific version exists.
        
        Args:
            audio_file: Path to the audio file
            version: Version number to check
            
        Returns:
            True if version exists, False otherwise
        """
        version_file = self._get_version_file(audio_file, version)
        return version_file.exists()
    
    def get_version_info(self, audio_file: str, version: int) -> Optional[Dict[str, Any]]:
        """
        Get metadata information for a specific version.
        
        Args:
            audio_file: Path to the audio file
            version: Version number
            
        Returns:
            Version info dictionary or None if not found
        """
        metadata = self._load_metadata(audio_file)
        
        for version_info in metadata["versions"]:
            if version_info["version"] == version:
                return version_info
        
        return None
    
    def cleanup_orphaned_files(self, audio_file: str) -> int:
        """
        Clean up orphaned version files that are not in metadata.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Number of files cleaned up
        """
        version_dir = self._get_version_dir(audio_file)
        metadata = self._load_metadata(audio_file)
        
        # Get list of valid version files from metadata
        valid_files = {v["filename"] for v in metadata["versions"]}
        valid_files.add("metadata.json")  # Don't delete metadata
        
        cleaned_count = 0
        
        try:
            for file_path in version_dir.iterdir():
                if file_path.is_file() and file_path.name not in valid_files:
                    if file_path.name.startswith("v") and file_path.name.endswith(".json"):
                        file_path.unlink()
                        cleaned_count += 1
        except OSError:
            pass
        
        return cleaned_count
    
    def get_storage_info(self, audio_file: str) -> Dict[str, Any]:
        """
        Get storage information for an audio file's versions.
        
        Args:
            audio_file: Path to the audio file
            
        Returns:
            Storage information dictionary
        """
        version_dir = self._get_version_dir(audio_file)
        metadata = self._load_metadata(audio_file)
        
        total_size = 0
        file_count = 0
        
        try:
            for file_path in version_dir.iterdir():
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
        except OSError:
            pass
        
        return {
            "version_count": len(metadata["versions"]),
            "total_files": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "directory": str(version_dir)
        }