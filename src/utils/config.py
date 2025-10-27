"""Configuration management with YAML support."""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigManager:
    """Manages application configuration with YAML support."""
    
    DEFAULT_CONFIG = {
        'transcription': {
            'default_service': 'assemblyai',
            'speaker_diarization': True,
            'max_speakers': 3,
            'confidence_threshold': 0.8
        },
        'services': {
            'assemblyai': {
                'api_base_url': 'https://api.assemblyai.com/v2',
                'supports_custom_vocabulary': True,
                'supports_speaker_diarization': True
            },
            'deepgram': {
                'api_base_url': 'https://api.deepgram.com/v1',
                'supports_custom_vocabulary': True,
                'supports_speaker_diarization': True
            }
        },
        'output': {
            'formats': ['html', 'markdown'],
            'timestamp_interval': 30,
            'speaker_colors': ['#2E86AB', '#A23B72', '#F18F01'],
            'cache_responses': True
        },
        'formatting': {
            'html': {
                'embed_css': True,
                'speaker_styling': True,
                'timestamp_links': True
            },
            'markdown': {
                'speaker_headers': True,
                'timestamp_blockquotes': True,
                'preserve_paragraphs': True
            }
        },
        'glossary': {
            'files': [],
            'max_terms': 1000,
            'warn_on_truncation': True
        }
    }
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path('config.yaml')
        self._config = self.DEFAULT_CONFIG.copy()
        
        # Load environment variables from .env file
        load_dotenv()
        
        self._load_config()
    
    def _load_config(self) -> None:
        """Load configuration from YAML file if it exists."""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        self._merge_config(self._config, user_config)
            except Exception as e:
                print(f"Warning: Could not load config from {self.config_path}: {e}")
    
    def _merge_config(self, base: Dict[str, Any], override: Dict[str, Any]) -> None:
        """Recursively merge override config into base config."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation (e.g., 'transcription.default_service')."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_api_key(self, service: str) -> Optional[str]:
        """Get API key for specified service from environment variables."""
        env_var = f"{service.upper()}_API_KEY"
        return os.getenv(env_var)
    
    def save_config(self) -> None:
        """Save current configuration to YAML file."""
        try:
            with open(self.config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False, indent=2)
        except Exception as e:
            print(f"Error saving config to {self.config_path}: {e}")
    
    def create_default_config(self) -> None:
        """Create default configuration file if it doesn't exist."""
        if not self.config_path.exists():
            self.save_config()
            print(f"Created default configuration at {self.config_path}")
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get the full configuration dictionary."""
        return self._config.copy()


# Backward compatibility function
def load_config(config_path: Optional[Path] = None) -> ConfigManager:
    """Load configuration and return ConfigManager instance.
    
    This function provides backward compatibility for existing code
    that expects a load_config function.
    """
    return ConfigManager(config_path)