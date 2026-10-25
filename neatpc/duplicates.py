"""Duplicate file detector using multi-stage size and SHA-256 content hashing."""

import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional, Any

from .scanner import FileItem


def get_partial_hash(filepath: Path, num_bytes: int = 65536) -> str:
    """Hash the first 64KB of a file for fast candidate pruning."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(num_bytes)
            hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return ""


def get_full_hash(filepath: Path) -> str:
    """Compute complete SHA-256 content hash."""
    hasher = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(131072), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (OSError, PermissionError):
        return ""


class DuplicateDetector:
    """Detects exact duplicate files and copy variants in scanned items."""

    def __init__(self):
        pass

    def identify_duplicates(self, items: List[FileItem]) -> Dict[str, Dict[str, Any]]:
        """
        Scans FileItems and detects exact binary duplicates.
        Returns mapping:
          { str(item.path): { "is_duplicate": bool, "original_path": Path, "hash": str } }
        """
        results: Dict[str, Dict[str, Any]] = {}

        # Exclude directories and shortcuts from duplicate hash checks
        eligible_items = [
            it for it in items 
            if not it.is_dir and not it.is_shortcut and it.size_bytes > 0
        ]

        # Stage 1: Group by file size
        size_map: Dict[int, List[FileItem]] = {}
        for it in eligible_items:
            size_map.setdefault(it.size_bytes, []).append(it)

        # Candidates that share identical file size
        size_candidates = [group for group in size_map.values() if len(group) > 1]

        # Stage 2: Group by partial hash
        partial_map: Dict[str, List[FileItem]] = {}
        for group in size_candidates:
            for it in group:
                p_hash = get_partial_hash(it.path)
                if p_hash:
                    partial_map.setdefault(p_hash, []).append(it)

        hash_candidates = [group for group in partial_map.values() if len(group) > 1]

        # Stage 3: Full SHA-256 comparison
        full_map: Dict[str, List[FileItem]] = {}
        for group in hash_candidates:
            for it in group:
                f_hash = get_full_hash(it.path)
                if f_hash:
                    full_map.setdefault(f_hash, []).append(it)

        # Classify originals vs duplicates
        for f_hash, duplicates in full_map.items():
            if len(duplicates) <= 1:
                continue

            # Sort duplicates so the cleanest/earliest filename is chosen as original
            # Criteria: shorter name, doesn't contain ' (1)' or ' - Copy', older modified date
            def sort_key(it: FileItem):
                has_copy_pattern = " (1)" in it.name or "- copy" in it.name.lower() or "copy" in it.name.lower()
                return (has_copy_pattern, len(it.name), it.modified_time)

            sorted_group = sorted(duplicates, key=sort_key)
            original = sorted_group[0]

            for dup in sorted_group[1:]:
                results[str(dup.path)] = {
                    "is_duplicate": True,
                    "original_path": original.path,
                    "original_name": original.name,
                    "hash": f_hash[:12]
                }

        return results
