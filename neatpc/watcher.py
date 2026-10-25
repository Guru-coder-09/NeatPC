"""Real-Time Folder Watcher Daemon for NeatPC.

Continuously monitors designated directories (e.g. ~/Downloads or ~/Desktop)
using watchdog and automatically categorizes, smart-renames, and quarantines duplicates
the moment a new file finishes downloading.
"""

import time
import os
from pathlib import Path
from typing import Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent
from rich.console import Console

from .config import PROTECTED_FILENAMES, PROTECTED_EXTENSIONS
from .organizer import Organizer
from .classifier import Classifier
from .duplicates import DuplicateDetector
from .scanner import FileItem

console = Console(legacy_windows=False)


class AutoOrganizeEventHandler(FileSystemEventHandler):
    """Handles new file arrivals with debounce and auto-organization."""

    def __init__(self, target_dir: Path, classifier: Optional[Classifier] = None):
        super().__init__()
        self.target_dir = target_dir.resolve()
        self.classifier = classifier or Classifier()
        self.organizer = Organizer(self.target_dir)
        self.detector = DuplicateDetector()
        self.processing_paths: Set[str] = set()

    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_event(Path(event.src_path))

    def on_moved(self, event):
        # Triggered when browser finishes download (renames .crdownload -> final file)
        if not event.is_directory:
            self._handle_file_event(Path(event.dest_path))

    def _handle_file_event(self, path: Path):
        """Debounce and process newly arrived file."""
        if str(path) in self.processing_paths:
            return

        # Ensure file is in target root, not an internal subfolder
        if path.parent.resolve() != self.target_dir:
            return

        name_lower = path.name.lower()
        suffix_lower = path.suffix.lower()

        # Ignore protected or downloading temp files
        if name_lower in PROTECTED_FILENAMES or suffix_lower in PROTECTED_EXTENSIONS:
            return

        self.processing_paths.add(str(path))
        try:
            # Wait for browser write to finish (file size stabilization debounce)
            time.sleep(1.5)
            last_size = -1
            for _ in range(10):
                if not path.exists():
                    return
                current_size = path.stat().st_size
                if current_size == last_size and current_size > 0:
                    break
                last_size = current_size
                time.sleep(0.5)

            if not path.exists():
                return

            item = FileItem(path)
            category, reason = self.classifier.rule_based_classify(item)

            # Check duplicate against existing files in target
            dup_info = {}
            # Build mini-plan
            classifications = {str(item.path): (category, reason)}
            plan = self.organizer.build_plan([item], classifications, duplicate_info=dup_info)

            if plan:
                res = self.organizer.execute_plan(plan)
                if res["moved_count"] > 0:
                    dest = plan[0].destination.relative_to(self.target_dir)
                    console.print(
                        f"[bold green]⚡ Auto-Organized:[/bold green] [white]{path.name}[/white] "
                        f"➔ [cyan]📁 {dest}[/cyan] [dim]({reason})[/dim]"
                    )
        except Exception as e:
            console.print(f"[dim red]Watcher warning on {path.name}: {e}[/dim red]")
        finally:
            self.processing_paths.discard(str(path))


def start_watcher(target_dir: Path):
    """Starts the real-time background watcher daemon."""
    target = target_dir.resolve()
    console.print(f"\n[bold green]👁️ NeatPC Watcher Active:[/bold green] Monitoring [cyan]{target}[/cyan]")
    console.print("[dim]New downloads will be automatically organized in real-time. Press Ctrl+C to stop.[/dim]\n")

    handler = AutoOrganizeEventHandler(target)
    observer = Observer()
    observer.schedule(handler, str(target), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping watcher daemon...[/yellow]")
        observer.stop()
    observer.join()
    console.print("[green]Watcher stopped cleanly.[/green]\n")
