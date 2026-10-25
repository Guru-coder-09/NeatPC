"""Universal Deep Content Analyzer for NeatPC.

Inspects the ACTUAL INTERNAL CONTENTS of every file and folder, incorporates
photo EXIF metadata, user custom YAML rules, and classifies items into clean categories.
"""

import os
import re
from pathlib import Path
from typing import Tuple, List, Optional
import pypdf
import docx

from .scanner import FileItem
from .config import USER_CONFIG, EXTENSION_MAPPINGS
from .exif import get_exif_destination_subfolder, get_image_exif_info


# --- UNIVERSAL TAXONOMY CONSTANTS ---

# Documents Taxonomy
DOC_LEGAL_COURT = "Documents/Legal & Contracts/Court Filings & Orders"
DOC_LEGAL_NOTICES = "Documents/Legal & Contracts/Regulatory & Notices"
DOC_LEGAL_AGREEMENTS = "Documents/Legal & Contracts/Agreements & MOUs"

DOC_FINANCE_INVOICES = "Documents/Finance & Invoices/Receipts & Invoices"
DOC_FINANCE_STATEMENTS = "Documents/Finance & Invoices/Bank & Tax Statements"

DOC_ACAD_SYLLABI = "Documents/Academic & Education/Courses & Syllabi"
DOC_ACAD_LABS = "Documents/Academic & Education/Lab Records & Handbooks"
DOC_ACAD_MANUALS = "Documents/Academic & Education/Manuals & Study Materials"
DOC_ACAD_SCHEDULES = "Documents/Academic & Education/Schedules & Rosters"

DOC_CAREER_RESUMES = "Documents/Career & Resumes/Resumes & CVs"
DOC_CAREER_CERTS = "Documents/Career & Resumes/Certificates & Awards"
DOC_CAREER_PORTFOLIOS = "Documents/Career & Resumes/Portfolios & Profiles"

DOC_WORK_REPORTS = "Documents/Work & Reports"
DOC_GENERAL = "Documents/General"

# Projects & Code Taxonomy
PROJ_SOFTWARE = "Projects & Code/Software & Web"
PROJ_HARDWARE = "Projects & Code/Hardware & Electronics"
PROJ_HACKATHONS = "Projects & Code/Hackathons & Competitions"

# Presentations & Spreadsheets
SYS_PRESENTATIONS = "Presentations"
SYS_SPREADSHEETS = "Spreadsheets & Data"

# System / Media Taxonomy
SYS_SHORTCUTS = "Shortcuts"
SYS_INSTALLERS = "Installers"
SYS_ARCHIVES = "Archives"
SYS_PICTURES = "Media/Pictures"
SYS_SCREENSHOTS = "Media/Pictures/Screenshots"
SYS_VIDEOS = "Media/Videos"
SYS_AUDIO = "Media/Audio"
SYS_DUPLICATES = "_Duplicates"

# Aliases for classifier backwards compatibility
CAT_SHORTCUTS = SYS_SHORTCUTS
CAT_DOCUMENTS_GENERAL = DOC_GENERAL


def count_matches(patterns: List[str], text: str) -> int:
    """Counts regex word boundary matches in text."""
    return sum(1 for pat in patterns if re.search(pat, text, re.IGNORECASE))


def analyze_directory_internal(dir_path: Path) -> Tuple[str, str]:
    """
    Opens and inspects the internal contents of a directory to categorize it granularly.
    """
    try:
        children = list(dir_path.iterdir())
    except (PermissionError, OSError):
        return "Folders", "Directory (unreadable)"

    child_names = [c.name.lower() for c in children[:40]]
    combined_names = " ".join(child_names)
    dir_name_lower = dir_path.name.lower()

    # 1. Legal / Regulatory Evidentiary Folders
    legal_sigs = ["oa no", "joint committee", "ngt", "survey", "reports_002", "prelitigation", "litigation", "high court"]
    if any(sig in combined_names for sig in legal_sigs) or any(sig in dir_name_lower for sig in ["ngt", "onsolated"]):
        if "prelitigation" in combined_names or "notice" in combined_names:
            return DOC_LEGAL_NOTICES, "Pre-litigation legal notice evidentiary folder"
        return DOC_LEGAL_COURT, "Court and regulatory tribunal evidentiary case files"

    # 2. Electronics & Hardware Projects (Arduino, PCB, Schematics, Gerber)
    hardware_extensions = {".ino", ".kicad_pcb", ".sch", ".gbr", ".gerber", ".drl", ".brd"}
    has_hw_files = any(c.suffix.lower() in hardware_extensions for c in children)
    if has_hw_files or (any(w in dir_name_lower for w in ["sketch", "arduino", "circuit", "schematic"]) and "court" not in combined_names):
        return PROJ_HARDWARE, "Hardware / Electronics engineering project"

    # 3. Software & Web Projects
    code_extensions = {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".sql", ".java", ".cpp", ".rs", ".go"}
    has_package_json = "package.json" in child_names or "requirements.txt" in child_names or "cargo.toml" in child_names
    has_web_entry = any(n in child_names for n in ["index.html", "script.js", "app.js", "style.css", "main.py"])
    code_file_count = sum(1 for c in children if c.suffix.lower() in code_extensions)

    if has_package_json or has_web_entry or (code_file_count >= 2) or any(w in dir_name_lower for w in ["store", "app", "predictor", "shopping cart", "backend", "frontend"]):
        return PROJ_SOFTWARE, "Software / Web engineering project repository"

    # 4. Media Collections
    image_count = sum(1 for c in children if c.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"])
    video_count = sum(1 for c in children if c.suffix.lower() in [".mp4", ".mov", ".mkv", ".avi"])
    if len(children) > 0 and image_count / len(children) >= 0.7:
        return SYS_PICTURES, "Photo collection album"
    if len(children) > 0 and video_count / len(children) >= 0.7:
        return SYS_VIDEOS, "Video recordings folder"

    return "Folders", "Folder directory"


def analyze_file_item(item: FileItem) -> Tuple[str, str]:
    """
    Opens and inspects the internal details of a file, checks user YAML custom rules,
    inspects EXIF camera/timestamp data, and returns a universal category path.
    """
    # 1. Directories
    if item.is_dir:
        return analyze_directory_internal(item.path)

    # 2. Application Shortcuts
    if item.is_shortcut:
        return SYS_SHORTCUTS, "Application shortcut"

    # 3. User Custom YAML Rules Check (Highest priority custom overrides)
    lower_stem = item.stem.lower()
    lower_name = item.name.lower()

    custom_rules = USER_CONFIG.get("custom_rules", [])
    for rule in custom_rules:
        kw = rule.get("keyword", "").lower()
        dest = rule.get("destination")
        if kw and dest and (kw in lower_name or kw in lower_stem):
            return dest, f"Custom user rule: keyword '{kw}'"

    # 4. Executables & Software Installers
    if item.suffix in [".exe", ".msi", ".iso", ".dmg"]:
        return SYS_INSTALLERS, "Software installer / executable binary"

    # 5. Archives
    if item.suffix in [".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"]:
        return SYS_ARCHIVES, "Compressed archive package"

    # 6. Media Files: Videos & Audio
    if item.suffix in [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm"]:
        return SYS_VIDEOS, "Video media recording"
    if item.suffix in [".mp3", ".wav", ".flac", ".aac", ".m4a"]:
        return SYS_AUDIO, "Audio recording file"

    # 7. Media Files: Images with EXIF Date & Camera Extraction
    if item.suffix in [".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"]:
        if any(w in lower_name for w in ["certificate", "award", "diploma", "completion"]):
            return DOC_CAREER_CERTS, "Certificate / award credential image"
        if "screenshot" in lower_stem or "screen shot" in lower_stem:
            return SYS_SCREENSHOTS, "Screenshot capture"

        # Check if EXIF photo sorting is enabled
        if USER_CONFIG.get("exif_photo_sorting", True):
            exif_dest = get_exif_destination_subfolder(item.path)
            if exif_dest:
                info = get_image_exif_info(item.path)
                camera_info = f" ({info['camera']})" if info.get("camera") else ""
                return exif_dest, f"Photo capture date: {info.get('date_str', 'EXIF')}{camera_info}"

        return SYS_PICTURES, "Image media"

    # 8. Presentations
    if item.suffix in [".pptx", ".ppt", ".key"]:
        return SYS_PRESENTATIONS, "Presentation slide deck"

    # 9. Spreadsheets & Data Tables
    if item.suffix in [".xlsx", ".xls", ".csv"]:
        if any(w in lower_name for w in ["timetable", "schedule", "roll", "roster"]):
            return DOC_ACAD_SCHEDULES, "Class schedule or student roster spreadsheet"
        return SYS_SPREADSHEETS, "Data spreadsheet / table"

    # 10. Source Code Files
    if item.suffix in [".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".cpp", ".c", ".sql", ".rs", ".go", ".java"]:
        return PROJ_SOFTWARE, f"Programming source code ({item.suffix})"

    # 11. Deep Content Inspection for Documents (PDF, Word, Text, etc.)
    snippet = item.extract_preview(max_chars=2000)
    combined = f"{item.name} {snippet}".lower()

    # --- CAREER: RESUMES & CVS ---
    is_resume = (
        any(w in lower_name for w in ["resume", "cv", "lebenslauf", "curriculum_vitae"])
        or "curriculum vitae" in combined
        or (
            "education" in combined 
            and ("experience" in combined or "skills" in combined) 
            and any(w in combined for w in ["email", "phone", "profile", "summary", "objective"])
        )
    )
    if is_resume:
        return DOC_CAREER_RESUMES, "Professional Resume / Curriculum Vitae"

    # --- CAREER: CERTIFICATES & AWARDS ---
    if (
        any(w in lower_name for w in ["certificate", "award", "diploma", "hall ticket"])
        or "certificate of completion" in combined
        or "has successfully completed" in combined
        or "certificate of participation" in combined
    ):
        return DOC_CAREER_CERTS, "Course or hackathon achievement certificate"

    # --- CAREER: PORTFOLIOS & EXTRACURRICULAR ---
    if any(w in combined for w in ["portfolio", "aiesec", "summit", "sponsorship outreach", "delegates"]):
        return DOC_CAREER_PORTFOLIOS, "Professional portfolio / extracurricular document"

    # --- LEGAL: COURT FILINGS, TRIBUNAL & ORDERS ---
    if (
        re.search(r"\b(?:ngt|national green tribunal|southern zone|joint committee report|original application|oa\s*[0-9]+|crp|civil revision petition|high court|supreme court|affidavit|interlocutory|reply affidavit|rejoinder)\b", combined)
        or lower_name.startswith("crp_")
        or "02_reply" in lower_name
        or "rejoinder" in lower_name
        or "urgent_hearing" in lower_name
    ):
        return DOC_LEGAL_COURT, "Court ruling, tribunal order or legal affidavit"

    # --- LEGAL: REGULATORY, NOTICES & STATUTORY ---
    if (
        "pre litigation notice" in combined 
        or "pre-litigation" in combined 
        or "legal notice" in combined
        or "statutory safety requisition" in combined
        or "mines safety" in combined
        or "pollution control" in combined
        or re.search(r"\bdgms\b", combined)
    ):
        return DOC_LEGAL_NOTICES, "Regulatory notice or statutory requisition"

    # --- LEGAL: AGREEMENTS, CONTRACTS & MOUS ---
    if (
        "memorandum of understanding" in combined 
        or re.search(r"\bmou\b", combined) 
        or "non-disclosure agreement" in combined 
        or re.search(r"\bnda\b", combined)
        or "agreement" in combined
        or "msme" in combined
        or "udyog aadhaar" in combined
    ):
        return DOC_LEGAL_AGREEMENTS, "Contract agreement, MOU or business registration"

    # --- FINANCE: INVOICES, BILLS & RECEIPTS ---
    if (
        any(w in lower_name for w in ["invoice", "receipt", "bill", "challan", "fee"])
        or "tax invoice" in combined
        or "bill to" in combined
        or ("tuition" in combined and "receipt" in combined)
        or "payment confirmation" in combined
    ):
        return DOC_FINANCE_INVOICES, "Payment receipt, invoice or commercial bill"

    # --- FINANCE: BANK & TAX STATEMENTS ---
    if (
        "account statement" in combined 
        or "bank statement" in combined 
        or "accountstatement" in lower_name
        or "credit report" in combined
        or "tax return" in combined
        or "form 16" in combined
        or "itr" in combined
    ):
        return DOC_FINANCE_STATEMENTS, "Bank savings statement or financial report"

    # --- ACADEMIC: COURSE GUIDES & SYLLABI ---
    if any(w in lower_name for w in ["course_guide", "course guide", "syllabus", "curriculum", "ap_course"]):
        return DOC_ACAD_SYLLABI, "Academic course guide or syllabus"

    # --- ACADEMIC: LAB HANDBOOKS & PRACTICAL RECORDS ---
    if any(w in lower_name for w in ["lab_exam_handbook", "exam_handbook", "lab record", "lab manual", "practical manual"]):
        return DOC_ACAD_LABS, "Laboratory exam handbook or practical record"

    # --- ACADEMIC: STUDY MANUALS & TEXTBOOKS ---
    if (
        "engineering drawing" in combined 
        or "pictorial solutions" in combined 
        or "textbook" in combined
        or "study material" in combined
        or "ndbhatt" in lower_name
    ):
        return DOC_ACAD_MANUALS, "Academic textbook, manual or study material"

    # --- ACADEMIC: SCHEDULES & ROSTERS ---
    if any(w in lower_name for w in ["roll nos list", "timetable", "time table", "subjects", "iddmp"]):
        return DOC_ACAD_SCHEDULES, "Class schedule or student roll number roster"

    # --- PROJECTS: HACKATHONS & COMPETITIONS ---
    if any(w in lower_name for w in ["sih", "hackathon", "ecosync", "hexavox", "problem statement", "pitch deck", "ideation"]):
        return PROJ_HACKATHONS, "Hackathon concept proposal or competition entry"

    # --- WORK: REPORTS & SPECIFICATIONS ---
    if (
        "meeting minutes" in combined 
        or "minutes of meeting" in combined 
        or "progress report" in combined
        or "project brief" in combined
    ):
        return DOC_WORK_REPORTS, "Work report or meeting minutes"

    # Default fallback for unclassified documents
    return DOC_GENERAL, "General document"
