"""Tests for plan generation, execution, and directory routing."""

import pytest
from pathlib import Path
from neatpc.scanner import FileItem
from neatpc.organizer import Organizer, OrganizationPlanItem
from neatpc.journal import Journal


def test_build_plan_and_execute(tmp_path: Path):
    source_dir = tmp_path / "incoming"
    source_dir.mkdir()

    f1 = source_dir / "statement.csv"
    f2 = source_dir / "recording.mp4"
    f1.write_text("date,amount\n2026-01-01,100")
    f2.write_bytes(b"\x00\x00\x00\x20ftypisom")

    items = [FileItem(f1), FileItem(f2)]
    classifications = {
        str(f1): ("Spreadsheets", "CSV data table"),
        str(f2): ("Media/Videos", "Video file")
    }

    journal = Journal(tmp_path / "test_history.json")
    organizer = Organizer(source_dir, journal=journal)
    plan = organizer.build_plan(items, classifications)

    assert len(plan) == 2
    assert plan[0].destination == source_dir / "Spreadsheets" / "statement.csv"
    assert plan[1].destination == source_dir / "Media" / "Videos" / "recording.mp4"

    # Execute plan
    res = organizer.execute_plan(plan)
    assert res["moved_count"] == 2
    assert len(res["errors"]) == 0

    # Verify files were moved
    assert not f1.exists()
    assert not f2.exists()
    assert (source_dir / "Spreadsheets" / "statement.csv").exists()
    assert (source_dir / "Media" / "Videos" / "recording.mp4").exists()


def test_execute_handles_nonexistent_source(tmp_path: Path):
    source_dir = tmp_path / "test"
    source_dir.mkdir()
    non_existent = source_dir / "ghost.txt"

    journal = Journal(tmp_path / "test_history.json")
    organizer = Organizer(source_dir, journal=journal)

    plan = [
        OrganizationPlanItem(
            source=non_existent,
            destination=source_dir / "Documents" / "ghost.txt",
            category="Documents",
            reason="Test"
        )
    ]

    res = organizer.execute_plan(plan)
    assert res["moved_count"] == 0
    assert len(res["errors"]) == 1
    assert "Source file does not exist" in res["errors"][0]["error"]
