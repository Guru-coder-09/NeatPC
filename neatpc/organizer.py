"""Execution and Rollback Engine for NeatPC with Smart Renaming and Duplicate Isolation."""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .scanner import FileItem
from .journal import Journal
from .duplicates import DuplicateDetector
from .renamer import SmartRenamer, is_cryptic_or_unnamed


class OrganizationPlanItem:
    """Represents a planned move operation with renaming and duplicate detection."""

    def __init__(
        self,
        source: Path,
        destination: Path,
        category: str,
        reason: str,
        is_collision: bool = False,
        is_duplicate: bool = False,
        original_file_match: Optional[str] = None,
        is_renamed: bool = False,
        original_name: Optional[str] = None,
        new_name: Optional[str] = None
    ):
        self.source = Path(source)
        self.destination = Path(destination)
        self.category = category
        self.reason = reason
        self.is_collision = is_collision
        self.is_duplicate = is_duplicate
        self.original_file_match = original_file_match
        self.is_renamed = is_renamed
        self.original_name = original_name or self.source.name
        self.new_name = new_name or self.destination.name


def get_collision_free_path(dest_folder: Path, filename: str) -> tuple[Path, bool]:
    """
    Ensure the target path does not overwrite any existing file.
    If 'report.pdf' exists, generates 'report (1).pdf', etc.
    Returns: (safe_path, had_collision)
    """
    dest_folder = Path(dest_folder)
    target = dest_folder / filename
    if not target.exists():
        return target, False

    stem = Path(filename).stem
    suffix = Path(filename).suffix
    counter = 1

    while True:
        candidate_name = f"{stem} ({counter}){suffix}"
        candidate_path = dest_folder / candidate_name
        if not candidate_path.exists():
            return candidate_path, True
        counter += 1


class Organizer:
    """Plans, executes, and rolls back file organization."""

    def __init__(self, target_dir: Path, journal: Optional[Journal] = None):
        self.target_dir = Path(target_dir).resolve()
        self.journal = journal or Journal()

    def build_plan(
        self,
        items: List[FileItem],
        classifications: Dict[str, tuple[str, str]],
        duplicate_info: Optional[Dict[str, Dict[str, Any]]] = None,
        rename_map: Optional[Dict[str, str]] = None,
        custom_base_dest: Optional[Path] = None
    ) -> List[OrganizationPlanItem]:
        """
        Builds a dry-run execution plan with duplicate isolation and smart renaming.
        """
        plan: List[OrganizationPlanItem] = []
        base_dest = custom_base_dest or self.target_dir
        dup_map = duplicate_info or {}
        renames = rename_map or {}

        for item in items:
            item_path_str = str(item.path)
            is_dup = item_path_str in dup_map
            orig_match = None

            if is_dup:
                dup_entry = dup_map[item_path_str]
                orig_match = dup_entry.get("original_name")
                category = "_Duplicates"
                reason = f"Duplicate copy of: {orig_match}"
                filename_to_use = item.name
                is_renamed = False
            else:
                cat_tuple = classifications.get(item_path_str)
                if not cat_tuple:
                    continue
                category, reason = cat_tuple

                # Check if file has a smart clean name
                if item_path_str in renames:
                    filename_to_use = renames[item_path_str]
                    is_renamed = filename_to_use != item.name
                    if is_renamed:
                        reason = f"Smart AI renamed: {filename_to_use}"
                else:
                    filename_to_use = item.name
                    is_renamed = False

            dest_dir = base_dest / category
            safe_dest_path, had_collision = get_collision_free_path(dest_dir, filename_to_use)

            # Skip if file is already at destination with the same name
            if item.path.resolve() == safe_dest_path.resolve():
                continue

            plan.append(OrganizationPlanItem(
                source=item.path,
                destination=safe_dest_path,
                category=category,
                reason=reason,
                is_collision=had_collision,
                is_duplicate=is_dup,
                original_file_match=orig_match,
                is_renamed=is_renamed,
                original_name=item.name,
                new_name=safe_dest_path.name
            ))

        return plan

    def execute_plan(
        self,
        plan: List[OrganizationPlanItem]
    ) -> Dict[str, Any]:
        """
        Safely executes the plan with transactional audit logging.
        If an individual move fails, previous moves remain recorded in the journal.
        """
        session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        moves_logged: List[Dict[str, Any]] = []
        created_dirs: set[str] = set()
        errors: List[Dict[str, str]] = []

        for item in plan:
            if not item.source.exists():
                errors.append({
                    "file": item.source.name,
                    "error": f"Source file does not exist: {item.source}"
                })
                continue

            dest_folder = item.destination.parent
            if not dest_folder.exists():
                try:
                    dest_folder.mkdir(parents=True, exist_ok=True)
                    created_dirs.add(str(dest_folder))
                except Exception as e:
                    errors.append({
                        "file": item.source.name,
                        "error": f"Failed to create folder {dest_folder}: {e}"
                    })
                    continue

            try:
                shutil.move(str(item.source), str(item.destination))
                moves_logged.append({
                    "source": str(item.source),
                    "destination": str(item.destination),
                    "original_name": item.original_name,
                    "new_name": item.new_name,
                    "category": item.category,
                    "is_duplicate": item.is_duplicate,
                    "is_renamed": item.is_renamed
                })
            except Exception as e:
                errors.append({"file": item.source.name, "error": str(e)})

        # Log session to journal even if partially executed
        if moves_logged:
            self.journal.record_session(
                session_id=session_id,
                target_dir=str(self.target_dir),
                moves=moves_logged,
                created_dirs=list(created_dirs)
            )

        return {
            "session_id": session_id,
            "moved_count": len(moves_logged),
            "errors": errors
        }

    def rollback_session(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Rollback moves from the last or specified session.
        Restores files to exact original locations with original names.
        Handles missing files, name collisions on restoration, and removes created empty folders.
        """
        if session_id:
            session = self.journal.get_session(session_id)
        else:
            session = self.journal.get_last_session()

        if not session:
            return {
                "success": False,
                "message": "No active session available to undo.",
                "restored_count": 0,
                "failed_count": 0,
                "restored_items": [],
                "failed_items": []
            }

        sid = session["session_id"]
        moves = session.get("moves", [])
        restored_items: List[Dict[str, str]] = []
        failed_items: List[Dict[str, str]] = []

        # Reverse moves: from destination back to original source path
        for move in reversed(moves):
            src = Path(move["source"])
            dest = Path(move["destination"])

            if not dest.exists():
                failed_items.append({
                    "destination": str(dest),
                    "target_source": str(src),
                    "reason": "Destination file no longer exists (deleted or moved externally)"
                })
                continue

            try:
                src.parent.mkdir(parents=True, exist_ok=True)
                # Check if target source path is already occupied
                if src.exists() and src.resolve() != dest.resolve():
                    # Avoid overwrite; generate collision-free restored path
                    safe_restore_path, _ = get_collision_free_path(src.parent, src.name)
                    shutil.move(str(dest), str(safe_restore_path))
                    restored_items.append({
                        "from": str(dest),
                        "to": str(safe_restore_path),
                        "note": "Restored with safe suffix because original path was occupied"
                    })
                else:
                    shutil.move(str(dest), str(src))
                    restored_items.append({
                        "from": str(dest),
                        "to": str(src),
                        "note": "Restored cleanly"
                    })
            except Exception as e:
                failed_items.append({
                    "destination": str(dest),
                    "target_source": str(src),
                    "reason": f"Permission or OS error: {e}"
                })

        # Clean up empty directories that were created during the session
        created_dirs = session.get("created_dirs", [])
        cleaned_dirs = 0
        for d_str in sorted(created_dirs, key=len, reverse=True):
            d_path = Path(d_str)
            if d_path.exists() and d_path.is_dir():
                try:
                    if not any(d_path.iterdir()):
                        d_path.rmdir()
                        cleaned_dirs += 1
                except OSError:
                    pass

        self.journal.mark_session_undone(sid)

        return {
            "success": True,
            "session_id": sid,
            "restored_count": len(restored_items),
            "failed_count": len(failed_items),
            "restored_items": restored_items,
            "failed_items": failed_items,
            "cleaned_dirs": cleaned_dirs
        }
