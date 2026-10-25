"""Tests for CLI arguments, simulation mode (--sim), and auto-confirmation flags."""

import pytest
from pathlib import Path
from neatpc.cli import run_find_duplicates, run_smart_renamer_station, run_shortcuts_only
from neatpc.scanner import FileItem


def test_duplicates_simulation_mode_does_not_move_files(tmp_path: Path):
    file1 = tmp_path / "copy1.txt"
    file2 = tmp_path / "copy2.txt"
    file1.write_text("Identical Content")
    file2.write_text("Identical Content")

    # Run in simulation mode
    run_find_duplicates(tmp_path, dry_run=True)

    # In dry_run, neither file should be moved to _Duplicates
    assert file1.exists()
    assert file2.exists()
    assert not (tmp_path / "_Duplicates").exists()


def test_smart_renamer_simulation_mode_does_not_rename_files(tmp_path: Path):
    cryptic = tmp_path / "IMG_20261025_001.pdf"
    cryptic.write_text("Annual Financial Report and Balance Sheet 2026")

    # Run in simulation mode
    run_smart_renamer_station(tmp_path, use_ai=False, dry_run=True)

    # In dry_run, original filename must still exist
    assert cryptic.exists()


def test_shortcuts_simulation_mode_does_not_move_shortcuts(tmp_path: Path):
    shortcut = tmp_path / "VSCode.lnk"
    shortcut.write_bytes(b"dummy shortcut content")

    # Run in simulation mode
    run_shortcuts_only(tmp_path, dry_run=True)

    # In dry_run, shortcut must remain untouched on Desktop root
    assert shortcut.exists()
    assert not (tmp_path / "Shortcuts").exists()
