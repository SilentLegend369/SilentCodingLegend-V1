
import os
from pathlib import Path
import json
from typing import Optional

class APIConfig:
    def __init__(self, config_dir: str = "~/.silent_coding"):
        self.config_dir = os.path.expanduser(config_dir)
        self.config_file = os.path.join(self.config_dir, "api_config.json")
        self.ensure_config_dir()

    def ensure_config_dir(self):
        """Create configuration directory if it doesn't exist."""
        Path(self.config_dir).mkdir(parents=True, exist_ok=True)

    def save_api_key(self, api_key: str):
        """Safely save API key to configuration file."""
        config_data = {
            "openai_api_key": api_key
        }
        
        # Set restrictive file permissions (only owner can read/write)
        os.umask(0o077)
        
        with open(self.config_file, 'w') as f:
            json.dump(config_data, f, indent=4)

    def get_api_key(self) -> Optional[str]:
        """Retrieve API key from configuration file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
                return config_data.get("openai_api_key")
        except FileNotFoundError:
            return None

    def remove_api_key(self):
        """Remove API key from configuration."""
        if os.path.exists(self.config_file):
            os.remove(self.config_file)