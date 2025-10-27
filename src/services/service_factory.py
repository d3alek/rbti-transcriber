"""Factory for creating transcription service clients with glossary integration."""

from pathlib import Path
from typing import Optional, List, Dict, Any

from .transcription_client import TranscriptionClient
from .assemblyai_client import AssemblyAIClient
from .deepgram_client import DeepgramClient
from .openai_client import OpenAIClient
from ..utils.glossary_manager import GlossaryManager
from ..utils.exceptions import ConfigurationError, AuthenticationError


class TranscriptionServiceFactory:
    """Factory for creating and configuring transcription service clients."""
    
    SUPPORTED_SERVICES = ['assemblyai', 'deepgram', 'openai']
    
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.glossary_manager = GlossaryManager(
            warn_on_truncation=config_manager.get('glossary.warn_on_truncation', True)
        )
    
    def create_client(self, service: str, glossary_files: Optional[List[Path]] = None) -> TranscriptionClient:
        """Create a transcription client for the specified service."""
        service = service.lower()
        
        if service not in self.SUPPORTED_SERVICES:
            raise ConfigurationError(f"Unsupported service: {service}. Supported: {self.SUPPORTED_SERVICES}")
        
        # Get API key for the service
        api_key = self.config_manager.get_api_key(service)
        if not api_key:
            raise AuthenticationError(f"No API key found for {service}. Set {service.upper()}_API_KEY environment variable.")
        
        # Create the appropriate client
        if service == 'assemblyai':
            client = AssemblyAIClient(api_key)
        elif service == 'deepgram':
            client = DeepgramClient(api_key)
        elif service == 'openai':
            client = OpenAIClient(api_key)
        else:
            raise ConfigurationError(f"Service implementation not found: {service}")
        
        # Apply glossary if provided (skip for OpenAI as it doesn't support custom vocabulary)
        if glossary_files and service != 'openai':
            self._apply_glossary_to_client(client, service, glossary_files)
        
        return client
    
    def _apply_glossary_to_client(self, client: TranscriptionClient, service: str, glossary_files: List[Path]) -> None:
        """Apply custom glossary to the transcription client."""
        try:
            # Load glossary terms
            terms = self.glossary_manager.load_multiple_glossaries(glossary_files)
            
            if not terms:
                print("Warning: No valid glossary terms loaded")
                return
            
            # Get service-specific terms
            service_terms = self.glossary_manager.get_terms_for_service(service)
            
            # Apply to client
            client.apply_custom_vocabulary(service_terms)
            
            print(f"Applied {len(service_terms)} glossary terms to {service} client")
            
        except Exception as e:
            print(f"Warning: Failed to apply glossary to {service} client: {e}")
    
    def get_service_capabilities(self, service: str) -> Dict[str, Any]:
        """Get capabilities information for a service."""
        service = service.lower()
        
        if service not in self.SUPPORTED_SERVICES:
            raise ConfigurationError(f"Unknown service: {service}")
        
        # Get service configuration
        service_config = self.config_manager.get(f'services.{service}', {})
        
        return {
            'service': service,
            'api_base_url': service_config.get('api_base_url', 'Unknown'),
            'supports_custom_vocabulary': service_config.get('supports_custom_vocabulary', False),
            'supports_speaker_diarization': service_config.get('supports_speaker_diarization', False),
            'max_vocabulary_terms': 1000,  # Both services support up to 1000 terms
            'supported_languages': self._get_supported_languages(service)
        }
    
    def _get_supported_languages(self, service: str) -> List[str]:
        """Get supported languages for a service."""
        # Common languages supported by both services
        common_languages = [
            'en', 'en-US', 'en-GB', 'en-AU', 'en-CA',
            'es', 'es-ES', 'es-MX',
            'fr', 'fr-FR', 'fr-CA',
            'de', 'de-DE',
            'it', 'it-IT',
            'pt', 'pt-BR', 'pt-PT',
            'nl', 'nl-NL',
            'ja', 'ja-JP',
            'ko', 'ko-KR',
            'zh', 'zh-CN', 'zh-TW'
        ]
        
        if service == 'assemblyai':
            return common_languages
        elif service == 'deepgram':
            return common_languages + ['ru', 'ru-RU', 'ar', 'ar-SA']
        elif service == 'openai':
            return common_languages + ['ru', 'ru-RU', 'ar', 'ar-SA', 'hi', 'hi-IN']
        else:
            return ['en']
    
    def validate_service_configuration(self, service: str) -> Dict[str, Any]:
        """Validate that a service is properly configured."""
        validation_result = {
            'service': service,
            'is_configured': True,
            'errors': [],
            'warnings': []
        }
        
        service = service.lower()
        
        # Check if service is supported
        if service not in self.SUPPORTED_SERVICES:
            validation_result['is_configured'] = False
            validation_result['errors'].append(f"Unsupported service: {service}")
            return validation_result
        
        # Check API key
        api_key = self.config_manager.get_api_key(service)
        if not api_key:
            validation_result['is_configured'] = False
            validation_result['errors'].append(f"No API key found. Set {service.upper()}_API_KEY environment variable.")
        elif len(api_key) < 10:  # Basic length check
            validation_result['warnings'].append("API key seems too short - please verify it's correct")
        
        # Check service configuration
        service_config = self.config_manager.get(f'services.{service}')
        if not service_config:
            validation_result['warnings'].append(f"No configuration found for {service} in config file")
        
        return validation_result
    
    def create_default_glossary(self, output_path: Path) -> None:
        """Create a default RBTI glossary file."""
        self.glossary_manager.create_default_glossary_file(output_path)
    
    def get_glossary_stats(self) -> Dict[str, Any]:
        """Get statistics about the loaded glossary."""
        return self.glossary_manager.get_glossary_stats()