"""Tests for collision-free path generation."""

import pytest
from pathlib import Path
from neatpc.organizer import get_collision_free_path


def test_collision_free_path_no_conflict(tmp_path: Path):
    target, had_collision = get_collision_free_path(tmp_path, "document.pdf")
    assert target == tmp_path / "document.pdf"
    assert had_collision is False


def test_collision_free_path_single_conflict(tmp_path: Path):
    existing = tmp_path / "document.pdf"
    existing.write_text("existing content")

    target, had_collision = get_collision_free_path(tmp_path, "document.pdf")
    assert target == tmp_path / "document (1).pdf"
    assert had_collision is True


def test_collision_free_path_multiple_conflicts(tmp_path: Path):
    (tmp_path / "report.docx").write_text("base")
    (tmp_path / "report (1).docx").write_text("first copy")
    (tmp_path / "report (2).docx").write_text("second copy")

    target, had_collision = get_collision_free_path(tmp_path, "report.docx")
    assert target == tmp_path / "report (3).docx"
    assert had_collision is True
