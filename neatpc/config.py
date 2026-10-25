"""Configuration, YAML loader, and constants for NeatPC file organizer."""

import os
from pathlib import Path
from typing import Dict, Any, List
import yaml

# Base User Directories
USER_HOME = Path.home()
DOWNLOADS_DIR = USER_HOME / "Downloads"

# Detect Desktop (OneDrive Synced Desktop or Local Desktop)
ONEDRIVE_DESKTOP = USER_HOME / "OneDrive" / "Desktop"
LOCAL_DESKTOP = USER_HOME / "Desktop"
DESKTOP_DIR = ONEDRIVE_DESKTOP if ONEDRIVE_DESKTOP.exists() else LOCAL_DESKTOP

# App Data Directory for NeatPC
APP_DATA_DIR = USER_HOME / ".neatpc"
APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
HISTORY_DB_PATH = APP_DATA_DIR / "history.json"
CONFIG_FILE_PATH = APP_DATA_DIR / "config.json"
CONFIG_YAML_PATH = APP_DATA_DIR / "config.yaml"

# Default Model & Endpoints
DEFAULT_GEMINI_MODEL = "gemini-3.8-flash"
DEFAULT_OLLAMA_ENDPOINT = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "llama3.2"

# Protected Files & Folders that should NEVER be moved
PROTECTED_FILENAMES = {
    "desktop.ini",
    "thumbs.db",
    ".ds_store",
    "ntuser.dat",
    "ntuser.ini",
    ".neatpc",
    ".git",
    "recycle.bin",
    "$recycle.bin",
    "system volume information",
    "_ORGANIZATION_AUDIT_LOG.md",
    "_DOWNLOADS_ORGANIZATION_PLAN.json",
    "_DOWNLOADS_ORGANIZATION_LOG.md"
}

PROTECTED_EXTENSIONS = {
    ".sys",
    ".dll",
    ".tmp",
    ".crdownload",
    ".part",
    ".swp"
}

# Rule-Based Extension Mappings
DEFAULT_EXTENSION_MAPPINGS = {
    # Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".txt": "Documents/Text",
    ".md": "Documents/Notes",
    ".rtf": "Documents",
    ".epub": "Documents/Ebooks",
    
    # Spreadsheets & Data
    ".xlsx": "Spreadsheets",
    ".xls": "Spreadsheets",
    ".csv": "Spreadsheets",
    ".json": "Code & Data",
    ".xml": "Code & Data",
    
    # Presentations
    ".pptx": "Presentations",
    ".ppt": "Presentations",
    ".key": "Presentations",

    # Media - Images
    ".png": "Media/Images",
    ".jpg": "Media/Images",
    ".jpeg": "Media/Images",
    ".webp": "Media/Images",
    ".gif": "Media/Images",
    ".svg": "Media/Images",
    ".bmp": "Media/Images",

    # Media - Videos
    ".mp4": "Media/Videos",
    ".mkv": "Media/Videos",
    ".avi": "Media/Videos",
    ".mov": "Media/Videos",
    ".wmv": "Media/Videos",
    ".webm": "Media/Videos",

    # Media - Audio
    ".mp3": "Media/Audio",
    ".wav": "Media/Audio",
    ".flac": "Media/Audio",
    ".aac": "Media/Audio",
    ".m4a": "Media/Audio",

    # Archives
    ".zip": "Archives",
    ".rar": "Archives",
    ".7z": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".bz2": "Archives",

    # Installers & Executables
    ".exe": "Installers",
    ".msi": "Installers",
    ".dmg": "Installers",
    ".iso": "Installers",

    # Code & Development
    ".py": "Code/Python",
    ".js": "Code/JavaScript",
    ".ts": "Code/TypeScript",
    ".html": "Code/Web",
    ".css": "Code/Web",
    ".cpp": "Code/C++",
    ".c": "Code/C",
    ".rs": "Code/Rust",
    ".go": "Code/Go",
    ".java": "Code/Java",
    ".ipynb": "Code/Notebooks",
}

# Desktop Application Shortcut (.lnk) Categorization Rules
SHORTCUT_CATEGORIES = {
    "Development & Tools": [
        "code", "visual studio", "antigravity", "git", "github", "terminal", 
        "pycharm", "intellij", "sublime", "cursor", "docker", "postman",
        "android studio", "dbeaver", "powershell", "cmd"
    ],
    "Browsers & Web": [
        "chrome", "google chrome", "edge", "firefox", "brave", "opera", "tor", "vivaldi", "safari"
    ],
    "Creative & Media": [
        "capcut", "davinci", "premiere", "photoshop", "illustrator", "after effects", 
        "audacity", "obs", "blender", "vlc", "spotify", "gimp", "canva"
    ],
    "Meetings & Communication": [
        "webex", "zoom", "teams", "slack", "discord", "whatsapp", "telegram", "skype", "outlook"
    ],
    "AI & Productivity": [
        "gemini", "chatgpt", "claude", "wispr flow", "flow", "notion", "obsidian", 
        "evernote", "onenote", "word", "excel", "powerpoint", "calculator"
    ],
    "Gaming": [
        "steam", "epic games", "riot client", "valorant", "battle.net", "minecraft", "roblox", "gog galaxy", "ea"
    ],
    "Utilities": [
        "gapplauncher", "settings", "task manager", "cleaner", "powertoys", "filezilla", "anydesk", "teamviewer"
    ]
}


def get_default_config_yaml() -> str:
    """Returns sample YAML configuration with helpful documentation."""
    return """# NeatPC Configuration File
# Location: ~/.neatpc/config.yaml

# AI Provider: 'auto', 'gemini', 'ollama', or 'none'
# - auto: Prefers Gemini if GEMINI_API_KEY is set, else tests local Ollama, else offline
# - gemini: Use Google Gemini Cloud API
# - ollama: Use local Ollama instance (100% private, no API key needed)
# - none: Fast rule-based heuristics only
ai_provider: auto

# Google Gemini Settings
gemini:
  model: "gemini-3.8-flash"
  api_key: ""  # Leave empty to read from $GEMINI_API_KEY environment variable

# Local Ollama Settings (run 'ollama serve' and 'ollama pull llama3.2')
ollama:
  endpoint: "http://localhost:11434"
  model: "llama3.2"

# Photo & Video EXIF Sorting
# When enabled, photos are organized into Media/Pictures/YYYY/MM based on capture date
exif_photo_sorting: true

# Custom File Extension Overrides
custom_extensions:
  .torrent: "Downloads/Torrents"
  .blend: "3D Models/Blender"
  .fig: "Design/Figma"

# Custom Keyword Rules
custom_rules:
  - keyword: "tax"
    destination: "Documents/Finance/Tax"
  - keyword: "receipt"
    destination: "Documents/Finance/Receipts"
"""


def load_user_config() -> Dict[str, Any]:
    """Loads user configuration from ~/.neatpc/config.yaml, creating template if missing."""
    if not CONFIG_YAML_PATH.exists():
        try:
            CONFIG_YAML_PATH.write_text(get_default_config_yaml(), encoding="utf-8")
        except Exception:
            pass
        return {}

    try:
        data = yaml.safe_load(CONFIG_YAML_PATH.read_text(encoding="utf-8"))
        return data or {}
    except Exception:
        return {}


# Load active configuration
USER_CONFIG = load_user_config()
EXTENSION_MAPPINGS = {**DEFAULT_EXTENSION_MAPPINGS, **USER_CONFIG.get("custom_extensions", {})}
