"""Interactive Terminal CLI interface using Rich with Diverse Specialized Tools."""

import sys
import os
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.prompt import Prompt, Confirm
from rich import box

from .config import DESKTOP_DIR, DOWNLOADS_DIR, CONFIG_FILE_PATH, CONFIG_YAML_PATH, USER_CONFIG
from .scanner import scan_directory, FileItem
from .classifier import Classifier
from .duplicates import DuplicateDetector
from .renamer import SmartRenamer, is_cryptic_or_unnamed
from .organizer import Organizer, OrganizationPlanItem
from .journal import Journal
from .llm import UnifiedLLMClient
from .watcher import start_watcher

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

console = Console(legacy_windows=False)


def print_banner():
    """Prints a styled banner for NeatPC with active AI engine info."""
    llm = UnifiedLLMClient()
    if llm.active_provider == "gemini":
        ai_badge = "[bold green]Google Gemini Cloud AI[/bold green]"
    elif llm.active_provider == "ollama":
        ai_badge = f"[bold cyan]Local Ollama ({llm.ollama_model})[/bold cyan]"
    else:
        ai_badge = "[dim yellow]Offline Smart Heuristics[/dim yellow]"

    banner_text = (
        "[bold cyan]✨ NeatPC Workstation[/bold cyan] - [bold white]Intelligent Desktop & File Automation[/bold white]\n"
        f"[dim]AI Engine:[/dim] {ai_badge}  •  [dim]Safety:[/dim] [green]Dry-Run Preview & 1-Click Rollback[/green]\n"
        "[dim]Deep Content Parsing • Multi-Stage Deduplication • EXIF Camera Sorting • Live Watcher[/dim]"
    )
    console.print(Panel(banner_text, style="blue", box=box.ROUNDED, expand=False))


def display_plan_table(plan: List[OrganizationPlanItem], target_root: Path):
    """Displays a formatted table of planned operations."""
    if not plan:
        console.print("\n[yellow]✨ Nothing to organize! Target folder is already clean and organized.[/yellow]\n")
        return

    table = Table(
        title=f"📋 Proposed Organization Plan for: {target_root}",
        box=box.ROUNDED,
        header_style="bold magenta",
        show_lines=True
    )

    table.add_column("Type", justify="center", width=5)
    table.add_column("Original Item", style="bold white", max_width=32, overflow="ellipsis")
    table.add_column("Proposed New Name", style="bold green", max_width=32, overflow="ellipsis")
    table.add_column("Target Subfolder", style="cyan", max_width=32)
    table.add_column("Status / Action", justify="center", width=14)

    for item in plan:
        if item.is_duplicate:
            icon = "⚠️"
        elif item.source.is_dir():
            icon = "📁"
        elif item.source.suffix in [".lnk", ".url"]:
            icon = "🔗"
        elif item.source.suffix in [".pdf", ".docx", ".doc", ".txt", ".md"]:
            icon = "📄"
        elif item.source.suffix in [".png", ".jpg", ".jpeg", ".webp", ".gif"]:
            icon = "🖼️"
        elif item.source.suffix in [".mp4", ".mov", ".mkv"]:
            icon = "🎥"
        elif item.source.suffix in [".zip", ".rar", ".7z"]:
            icon = "📦"
        elif item.source.suffix in [".exe", ".msi"]:
            icon = "⚙️"
        else:
            icon = "📝"

        try:
            rel_dest = item.destination.relative_to(target_root)
            target_str = str(rel_dest.parent)
        except ValueError:
            target_str = item.category

        if item.is_duplicate:
            status_badge = "[bold yellow]Duplicate[/bold yellow]"
            new_name_display = f"[dim]{item.new_name}[/dim]"
        elif item.is_renamed:
            status_badge = "[bold green]✨ Renamed[/bold green]"
            new_name_display = f"[bold green]{item.new_name}[/bold green]"
        elif item.is_collision:
            status_badge = "[yellow]Rename (safe)[/yellow]"
            new_name_display = item.new_name
        else:
            status_badge = "[dim]Move[/dim]"
            new_name_display = f"[dim]{item.new_name}[/dim]"

        table.add_row(
            icon,
            item.original_name,
            new_name_display,
            f"📁 {target_str}",
            status_badge
        )

    console.print(table)


def display_tree_preview(plan: List[OrganizationPlanItem], target_root: Path):
    """Displays a tree structure of the resulting organized folders."""
    if not plan:
        return

    tree = Tree(f"[bold blue]📁 {target_root.name}[/bold blue] (Preview)")
    category_nodes = {}

    for item in plan:
        parts = item.category.split("/")
        curr_node = tree
        curr_path = ""

        for part in parts:
            curr_path = f"{curr_path}/{part}" if curr_path else part
            if curr_path not in category_nodes:
                category_nodes[curr_path] = curr_node.add(f"[cyan]📁 {part}[/cyan]")
            curr_node = category_nodes[curr_path]

        display_label = f"[bold green]{item.new_name}[/bold green]" if item.is_renamed else f"[dim]{item.new_name}[/dim]"
        if item.is_duplicate:
            display_label = f"[yellow]⚠️ {item.new_name} (copy)[/yellow]"
        curr_node.add(display_label)

    console.print(Panel(tree, title="🌳 Resulting Directory Structure Preview", box=box.ROUNDED))


def run_organize(
    target_dir: Path,
    use_ai: bool = True,
    dry_run: bool = False,
    include_shortcuts: bool = True,
    auto_approve: bool = False,
    detect_duplicates: bool = True,
    smart_rename: bool = True,
    category_filter: Optional[str] = None
):
    """Executes the full scan, duplicate detection, smart rename, classify, and organize workflow."""
    console.print(f"\n[bold green]🔍 Scanning directory:[/bold green] [cyan]{target_dir}[/cyan] ...")

    items = scan_directory(target_dir, include_shortcuts=include_shortcuts)
    if not items:
        console.print("[yellow]No unorganized files found in this directory.[/yellow]\n")
        return

    console.print(f"Found [bold white]{len(items)}[/bold white] eligible items to evaluate.")

    duplicate_map: Dict[str, Dict[str, Any]] = {}
    if detect_duplicates:
        with console.status("[bold yellow]Detecting duplicate files via content hashing (SHA-256)...[/bold yellow]"):
            detector = DuplicateDetector()
            duplicate_map = detector.identify_duplicates(items)

    rename_map: Dict[str, str] = {}
    if smart_rename:
        with console.status("[bold cyan]Analyzing document contents & resolving cryptic filenames...[/bold cyan]"):
            classifier = Classifier(use_ai=use_ai)
            renamer = SmartRenamer(llm_client=classifier.llm)

            cryptic_candidates = [
                it for it in items 
                if not it.is_dir 
                and not it.is_shortcut 
                and str(it.path) not in duplicate_map
                and it.suffix in [".pdf", ".docx", ".doc", ".txt", ".csv", ".xlsx"]
                and is_cryptic_or_unnamed(it.name)
            ]

            if cryptic_candidates:
                if classifier.llm and classifier.llm.is_available:
                    rename_map = renamer.batch_ai_rename(cryptic_candidates)

                for it in cryptic_candidates:
                    if str(it.path) not in rename_map:
                        local_name = renamer.local_heuristic_rename(it)
                        if local_name:
                            rename_map[str(it.path)] = local_name

    with console.status("[bold green]Building intelligent universal plan...[/bold green]"):
        classifier = Classifier(use_ai=use_ai)
        classifications = classifier.classify_batch(items)
        organizer = Organizer(target_dir)
        plan = organizer.build_plan(
            items=items,
            classifications=classifications,
            duplicate_info=duplicate_map,
            rename_map=rename_map
        )

    # Optional filter for specific category
    if category_filter:
        plan = [p for p in plan if category_filter.lower() in p.category.lower()]

    if not plan:
        console.print("[green]✅ No items matching the filter need organizing![/green]\n")
        return

    dup_count = sum(1 for p in plan if p.is_duplicate)
    rename_count = sum(1 for p in plan if p.is_renamed)
    console.print(
        f"\n[bold white]Analysis Summary:[/bold white] "
        f"[cyan]{len(plan)}[/cyan] items to organize • "
        f"[yellow]{dup_count}[/yellow] duplicates detected (routed to _Duplicates) • "
        f"[green]{rename_count}[/green] cryptic files smart-renamed\n"
    )

    display_plan_table(plan, target_dir)
    display_tree_preview(plan, target_dir)

    if dry_run:
        console.print("[bold yellow]🔎 Dry-run mode completed. No files were moved or renamed.[/bold yellow]\n")
        return

    # Interactive Action Selection
    selected_plan = plan
    if not auto_approve:
        console.print("\n[bold white]Select how you want to apply this plan:[/bold white]")
        console.print("  [bold green][A][/bold green] Apply All (Organize all files, isolate duplicates & rename)")
        console.print("  [bold yellow][D][/bold yellow] Quarantining Duplicates Only (Move duplicate copies to _Duplicates/)")
        console.print("  [bold cyan][R][/bold cyan] Smart Renames Only (Apply clean names leaving folders as-is)")
        console.print("  [bold magenta][S][/bold magenta] Select Specific Category to Apply")
        console.print("  [bold red][C][/bold red] Cancel (Do nothing)")

        user_action = Prompt.ask("\nChoose action", choices=["a", "d", "r", "s", "c"], default="a").lower()

        if user_action == "c":
            console.print("[yellow]Operation canceled. No files were modified.[/yellow]\n")
            return
        elif user_action == "d":
            selected_plan = [p for p in plan if p.is_duplicate]
        elif user_action == "r":
            selected_plan = [p for p in plan if p.is_renamed]
        elif user_action == "s":
            available_cats = sorted(list({p.category.split('/')[0] for p in plan}))
            console.print("\nAvailable Categories:")
            for idx, c in enumerate(available_cats, 1):
                console.print(f"  {idx}. {c}")
            choice_idx = Prompt.ask("Enter number of category to organize", default="1")
            try:
                chosen_cat = available_cats[int(choice_idx) - 1]
                selected_plan = [p for p in plan if p.category.startswith(chosen_cat)]
            except Exception:
                console.print("[red]Invalid selection. Applying all.[/red]")

    if not selected_plan:
        console.print("[yellow]No items selected to apply.[/yellow]\n")
        return

    with console.status("[bold green]Applying changes safely with rollback journal...[/bold green]"):
        result = organizer.execute_plan(selected_plan)

    console.print(f"\n[bold green]🎉 Successfully applied {result['moved_count']} items![/bold green]")
    console.print(f"[dim]Transaction Session ID: {result['session_id']}[/dim]")

    if result["errors"]:
        console.print(f"[bold red]⚠️ Encountered {len(result['errors'])} errors:[/bold red]")
        for err in result["errors"]:
            console.print(f"  • {err['file']}: {err['error']}")

    console.print("\n[bold cyan]Tip:[/bold cyan] To revert anytime, run: [bold white]python main.py --undo[/bold white]\n")


def run_shortcuts_only(target_dir: Path):
    """Organizes desktop shortcuts (.lnk and .url) without touching any files."""
    console.print(f"\n[bold green]🔗 Scanning Application Shortcuts in:[/bold green] [cyan]{target_dir}[/cyan] ...")
    items = [FileItem(p) for p in list(target_dir.glob("*.lnk")) + list(target_dir.glob("*.url"))]
    if not items:
        console.print("[yellow]No application shortcuts found to organize.[/yellow]\n")
        return

    classifier = Classifier(use_ai=False)
    organizer = Organizer(target_dir)
    classifications = {str(it.path): (classifier.classify_shortcut(it), "Application shortcut") for it in items}
    plan = organizer.build_plan(items, classifications)

    display_plan_table(plan, target_dir)
    confirm = Confirm.ask(f"[bold green]Move {len(plan)} shortcuts into organized categories?[/bold green]", default=True)
    if confirm:
        with console.status("[bold green]Organizing shortcuts...[/bold green]"):
            result = organizer.execute_plan(plan)
        console.print(f"\n[bold green]✅ Organized {result['moved_count']} shortcuts![/bold green]\n")


def run_documents_only(target_dir: Path):
    """Organizes only document files into structured universal subcategories."""
    console.print(f"\n[bold cyan]📄 Scanning Documents in:[/bold cyan] [cyan]{target_dir}[/cyan] ...")
    run_organize(target_dir, include_shortcuts=False, category_filter="Documents")


def run_projects_only(target_dir: Path):
    """Organizes only source code, project repos, and engineering files."""
    console.print(f"\n[bold cyan]💻 Scanning Projects & Code in:[/bold cyan] [cyan]{target_dir}[/cyan] ...")
    run_organize(target_dir, include_shortcuts=False, category_filter="Projects")


def run_spreadsheets_presentations(target_dir: Path):
    """Organizes presentations (.pptx) and spreadsheets (.xlsx, .csv)."""
    console.print(f"\n[bold cyan]📊 Scanning Presentations & Spreadsheets in:[/bold cyan] [cyan]{target_dir}[/cyan] ...")
    run_organize(target_dir, include_shortcuts=False, category_filter="Presentations")


def run_find_duplicates(target_dir: Path):
    """Finds and lists duplicate files in a folder with action options."""
    console.print(f"\n[bold yellow]🔍 Scanning for duplicates in:[/bold yellow] [cyan]{target_dir}[/cyan] ...")
    items = scan_directory(target_dir, include_shortcuts=False)
    detector = DuplicateDetector()
    dups = detector.identify_duplicates(items)

    if not dups:
        console.print("[green]✨ No duplicate files found! All files are unique.[/green]\n")
        return

    table = Table(title=f"⚠️ Duplicate Files Detected in {target_dir.name}", box=box.ROUNDED)
    table.add_column("Duplicate File Copy", style="yellow")
    table.add_column("Master File (Original)", style="green")
    table.add_column("SHA-256 Hash", style="dim")

    for path_str, info in dups.items():
        dup_path = Path(path_str)
        table.add_row(
            dup_path.name,
            str(info.get("original_name")),
            str(info.get("hash"))
        )

    console.print(table)
    console.print(f"\n[bold yellow]Found {len(dups)} duplicate copies.[/bold yellow]")

    action = Prompt.ask(
        "What would you like to do with these duplicates?",
        choices=["quarantine", "preview", "cancel"],
        default="quarantine"
    )
    if action == "quarantine":
        organizer = Organizer(target_dir)
        plan = []
        for path_str, info in dups.items():
            src = Path(path_str)
            dest = target_dir / "_Duplicates" / src.name
            plan.append(OrganizationPlanItem(
                source=src,
                destination=dest,
                category="_Duplicates",
                reason=f"Duplicate of {info.get('original_name')}",
                is_duplicate=True,
                original_file_match=info.get("original_name")
            ))
        with console.status("[bold green]Quarantining duplicates...[/bold green]"):
            res = organizer.execute_plan(plan)
        console.print(f"[bold green]✅ Safely quarantined {res['moved_count']} duplicates to '_Duplicates/' folder![/bold green]\n")


def run_smart_renamer_station(target_dir: Path):
    """Scans and renames cryptic/generic documents with preview."""
    console.print(f"\n[bold cyan]✨ Scanning for cryptic & poorly named documents in:[/bold cyan] [cyan]{target_dir}[/cyan] ...")
    items = scan_directory(target_dir, include_shortcuts=False)
    cryptic = [
        it for it in items 
        if not it.is_dir and not it.is_shortcut 
        and it.suffix in [".pdf", ".docx", ".doc", ".txt", ".csv"] 
        and is_cryptic_or_unnamed(it.name)
    ]

    if not cryptic:
        console.print("[green]✨ All documents already have clear, readable names![/green]\n")
        return

    classifier = Classifier(use_ai=True)
    renamer = SmartRenamer(llm_client=classifier.llm)

    with console.status("[bold cyan]Analyzing contents and generating smart names...[/bold cyan]"):
        rename_map = {}
        if classifier.llm and classifier.llm.is_available:
            rename_map = renamer.batch_ai_rename(cryptic)
        for it in cryptic:
            if str(it.path) not in rename_map:
                loc = renamer.local_heuristic_rename(it)
                if loc:
                    rename_map[str(it.path)] = loc

    if not rename_map:
        console.print("[yellow]Could not generate new names for candidates.[/yellow]\n")
        return

    table = Table(title="✨ Smart Renaming Proposals", box=box.ROUNDED)
    table.add_column("Original Filename", style="white")
    table.add_column("Proposed Clean Name", style="bold green")

    for path_str, new_name in rename_map.items():
        table.add_row(Path(path_str).name, new_name)

    console.print(table)
    confirm = Confirm.ask(f"[bold green]Apply renaming to these {len(rename_map)} files?[/bold green]", default=True)
    if confirm:
        organizer = Organizer(target_dir)
        plan = []
        for path_str, new_name in rename_map.items():
            src = Path(path_str)
            dest = src.parent / new_name
            plan.append(OrganizationPlanItem(
                source=src,
                destination=dest,
                category="Renamed",
                reason=f"Smart renamed: {new_name}",
                is_renamed=True,
                original_name=src.name,
                new_name=new_name
            ))
        with console.status("[bold green]Renaming files...[/bold green]"):
            res = organizer.execute_plan(plan)
        console.print(f"[bold green]✅ Successfully renamed {res['moved_count']} files![/bold green]\n")


def run_undo():
    """Rolls back the most recent organization session."""
    organizer = Organizer(DESKTOP_DIR)
    last_session = organizer.journal.get_last_session()

    if not last_session:
        console.print("\n[yellow]⚠️ No active organization session found to undo.[/yellow]\n")
        return

    console.print(Panel(
        f"[bold]Session ID:[/bold] {last_session['session_id']}\n"
        f"[bold]Date:[/bold] {last_session['timestamp']}\n"
        f"[bold]Root Folder:[/bold] {last_session['target_dir']}\n"
        f"[bold]Files Moved / Renamed:[/bold] {last_session['move_count']}",
        title="⏪ Session to Rollback",
        box=box.ROUNDED
    ))

    confirm = Confirm.ask("[bold red]Are you sure you want to restore all files to original locations and names?[/bold red]", default=True)
    if not confirm:
        console.print("[yellow]Undo canceled.[/yellow]\n")
        return

    with console.status("[bold yellow]Restoring files to original names and locations...[/bold yellow]"):
        result = organizer.rollback_session()

    if result["success"]:
        console.print(f"\n[bold green]✅ Rollback successful![/bold green]")
        console.print(f"Restored: [bold white]{result['restored_count']}[/bold white] files.")
        if result['failed_count'] > 0:
            console.print(f"[yellow]Failed to restore: {result['failed_count']} files.[/yellow]")
        console.print(f"Cleaned up: [dim]{result['cleaned_dirs']} empty folders.[/dim]\n")
    else:
        console.print(f"[red]❌ Rollback failed: {result.get('message')}[/red]\n")


def show_history():
    """Lists past organization sessions."""
    journal = Journal()
    sessions = journal.list_sessions()

    if not sessions:
        console.print("\n[yellow]No organization history recorded yet.[/yellow]\n")
        return

    table = Table(title="📜 NeatPC History Log", box=box.ROUNDED)
    table.add_column("Session ID", style="cyan")
    table.add_column("Date", style="dim")
    table.add_column("Target Directory", style="white")
    table.add_column("Items Moved / Renamed", justify="center")
    table.add_column("Status", justify="center")

    for s in reversed(sessions):
        status_str = "[green]Active[/green]" if s.get("status") == "completed" else "[dim]Undone[/dim]"
        table.add_row(
            s.get("session_id", "N/A"),
            s.get("timestamp", "N/A")[:19],
            s.get("target_dir", "N/A"),
            str(s.get("move_count", 0)),
            status_str
        )

    console.print(table)


def configure_ai():
    """Interactive helper to configure AI Provider (Gemini vs Local Ollama)."""
    llm = UnifiedLLMClient()
    console.print(Panel(
        f"[bold]Current Active Provider:[/bold] [cyan]{llm.active_provider.upper()}[/cyan]\n"
        f"[bold]Gemini Model:[/bold] {llm.gemini_model}\n"
        f"[bold]Ollama Endpoint:[/bold] {llm.ollama_endpoint} (Model: {llm.ollama_model})\n"
        f"[bold]Config File:[/bold] {CONFIG_YAML_PATH}",
        title="🤖 AI Engine Settings",
        box=box.ROUNDED
    ))

    choice = Prompt.ask(
        "Choose setting to configure",
        choices=["gemini_key", "ollama_endpoint", "open_config", "cancel"],
        default="gemini_key"
    )

    if choice == "gemini_key":
        new_key = Prompt.ask("Enter Google Gemini API Key", default="")
        if new_key.strip():
            os.environ["GEMINI_API_KEY"] = new_key.strip()
            console.print("[green]✅ Gemini API Key set for this session![/green]\n")
    elif choice == "ollama_endpoint":
        new_ep = Prompt.ask("Enter Ollama Endpoint URL", default=llm.ollama_endpoint)
        new_model = Prompt.ask("Enter Ollama Model", default=llm.ollama_model)
        console.print(f"[green]✅ Set Ollama to {new_ep} with model {new_model}[/green]\n")
    elif choice == "open_config":
        console.print(f"[cyan]Edit your settings directly in: {CONFIG_YAML_PATH}[/cyan]\n")


def interactive_menu():
    """Main interactive terminal workstation menu."""
    while True:
        print_banner()
        console.print(f"[dim]Active Desktop:[/dim] [cyan]{DESKTOP_DIR}[/cyan]")
        console.print(f"[dim]Downloads Folder:[/dim] [cyan]{DOWNLOADS_DIR}[/cyan]\n")

        console.print("[bold white]══════════════ 🚀 MAIN ORGANIZATION WORKFLOWS ══════════════[/bold white]")
        console.print("  [bold cyan]1[/bold cyan]  🖥️  Full Desktop Cleanup & Organize (Files, Folders & App Shortcuts)")
        console.print("  [bold cyan]2[/bold cyan]  📥  Downloads Folder Deep Declutter (Organize all downloads)")
        console.print("  [bold cyan]3[/bold cyan]  📂  Custom Folder / External Drive Organizer")
        console.print("  [bold cyan]4[/bold cyan]  🔎  Preview Organization (Simulation / Dry-Run Mode)\n")

        console.print("[bold white]══════════════ 🎯 SPECIALIZED TARGETED TOOLS ══════════════[/bold white]")
        console.print("  [bold cyan]5[/bold cyan]  🔗  Organize Desktop App Shortcuts Only (Leave files untouched)")
        console.print("  [bold cyan]6[/bold cyan]  📄  Organize Documents Only (Deep Content Analysis)")
        console.print("  [bold cyan]7[/bold cyan]  💻  Organize Projects & Source Code Only")
        console.print("  [bold cyan]8[/bold cyan]  📊  Organize Spreadsheets & Presentations Only")
        console.print("  [bold cyan]9[/bold cyan]  ⚠️  Duplicate Scanner & Quarantine (Isolate identical copy files)")
        console.print("  [bold cyan]10[/bold cyan] ✨  Smart Document Renaming Station (Resolve cryptic names)\n")

        console.print("[bold white]══════════════ ⚡ AUTOMATION & DAEMONS ══════════════[/bold white]")
        console.print("  [bold cyan]11[/bold cyan] 👁️  Start Live Background Watcher Daemon (Auto-organize downloads on the fly)\n")

        console.print("[bold white]══════════════ 🛡️ SAFETY, AUDIT & CONFIGURATION ══════════════[/bold white]")
        console.print("  [bold cyan]12[/bold cyan] ⏪  Instant Undo / Rollback (Restore original files & names)")
        console.print("  [bold cyan]13[/bold cyan] 📜  View Organization History & Audit Log")
        console.print("  [bold cyan]14[/bold cyan] 🤖  Configure AI Engine (Gemini Cloud vs Local Ollama)")
        console.print("  [bold cyan]15[/bold cyan] ❌  Exit\n")

        choice = Prompt.ask(
            "Select an option",
            choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15"],
            default="1"
        )

        if choice == "1":
            run_organize(DESKTOP_DIR, include_shortcuts=True)
        elif choice == "2":
            run_organize(DOWNLOADS_DIR, include_shortcuts=False)
        elif choice == "3":
            custom_path = Prompt.ask("Enter the full path of the folder you want to organize")
            p = Path(custom_path.strip().strip('"'))
            if p.exists() and p.is_dir():
                run_organize(p, include_shortcuts=False)
            else:
                console.print(f"[red]Folder does not exist: {p}[/red]\n")
        elif choice == "4":
            sub_choice = Prompt.ask("Preview which location?", choices=["desktop", "downloads"], default="desktop")
            target = DESKTOP_DIR if sub_choice == "desktop" else DOWNLOADS_DIR
            run_organize(target, include_shortcuts=(sub_choice == "desktop"), dry_run=True)
        elif choice == "5":
            run_shortcuts_only(DESKTOP_DIR)
        elif choice == "6":
            sub_choice = Prompt.ask("Organize documents in which location?", choices=["desktop", "downloads"], default="desktop")
            target = DESKTOP_DIR if sub_choice == "desktop" else DOWNLOADS_DIR
            run_documents_only(target)
        elif choice == "7":
            sub_choice = Prompt.ask("Organize projects in which location?", choices=["desktop", "downloads"], default="desktop")
            target = DESKTOP_DIR if sub_choice == "desktop" else DOWNLOADS_DIR
            run_projects_only(target)
        elif choice == "8":
            sub_choice = Prompt.ask("Organize spreadsheets/presentations in which location?", choices=["desktop", "downloads"], default="desktop")
            target = DESKTOP_DIR if sub_choice == "desktop" else DOWNLOADS_DIR
            run_spreadsheets_presentations(target)
        elif choice == "9":
            sub_choice = Prompt.ask("Scan which location for duplicates?", choices=["desktop", "downloads", "custom"], default="downloads")
            if sub_choice == "desktop":
                run_find_duplicates(DESKTOP_DIR)
            elif sub_choice == "downloads":
                run_find_duplicates(DOWNLOADS_DIR)
            else:
                cpath = Prompt.ask("Enter folder path")
                run_find_duplicates(Path(cpath.strip().strip('"')))
        elif choice == "10":
            sub_choice = Prompt.ask("Scan which location for cryptic names?", choices=["desktop", "downloads"], default="desktop")
            target = DESKTOP_DIR if sub_choice == "desktop" else DOWNLOADS_DIR
            run_smart_renamer_station(target)
        elif choice == "11":
            sub_choice = Prompt.ask("Watch which folder?", choices=["downloads", "desktop", "custom"], default="downloads")
            target = DOWNLOADS_DIR if sub_choice == "downloads" else (DESKTOP_DIR if sub_choice == "desktop" else Path(Prompt.ask("Enter path")))
            start_watcher(target)
        elif choice == "12":
            run_undo()
        elif choice == "13":
            show_history()
        elif choice == "14":
            configure_ai()
        elif choice == "15":
            console.print("\n[bold cyan]Goodbye! Keep your PC neat and clean.[/bold cyan]\n")
            sys.exit(0)

        Prompt.ask("\n[dim]Press Enter to return to main menu...[/dim]")
        console.clear()
