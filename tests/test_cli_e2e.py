"""End-to-end CLI integration tests executing main.py via subprocess."""

import sys
import subprocess
from pathlib import Path

PYTHON_EXE = sys.executable
MAIN_PY = str(Path(__file__).parent.parent / "main.py")


def test_cli_help():
    """Verify `python main.py --help` exits cleanly with code 0."""
    res = subprocess.run(
        [PYTHON_EXE, MAIN_PY, "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 0
    assert "NeatPC Workstation" in res.stdout
    assert "--sim" in res.stdout
    assert "--duplicates" in res.stdout


def test_cli_duplicates_sim_e2e(tmp_path: Path):
    """Verify `python main.py --duplicates --sim --path <dir>` does not move files."""
    f1 = tmp_path / "file1.txt"
    f2 = tmp_path / "file2.txt"
    f1.write_text("Deduplication E2E Test Content")
    f2.write_text("Deduplication E2E Test Content")

    res = subprocess.run(
        [PYTHON_EXE, MAIN_PY, "--duplicates", "--sim", "--path", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 0
    assert "Simulation mode" in res.stdout
    assert f1.exists()
    assert f2.exists()
    assert not (tmp_path / "_Duplicates").exists()


def test_cli_rename_sim_e2e(tmp_path: Path):
    """Verify `python main.py --rename --sim --path <dir>` executes cleanly."""
    f = tmp_path / "scan.pdf"
    f.write_text("Invoice and Tax Receipt 2026")

    res = subprocess.run(
        [PYTHON_EXE, MAIN_PY, "--rename", "--sim", "--path", str(tmp_path), "--no-ai"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 0
    assert f.exists()


def test_cli_shortcuts_sim_e2e(tmp_path: Path):
    """Verify `python main.py --shortcuts --sim --path <dir>` does not move shortcuts."""
    lnk = tmp_path / "TestApp.lnk"
    lnk.write_bytes(b"shortcut data")

    res = subprocess.run(
        [PYTHON_EXE, MAIN_PY, "--shortcuts", "--sim", "--path", str(tmp_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    assert res.returncode == 0
    assert "Simulation mode" in res.stdout
    assert lnk.exists()
    assert not (tmp_path / "Shortcuts").exists()
