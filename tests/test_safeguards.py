"""Tests for privacy safeguards and heuristic categorization."""

import pytest
from pathlib import Path
from neatpc.scanner import FileItem
from neatpc.classifier import Classifier, is_sensitive_file


def test_sensitive_file_detection(tmp_path: Path):
    safe_file = tmp_path / "meeting_notes.docx"
    safe_file.write_text("Team updates")

    password_file = tmp_path / "my_passwords.txt"
    password_file.write_text("secret logins")

    tax_file = tmp_path / "tax_return_2025.pdf"
    tax_file.write_text("W2 form")

    assert is_sensitive_file(FileItem(safe_file)) is False
    assert is_sensitive_file(FileItem(password_file)) is True
    assert is_sensitive_file(FileItem(tax_file)) is True


def test_rule_based_categorization(tmp_path: Path):
    classifier = Classifier(use_ai=False)

    py_file = tmp_path / "script.py"
    py_file.write_text("print('hello')")
    cat, _ = classifier.rule_based_classify(FileItem(py_file))
    assert cat.startswith("Projects & Code")

    zip_file = tmp_path / "archive.zip"
    zip_file.write_bytes(b"PK\x03\x04")
    cat, _ = classifier.rule_based_classify(FileItem(zip_file))
    assert cat == "Archives"

    exe_file = tmp_path / "installer.exe"
    exe_file.write_bytes(b"MZ\x90\x00")
    cat, _ = classifier.rule_based_classify(FileItem(exe_file))
    assert cat == "Installers"
