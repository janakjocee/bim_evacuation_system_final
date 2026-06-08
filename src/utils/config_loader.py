"""
Configuration loader with YAML validation.
"""
import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class ConfigLoader:
    """Load and validate configuration from YAML files."""
    
    def __init__(self, config_path: str = None):
        """Initialize config loader."""
        self.config_path = config_path or self._find_config_file()
        self._config: Dict[str, Any] = {}
        self._load()
    
    def _find_config_file(self) -> str:
        """Find configuration file."""
        # Get the project root (directory containing src/)
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent
        
        possible_paths = [
            str(project_root / "config" / "settings.yaml"),
            "config/settings.yaml",
            "./config/settings.yaml",
            "../config/settings.yaml",
            "../../config/settings.yaml",
        ]
        
        for path in possible_paths:
            if Path(path).exists():
                return path
        
        raise FileNotFoundError(f"Could not find settings.yaml. Searched: {possible_paths}")
    
    def _load(self) -> None:
        """Load YAML configuration with error handling."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            if self._config is None:
                raise ValueError("Configuration file is empty")
                
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML syntax in {self.config_path}: {e}")
        except Exception as e:
            raise ValueError(f"Error loading configuration: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    @property
    def config(self) -> Dict[str, Any]:
        """Get full configuration dictionary."""
        return self._config


# Global config instance
_config_instance: Optional[ConfigLoader] = None


def get_config(config_path: str = None) -> ConfigLoader:
    """Get or create global config instance."""
    global _config_instance
    if _config_instance is None or config_path is not None:
        _config_instance = ConfigLoader(config_path)
    return _config_instance
