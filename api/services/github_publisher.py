"""GitHub Pages publisher service."""

import json
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import git
import shutil

from ..models import PublicationRequest, PublicationStatus
from ..config import Settings


class GitHubPublisher:
    """Manages publishing transcriptions to GitHub Pages."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.repo_url = settings.github_repository_url
        self.token = settings.github_token
        self.branch = settings.github_branch
        self.base_url = settings.github_base_url
        
        # Local repository path
        self.repo_dir = Path(tempfile.gettempdir()) / "transcription_site_repo"
        
        # Publication tracking
        self.published_files: Dict[str, PublicationStatus] = {}
        
        # Initialize repository if configured
        if self.repo_url and self.token:
            self._init_repository()
    
    async def publish_transcription(self, file_id: str, request: PublicationRequest) -> PublicationStatus:
        """Publish a transcription to GitHub Pages."""
        if not self._is_configured():
            raise Exception("GitHub publishing not configured")
        
        try:
            # Load transcription HTML
            html_content = await self._get_transcription_html(file_id)
            if not html_content:
                raise Exception("No HTML transcription found")
            
            # Generate publication metadata
            metadata = {
                'file_id': file_id,
                'title': request.title or f"Transcription {file_id}",
                'description': request.description or "",
                'tags': request.tags,
                'published_date': datetime.now().isoformat(),
                'original_request': request.dict()
            }
            
            # Write HTML file to repository
            html_filename = f"{file_id}.html"
            html_path = self.repo_dir / "transcriptions" / html_filename
            html_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Update metadata file
            await self._update_metadata(file_id, metadata)
            
            # Regenerate index
            await self._generate_index()
            
            # Commit and push changes
            commit_hash = await self._commit_and_push(f"Publish transcription: {metadata['title']}")
            
            # Create publication status
            publication_status = PublicationStatus(
                is_published=True,
                published_url=f"{self.base_url}/transcriptions/{html_filename}" if self.base_url else None,
                published_date=datetime.now(),
                github_commit_hash=commit_hash
            )
            
            self.published_files[file_id] = publication_status
            return publication_status
            
        except Exception as e:
            raise Exception(f"Failed to publish transcription: {str(e)}")
    
    async def unpublish_transcription(self, file_id: str) -> bool:
        """Remove a transcription from GitHub Pages."""
        if not self._is_configured():
            return False
        
        try:
            # Remove HTML file
            html_path = self.repo_dir / "transcriptions" / f"{file_id}.html"
            if html_path.exists():
                html_path.unlink()
            
            # Remove from metadata
            await self._remove_from_metadata(file_id)
            
            # Regenerate index
            await self._generate_index()
            
            # Commit and push changes
            await self._commit_and_push(f"Unpublish transcription: {file_id}")
            
            # Remove from tracking
            if file_id in self.published_files:
                del self.published_files[file_id]
            
            return True
            
        except Exception as e:
            print(f"❌ Error unpublishing transcription: {e}")
            return False
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall publication system status."""
        return {
            'configured': self._is_configured(),
            'repository_url': self.repo_url,
            'base_url': self.base_url,
            'branch': self.branch,
            'published_count': len(self.published_files),
            'repository_exists': self.repo_dir.exists() if self._is_configured() else False
        }
    
    async def get_file_publication_status(self, file_id: str) -> Optional[PublicationStatus]:
        """Get publication status for a specific file."""
        return self.published_files.get(file_id)
    
    async def list_published_transcriptions(self) -> List[Dict[str, Any]]:
        """List all published transcriptions."""
        try:
            metadata_file = self.repo_dir / "metadata.json"
            if not metadata_file.exists():
                return []
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return list(metadata.get('transcriptions', {}).values())
            
        except Exception:
            return []
    
    async def rebuild_index(self):
        """Rebuild the GitHub Pages index."""
        if not self._is_configured():
            raise Exception("GitHub publishing not configured")
        
        await self._generate_index()
        await self._commit_and_push("Rebuild index page")
    
    def _is_configured(self) -> bool:
        """Check if GitHub publishing is properly configured."""
        return bool(self.repo_url and self.token)
    
    def _init_repository(self):
        """Initialize or clone the GitHub repository."""
        try:
            if self.repo_dir.exists():
                # Try to pull latest changes
                repo = git.Repo(self.repo_dir)
                repo.remotes.origin.pull()
            else:
                # Clone repository
                auth_url = self.repo_url.replace('https://', f'https://{self.token}@')
                git.Repo.clone_from(auth_url, self.repo_dir, branch=self.branch)
            
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize GitHub repository: {e}")
    
    async def _get_transcription_html(self, file_id: str) -> Optional[str]:
        """Get HTML content for a transcription."""
        # Look for existing HTML files
        html_dir = self.settings.audio_directory / "transcriptions" / "html"
        
        for html_file in html_dir.glob("*.html"):
            # Check if this file matches the file_id
            # This is a simplified check - in practice, you'd want better mapping
            if file_id in html_file.name:
                with open(html_file, 'r', encoding='utf-8') as f:
                    return f.read()
        
        return None
    
    async def _update_metadata(self, file_id: str, metadata: Dict[str, Any]):
        """Update the metadata file with new transcription info."""
        metadata_file = self.repo_dir / "metadata.json"
        
        # Load existing metadata
        if metadata_file.exists():
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
        else:
            data = {'transcriptions': {}}
        
        # Add new transcription
        data['transcriptions'][file_id] = metadata
        
        # Save metadata
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    async def _remove_from_metadata(self, file_id: str):
        """Remove a transcription from metadata."""
        metadata_file = self.repo_dir / "metadata.json"
        
        if not metadata_file.exists():
            return
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if file_id in data.get('transcriptions', {}):
            del data['transcriptions'][file_id]
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    async def _generate_index(self):
        """Generate the main index.html page."""
        metadata_file = self.repo_dir / "metadata.json"
        
        if not metadata_file.exists():
            transcriptions = {}
        else:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                transcriptions = data.get('transcriptions', {})
        
        # Generate HTML index
        html_content = self._generate_index_html(transcriptions)
        
        index_path = self.repo_dir / "index.html"
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
    
    def _generate_index_html(self, transcriptions: Dict[str, Any]) -> str:
        """Generate HTML content for the index page."""
        html = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Audio Transcriptions</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header { text-align: center; margin-bottom: 40px; }
        .transcription-list { display: grid; gap: 20px; }
        .transcription-item { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .transcription-title { font-size: 1.2em; font-weight: bold; margin-bottom: 10px; }
        .transcription-meta { color: #666; font-size: 0.9em; margin-bottom: 10px; }
        .transcription-description { margin-bottom: 15px; }
        .transcription-link { color: #007bff; text-decoration: none; }
        .transcription-link:hover { text-decoration: underline; }
        .search-box { width: 100%; padding: 10px; margin-bottom: 20px; border: 1px solid #ddd; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Audio Transcriptions</h1>
        <p>Browse and search through our collection of transcribed audio content.</p>
    </div>
    
    <input type="text" class="search-box" placeholder="Search transcriptions..." id="searchBox" onkeyup="filterTranscriptions()">
    
    <div class="transcription-list" id="transcriptionList">
"""
        
        for file_id, metadata in transcriptions.items():
            html += f"""
        <div class="transcription-item" data-title="{metadata.get('title', '')}" data-description="{metadata.get('description', '')}">
            <div class="transcription-title">
                <a href="transcriptions/{file_id}.html" class="transcription-link">{metadata.get('title', f'Transcription {file_id}')}</a>
            </div>
            <div class="transcription-meta">
                Published: {metadata.get('published_date', 'Unknown')}
            </div>
            <div class="transcription-description">
                {metadata.get('description', 'No description available.')}
            </div>
        </div>
"""
        
        html += """
    </div>
    
    <script>
        function filterTranscriptions() {
            const searchTerm = document.getElementById('searchBox').value.toLowerCase();
            const items = document.querySelectorAll('.transcription-item');
            
            items.forEach(item => {
                const title = item.getAttribute('data-title').toLowerCase();
                const description = item.getAttribute('data-description').toLowerCase();
                
                if (title.includes(searchTerm) || description.includes(searchTerm)) {
                    item.style.display = 'block';
                } else {
                    item.style.display = 'none';
                }
            });
        }
    </script>
</body>
</html>"""
        
        return html
    
    async def _commit_and_push(self, message: str) -> str:
        """Commit changes and push to GitHub."""
        try:
            repo = git.Repo(self.repo_dir)
            
            # Add all changes
            repo.git.add('.')
            
            # Commit changes
            commit = repo.index.commit(message)
            
            # Push to remote
            repo.remotes.origin.push()
            
            return commit.hexsha
            
        except Exception as e:
            raise Exception(f"Failed to commit and push: {str(e)}")