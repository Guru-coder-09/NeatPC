"""Main entry point for NeatPC file organizer CLI."""

import sys
import os
import argparse
from pathlib import Path

# Ensure UTF-8 stdout encoding on Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from neatpc.config import DESKTOP_DIR, DOWNLOADS_DIR
from neatpc.cli import (
    run_organize,
    run_undo,
    run_shortcuts_only,
    run_documents_only,
    run_projects_only,
    run_spreadsheets_presentations,
    run_find_duplicates,
    run_smart_renamer_station,
    show_history,
    interactive_menu,
    print_banner
)
from neatpc.watcher import start_watcher


def main():
    parser = argparse.ArgumentParser(
        description="NeatPC Workstation: Intelligent Desktop, File & Application Automation with Multi-Provider AI & Undo Support.",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument("--desktop", action="store_true", help="Organize Desktop files, folders, and app shortcuts")
    parser.add_argument("--downloads", action="store_true", help="Organize Downloads folder")
    parser.add_argument("--path", type=str, help="Organize a custom folder or directory")
    parser.add_argument("--watch", nargs="?", const="downloads", type=str, help="Start live background watcher on folder (default: downloads)")
    parser.add_argument("--shortcuts", action="store_true", help="Organize only application shortcuts (.lnk and .url)")
    parser.add_argument("--documents", action="store_true", help="Organize only document files (Legal, Finance, Academic, Career)")
    parser.add_argument("--code", action="store_true", help="Organize only project folders and source code")
    parser.add_argument("--spreadsheets", action="store_true", help="Organize only spreadsheets and presentations")
    parser.add_argument("--duplicates", action="store_true", help="Scan and quarantine duplicate files")
    parser.add_argument("--rename", action="store_true", help="Scan and smart-rename cryptic document names")
    parser.add_argument("--sim", "--dry-run", dest="dry_run", action="store_true", help="Simulation mode: preview changes without moving any files (like 'organize sim')")
    parser.add_argument("--undo", action="store_true", help="Roll back the most recent organization session")
    parser.add_argument("--history", action="store_true", help="Display audit history of past organization runs")
    parser.add_argument("--no-ai", action="store_true", help="Use rule-based heuristics only without Gemini or Ollama")
    parser.add_argument("-y", "--yes", action="store_true", help="Automatically confirm and apply changes")

    args = parser.parse_args()

    # 1. Background Watcher Daemon
    if args.watch is not None:
        target = DOWNLOADS_DIR if args.watch.lower() == "downloads" else (DESKTOP_DIR if args.watch.lower() == "desktop" else Path(args.watch.strip('"')))
        start_watcher(target)
        return

    # 2. Undo & History
    if args.undo:
        run_undo()
        return

    if args.history:
        show_history()
        return

    target = Path(args.path.strip('"')) if args.path else None

    # 3. Targeted Tools
    if args.shortcuts:
        run_shortcuts_only(target or DESKTOP_DIR)
        return

    if args.documents:
        run_documents_only(target or DESKTOP_DIR)
        return

    if args.code:
        run_projects_only(target or DESKTOP_DIR)
        return

    if args.spreadsheets:
        run_spreadsheets_presentations(target or DESKTOP_DIR)
        return

    if args.duplicates:
        run_find_duplicates(target or DOWNLOADS_DIR)
        return

    if args.rename:
        run_smart_renamer_station(target or DESKTOP_DIR)
        return

    use_ai = not args.no_ai

    # 4. Standard Workflows
    if args.desktop:
        run_organize(
            DESKTOP_DIR,
            use_ai=use_ai,
            dry_run=args.dry_run,
            include_shortcuts=True,
            auto_approve=args.yes
        )
        return

    if args.downloads:
        run_organize(
            DOWNLOADS_DIR,
            use_ai=use_ai,
            dry_run=args.dry_run,
            include_shortcuts=False,
            auto_approve=args.yes
        )
        return

    if args.path:
        if not target.exists() or not target.is_dir():
            print(f"Error: Target path does not exist or is not a directory: {target}")
            sys.exit(1)
        run_organize(
            target,
            use_ai=use_ai,
            dry_run=args.dry_run,
            include_shortcuts=False,
            auto_approve=args.yes
        )
        return

    # Default: Interactive Menu
    interactive_menu()


if __name__ == "__main__":
    main()
