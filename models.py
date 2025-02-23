from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum
import json
from datetime import datetime

class SuggestionType(Enum):
    """Types of code suggestions that can be generated."""
    COMPLETION = "completion"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    SECURITY = "security"
    OPTIMIZATION = "optimization"

class ModelType(Enum):
    """Available AI models for code generation."""
    OPENAI = "openai"
    TRANSFORMER = "transformer"
    COMBINED = "combined"

@dataclass
class CodeContext:
    """Represents the context in which code is being written."""
    text: str
    language: Optional[str] = None
    file_type: Optional[str] = None
    line_number: Optional[int] = None
    surrounding_code: Optional[str] = None
    project_type: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert the context to a dictionary."""
        return {
            "text": self.text,
            "language": self.language,
            "file_type": self.file_type,
            "line_number": self.line_number,
            "surrounding_code": self.surrounding_code,
            "project_type": self.project_type
        }

@dataclass
class Suggestion:
    """Represents a code suggestion."""
    content: str
    type: SuggestionType
    model: ModelType
    confidence: float
    timestamp: datetime = datetime.now()
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert the suggestion to a dictionary."""
        return {
            "content": self.content,
            "type": self.type.value,
            "model": self.model.value,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata or {}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Suggestion':
        """Create a Suggestion instance from a dictionary."""
        return cls(
            content=data["content"],
            type=SuggestionType(data["type"]),
            model=ModelType(data["model"]),
            confidence=data["confidence"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            metadata=data.get("metadata", {})
        )

@dataclass
class SuggestionHistory:
    """Maintains a history of code suggestions."""
    suggestions: List[Suggestion] = None

    def __post_init__(self):
        self.suggestions = self.suggestions or []

    def add_suggestion(self, suggestion: Suggestion):
        """Add a suggestion to the history."""
        self.suggestions.append(suggestion)

    def get_recent_suggestions(self, limit: int = 10) -> List[Suggestion]:
        """Get the most recent suggestions."""
        return sorted(
            self.suggestions,
            key=lambda x: x.timestamp,
            reverse=True
        )[:limit]

    def save_to_file(self, filepath: str):
        """Save suggestion history to a file."""
        data = {
            "suggestions": [s.to_dict() for s in self.suggestions]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=4)

    @classmethod
    def load_from_file(cls, filepath: str) -> 'SuggestionHistory':
        """Load suggestion history from a file."""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        suggestions = [
            Suggestion.from_dict(s_data)
            for s_data in data["suggestions"]
        ]
        return cls(suggestions=suggestions)

@dataclass
class EditorState:
    """Represents the current state of the editor."""
    cursor_position: tuple[int, int]
    selected_text: Optional[str]
    current_file: Optional[str]
    language: Optional[str]
    is_active: bool = True

    def update_position(self, x: int, y: int):
        """Update the cursor position."""
        self.cursor_position = (x, y)

    def update_selection(self, text: str):
        """Update the selected text."""
        self.selected_text = text

class Settings:
    """Manages application settings."""
    def __init__(self, config_path: str):
        self.config_path = config_path
        self.settings: Dict[str, Any] = self.load_settings()

    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return self.get_default_settings()

    def save_settings(self):
        """Save current settings to file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def get_default_settings(self) -> Dict[str, Any]:
        """Get default settings."""
        return {
            "hotkeys": {
                "toggle": "ctrl+shift+s",
                "generate": "ctrl+space",
                "accept": "ctrl+enter"
            },
            "editor_settings": {
                "indent_size": 4,
                "use_spaces": True
            },
            "suggestion_settings": {
                "max_length": 100,
                "temperature": 0.7,
                "top_p": 0.9
            },
            "ui_settings": {
                "theme": "dark",
                "font_size": 12,
                "suggestion_window_width": 600,
                "suggestion_window_height": 400
            }
        }

    def update_setting(self, key: str, value: Any):
        """Update a specific setting."""
        keys = key.split('.')
        current = self.settings
        for k in keys[:-1]:
            current = current.setdefault(k, {})
        current[keys[-1]] = value
        self.save_settings()