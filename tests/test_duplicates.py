"""Tests for duplicate detection, hash verification, and master copy selection."""

import pytest
from pathlib import Path
from neatpc.scanner import FileItem
from neatpc.duplicates import DuplicateDetector


def test_duplicate_exact_match(tmp_path: Path):
    file1 = tmp_path / "invoice.pdf"
    file2 = tmp_path / "invoice (1).pdf"
    file3 = tmp_path / "invoice_copy.pdf"
    file4 = tmp_path / "different.pdf"

    content = b"PDF-1.4 Identical Content For Deduplication Testing 123456"
    file1.write_bytes(content)
    file2.write_bytes(content)
    file3.write_bytes(content)
    file4.write_bytes(b"Different Content")

    items = [FileItem(p) for p in [file1, file2, file3, file4]]
    detector = DuplicateDetector()
    duplicates = detector.identify_duplicates(items)

    # file1 (cleanest name 'invoice.pdf') should be chosen as original
    # file2 and file3 should be detected as duplicates
    assert len(duplicates) == 2
    assert str(file2) in duplicates
    assert str(file3) in duplicates
    assert str(file1) not in duplicates
    assert str(file4) not in duplicates

    # Original match name should be 'invoice.pdf'
    assert duplicates[str(file2)]["original_name"] == "invoice.pdf"
    assert duplicates[str(file3)]["original_name"] == "invoice.pdf"


def test_no_duplicates_for_unique_files(tmp_path: Path):
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    file1.write_text("Hello World")
    file2.write_text("Foo Bar")

    items = [FileItem(p) for p in [file1, file2]]
    detector = DuplicateDetector()
    duplicates = detector.identify_duplicates(items)

    assert len(duplicates) == 0
