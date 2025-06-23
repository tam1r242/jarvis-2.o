import os
import json
from typing import Dict, Any

class ConfigManager:
    _instance = None
    _config = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._config is None:
            self.load_config()

    def load_config(self, config_path: str = "config/config.json") -> None:
        """Load configuration from file with validation."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
            
        try:
            with open(config_path, 'r') as f:
                self._config = json.load(f)
            self._validate_config()
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            raise Exception(f"Error loading config: {str(e)}")

    def _validate_config(self) -> None:
        """Validate required configuration fields."""
        required_sections = {
            'audio': ['sample_rate', 'channels', 'chunk_size', 'record_seconds'],
            'speech': ['wake_phrase', 'keyword_threshold'],
            'whisper': ['model', 'language'],
            'tts': ['voice', 'rate', 'volume'],
            'groq': ['api_key'],
            'web': ['host', 'port']
        }

        for section, fields in required_sections.items():
            if section not in self._config:
                raise ValueError(f"Missing required config section: {section}")
            
            for field in fields:
                if field not in self._config[section]:
                    raise ValueError(f"Missing required config field: {section}.{field}")

    def get(self, section: str = None) -> Dict[str, Any]:
        """Get configuration or specific section."""
        if section is None:
            return self._config
        if section not in self._config:
            raise KeyError(f"Config section not found: {section}")
        return self._config[section]

    def update(self, section: str, key: str, value: Any) -> None:
        """Update a configuration value."""
        if section not in self._config:
            raise KeyError(f"Config section not found: {section}")
        self._config[section][key] = value

# Global config instance
config = ConfigManager()
