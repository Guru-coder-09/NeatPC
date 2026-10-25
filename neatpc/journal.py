"""Transaction journal and audit history for NeatPC rollback / undo."""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from .config import HISTORY_DB_PATH


class Journal:
    """Manages recording and reading organization transaction history."""

    def __init__(self, db_path: Path = HISTORY_DB_PATH):
        self.db_path = db_path
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        if not self.db_path.exists():
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._write_data([])

    def _read_data(self) -> List[Dict[str, Any]]:
        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _write_data(self, data: List[Dict[str, Any]]) -> None:
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def record_session(
        self,
        session_id: str,
        target_dir: str,
        moves: List[Dict[str, str]],
        created_dirs: List[str]
    ) -> None:
        """Record a completed file organization session."""
        sessions = self._read_data()
        session_record = {
            "session_id": session_id,
            "timestamp": datetime.now().isoformat(),
            "target_dir": str(target_dir),
            "move_count": len(moves),
            "moves": moves,
            "created_dirs": created_dirs,
            "status": "completed"
        }
        sessions.append(session_record)
        self._write_data(sessions)

    def get_last_session(self) -> Optional[Dict[str, Any]]:
        """Return the most recent active session that can be undone."""
        sessions = self._read_data()
        for s in reversed(sessions):
            if s.get("status") == "completed":
                return s
        return None

    def mark_session_undone(self, session_id: str) -> None:
        """Mark a session as undone after rollback."""
        sessions = self._read_data()
        for s in sessions:
            if s.get("session_id") == session_id:
                s["status"] = "undone"
                s["undone_at"] = datetime.now().isoformat()
        self._write_data(sessions)

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all recorded sessions."""
        return self._read_data()
