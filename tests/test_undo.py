"""Tests for transactional rollback / undo and journal validation."""

import pytest
from pathlib import Path
from neatpc.scanner import FileItem
from neatpc.organizer import Organizer, OrganizationPlanItem
from neatpc.journal import Journal


def test_full_reversible_undo(tmp_path: Path):
    source_dir = tmp_path / "workspace"
    source_dir.mkdir()

    f1 = source_dir / "notes.txt"
    f2 = source_dir / "data.csv"
    f1.write_text("Hello text")
    f2.write_text("id,val\n1,2")

    items = [FileItem(f1), FileItem(f2)]
    classifications = {
        str(f1): ("Documents/General", "Text document"),
        str(f2): ("Spreadsheets", "CSV table")
    }

    journal = Journal(tmp_path / "journal.json")
    organizer = Organizer(source_dir, journal=journal)

    # 1. Plan & Execute
    plan = organizer.build_plan(items, classifications)
    organizer.execute_plan(plan)

    # Files should be moved
    assert not f1.exists()
    assert not f2.exists()
    dest1 = source_dir / "Documents" / "General" / "notes.txt"
    dest2 = source_dir / "Spreadsheets" / "data.csv"
    assert dest1.exists()
    assert dest2.exists()

    # 2. Rollback
    rollback_res = organizer.rollback_session()
    assert rollback_res["success"] is True
    assert rollback_res["restored_count"] == 2
    assert rollback_res["failed_count"] == 0

    # Files should be back in original locations
    assert f1.exists()
    assert f2.exists()
    assert f1.read_text() == "Hello text"
    assert f2.read_text() == "id,val\n1,2"

    # Destination directories should be cleaned up
    assert not dest1.parent.exists()
    assert not dest2.parent.exists()


def test_undo_with_occupied_source_path(tmp_path: Path):
    """If original path was re-occupied before undo, restore with safe suffix without overwriting."""
    source_dir = tmp_path / "workspace"
    source_dir.mkdir()

    orig_file = source_dir / "report.pdf"
    orig_file.write_text("Original PDF content")

    journal = Journal(tmp_path / "journal.json")
    organizer = Organizer(source_dir, journal=journal)

    plan = organizer.build_plan(
        [FileItem(orig_file)],
        {str(orig_file): ("Documents", "PDF doc")}
    )
    organizer.execute_plan(plan)

    # Re-create a NEW file at the original path
    orig_file.write_text("Brand new file created while organized")

    # Perform rollback
    rollback_res = organizer.rollback_session()
    assert rollback_res["success"] is True
    assert rollback_res["restored_count"] == 1

    # Both files must exist! Original must NOT be overwritten!
    assert orig_file.read_text() == "Brand new file created while organized"
    restored_collision_file = source_dir / "report (1).pdf"
    assert restored_collision_file.exists()
    assert restored_collision_file.read_text() == "Original PDF content"


def test_undo_with_missing_destination_file(tmp_path: Path):
    """If organized file was deleted externally after run, undo reports it gracefully."""
    source_dir = tmp_path / "workspace"
    source_dir.mkdir()

    f1 = source_dir / "test.txt"
    f1.write_text("Temp")

    journal = Journal(tmp_path / "journal.json")
    organizer = Organizer(source_dir, journal=journal)

    plan = organizer.build_plan([FileItem(f1)], {str(f1): ("Documents", "Text")})
    organizer.execute_plan(plan)

    dest_file = source_dir / "Documents" / "test.txt"
    dest_file.unlink()  # User deletes it externally

    rollback_res = organizer.rollback_session()
    assert rollback_res["success"] is True
    assert rollback_res["restored_count"] == 0
    assert rollback_res["failed_count"] == 1
    assert len(rollback_res["failed_items"]) == 1
    assert "no longer exists" in rollback_res["failed_items"][0]["reason"]
