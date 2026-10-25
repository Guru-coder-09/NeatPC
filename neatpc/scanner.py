"""File scanner and text extractor for NeatPC."""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import pypdf
import docx

# Suppress noisy PDF parsing warnings
logging.getLogger("pypdf").setLevel(logging.ERROR)

from .config import PROTECTED_FILENAMES, PROTECTED_EXTENSIONS


class FileItem:
    """Represents a file or directory scanned for organization."""

    def __init__(self, path: Path):
        self.path = path.resolve()
        self.name = path.name
        self.stem = path.stem
        self.suffix = path.suffix.lower()
        self.is_dir = path.is_dir()
        self.is_shortcut = self.suffix in [".lnk", ".url"]
        self.size_bytes = 0
        self.modified_time = 0.0

        if not self.is_dir and path.exists():
            try:
                stat = path.stat()
                self.size_bytes = stat.st_size
                self.modified_time = stat.st_mtime
            except (OSError, PermissionError):
                pass

        self.text_preview: Optional[str] = None

    def is_protected(self) -> bool:
        """Check if file or folder is protected from movement."""
        lower_name = self.name.lower()
        if lower_name in PROTECTED_FILENAMES:
            return True
        if self.suffix in PROTECTED_EXTENSIONS:
            return True
        if lower_name.startswith("~$") or lower_name.startswith("."):
            return True
        return False

    def extract_preview(self, max_chars: int = 1200) -> str:
        """Extract text content snippet for AI semantic classification."""
        if self.text_preview is not None:
            return self.text_preview

        if self.is_dir or self.is_shortcut:
            self.text_preview = ""
            return ""

        snippet = ""
        try:
            if self.suffix == ".pdf":
                reader = pypdf.PdfReader(str(self.path))
                text_parts = []
                for page in reader.pages[:2]:
                    extracted = page.extract_text()
                    if extracted:
                        text_parts.append(extracted.strip())
                snippet = " ".join(text_parts)[:max_chars]

            elif self.suffix in [".docx", ".doc"]:
                doc = docx.Document(str(self.path))
                paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
                snippet = " ".join(paragraphs)[:max_chars]

            elif self.suffix in [".txt", ".md", ".csv", ".json", ".log", ".yaml", ".yml", ".py", ".html"]:
                with open(self.path, "r", encoding="utf-8", errors="ignore") as f:
                    snippet = f.read(max_chars)
        except Exception:
            # Fallback gracefully if file is locked or binary
            snippet = ""

        self.text_preview = snippet.strip()
        return self.text_preview


def scan_directory(
    target_dir: Path,
    include_shortcuts: bool = True,
    exclude_folder_names: Optional[List[str]] = None
) -> List[FileItem]:
    """
    Scans the given directory and returns eligible files and folders.
    Does not recurse deeply into subfolders to prevent moving internal project contents.
    """
    if not target_dir.exists() or not target_dir.is_dir():
        return []

    excluded = set(exclude_folder_names or [])
    # Add common destination folder names so we don't re-organize them
    excluded.update({
        "Documents", "Pictures", "Videos", "Audio", "Archives", "Installers", 
        "Code", "Shortcuts", "Projects", "Organized_Shortcuts"
    })

    items: List[FileItem] = []

    try:
        for entry in target_dir.iterdir():
            file_item = FileItem(entry)

            # Skip protected system files
            if file_item.is_protected():
                continue

            # If it's an excluded destination folder, skip
            if file_item.is_dir and file_item.name in excluded:
                continue

            # Skip shortcut if shortcuts disabled
            if file_item.is_shortcut and not include_shortcuts:
                continue

            items.append(file_item)
    except PermissionError:
        pass

    return items
