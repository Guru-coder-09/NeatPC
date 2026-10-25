"""Universal Smart Document Renaming Engine with Multi-Provider LLM.

Generates clean, descriptive names for poorly named documents by inspecting
content snippets with heuristics and Unified LLMs (Gemini / Ollama).
"""

import re
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from .scanner import FileItem
from .llm import UnifiedLLMClient


def is_cryptic_or_unnamed(name: str) -> bool:
    """
    Determines if a filename is cryptic, generic, machine-generated, or poorly named.
    Examples:
      - '17866207659991967956a7dab5d41580.pdf' (hash/hex)
      - '01-15.pdf', '4.docx', '01_02.txt' (digits only)
      - '01_IA_001_1776077346961.pdf' (machine filing string)
      - 'New Document (1).docx', 'Untitled.pdf', 'Doc1.pdf' (generic)
    """
    stem = Path(name).stem.strip()
    lower = stem.lower()

    # Clean short names that should NOT be marked cryptic
    clean_short_names = {"cv", "mou", "nda", "tax", "gst", "pan", "bill", "rent", "w2", "resume"}
    if lower in clean_short_names:
        return False

    # Generic or placeholder names
    generic_words = [
        "untitled", "new document", "document", "doc", "file", "download", 
        "scan", "scanned", "output", "temp", "tmp", "test", "test_fpdf"
    ]
    for gw in generic_words:
        if lower == gw or lower.startswith(f"{gw}_") or lower.startswith(f"{gw} ") or lower.startswith(f"{gw}-"):
            return True

    # Numeric or symbol heavy (e.g. '01-15', '4', '12345')
    alpha_chars = sum(c.isalpha() for c in stem)
    if alpha_chars == 0 and len(stem) > 0:
        return True
    if len(stem) <= 3 and lower not in clean_short_names:
        return True

    # Long random hex/hash strings (e.g. 17866207659991967956a7dab5d41580)
    if len(stem) >= 20 and (re.match(r"^[0-9a-fA-F]+$", stem) or re.match(r"^[0-9_]+$", stem)):
        return True

    # Machine generated filing prefixes (e.g. 01_IA_001_1776077346961, 02_Reply_009_...)
    if re.search(r"_\d{10,}", stem) or re.match(r"^\d{2}_(ia|reply|affidavit)", lower):
        return True

    return False


def sanitize_filename(filename: str, max_chars: int = 70) -> str:
    """Sanitizes a string to be a safe, valid Windows filename."""
    cleaned = re.sub(r'[<>:"/\\|?*\n\r\t!]', "", filename)
    cleaned = re.sub(r"[\s\-_]+", "_", cleaned).strip(" ._")

    if not cleaned:
        cleaned = "Document"

    stem = cleaned[:max_chars].rstrip(" ._")
    return stem


class SmartRenamer:
    """Generates clean, descriptive names for poorly named documents universally."""

    def __init__(self, llm_client: Optional[UnifiedLLMClient] = None):
        self.llm = llm_client or UnifiedLLMClient()

    def local_heuristic_rename(self, item: FileItem) -> Optional[str]:
        """Offline universal rule-based renamer based on text snippet patterns."""
        snippet = item.extract_preview(max_chars=900)
        if not snippet:
            return None

        # Check for HTML title tag
        if item.suffix in [".html", ".htm"]:
            title_match = re.search(r"<title>(.*?)</title>", snippet, re.IGNORECASE | re.DOTALL)
            if title_match:
                title_text = title_match.group(1).strip()
                if title_text and not title_text.lower().startswith("<!doctype"):
                    clean_title = sanitize_filename(title_text)
                    if clean_title:
                        return f"{clean_title}{item.suffix}"

        upper_snippet = snippet.upper()

        # Legal / Tribunal filings
        if "TRIBUNAL" in upper_snippet or "COURT" in upper_snippet:
            oa_match = re.search(r"(?:OA|NO|CASE|APPLICATION)\s*(?:NO\.?|NUMBER)?\s*([0-9]+)", upper_snippet)
            case_tag = f"_Case_{oa_match.group(1)}" if oa_match else ""

            if "JOINT COMMITTEE" in upper_snippet:
                return f"Joint_Committee_Inspection_Report{case_tag}{item.suffix}"
            if "REPLY" in upper_snippet or "COUNTER" in upper_snippet:
                return f"Reply_Affidavit_Filing{case_tag}{item.suffix}"
            if "INTERLOCUTORY" in upper_snippet or "IA NO" in upper_snippet or "I.A. NO" in upper_snippet:
                return f"Interlocutory_Application_Filing{case_tag}{item.suffix}"
            if "AFFIDAVIT" in upper_snippet:
                return f"Affidavit_Legal_Filing{case_tag}{item.suffix}"
            if "HEARING" in upper_snippet or "PROCEEDINGS" in upper_snippet or "ITEM NO" in upper_snippet:
                return f"Hearing_Proceedings_Order{case_tag}{item.suffix}"
            return f"Court_Legal_Filing{case_tag}{item.suffix}"

        # Course Guides
        if "COURSE GUIDE" in upper_snippet or "SYLLABUS" in upper_snippet:
            unit_match = re.search(r"UNIT[\s\-_]*([0-9]+)", upper_snippet)
            unit_str = f"_Unit_{unit_match.group(1)}" if unit_match else ""
            return f"Course_Guide{unit_str}{item.suffix}"

        # Invoices / Financial
        if "INVOICE" in upper_snippet or "BILL TO" in upper_snippet:
            inv_match = re.search(r"INVOICE\s*(?:NO|NUMBER|#)?[:\s]*([A-Za-z0-9\-]+)", upper_snippet)
            inv_num = f"_{inv_match.group(1)[:10]}" if inv_match else ""
            return f"Commercial_Invoice{inv_num}{item.suffix}"

        # Resume / CV
        if "CURRICULUM VITAE" in upper_snippet or "RESUME" in upper_snippet:
            clean_lines = [
                l.strip() for l in snippet.splitlines() 
                if l.strip() and not l.strip().startswith("<") and not l.strip().startswith("{")
            ]
            title_name = sanitize_filename(clean_lines[0]) if clean_lines else "Candidate"
            return f"Resume_{title_name[:25]}{item.suffix}"

        return None

    def batch_ai_rename(self, items: List[FileItem]) -> Dict[str, str]:
        """Batch queries LLM (Gemini or Ollama) to generate clean filenames universally."""
        if not self.llm or not self.llm.is_available or not items:
            return {}

        batch_inputs = []
        for idx, item in enumerate(items):
            preview = item.extract_preview(max_chars=900)
            batch_inputs.append({
                "id": idx,
                "current_name": item.name,
                "extension": item.suffix,
                "text_snippet": preview
            })

        prompt = f"""
You are an intelligent document organizer.
The following documents have messy, machine-generated, generic, or cryptic filenames.
Inspect each document's text snippet and propose a clean, concise, professional filename (PascalCase with underscores, keeping original extension).

Examples:
- "01-15.pdf" (Committee inspection) -> "Joint_Committee_Inspection_Report.pdf"
- "4.docx" (Legal application) -> "Interlocutory_Application_Filing.docx"
- "17866207659991967956a7dab5d41580.pdf" (Hearing order) -> "Court_Hearing_Proceedings_Order.pdf"
- "New Document (1).docx" (Meeting minutes) -> "Project_Sync_Meeting_Minutes.docx"
- "Untitled.pdf" (Invoice) -> "Vendor_Service_Invoice.pdf"

Rules:
1. Max length: 50 characters (excluding extension).
2. Keep the exact original extension.
3. No special characters like < > : " / \\ | ? *.

Files to rename:
{json.dumps(batch_inputs, indent=2)}

Respond with a JSON array where each object has:
- "id": integer matching input id
- "clean_filename": proposed clean filename
- "summary": brief 5-word explanation
"""

        parsed = self.llm.generate_json(prompt)
        if not parsed or not isinstance(parsed, list):
            return {}

        renamed_map = {}
        for entry in parsed:
            idx = entry.get("id")
            clean_name = entry.get("clean_filename")
            if idx is not None and 0 <= idx < len(items) and clean_name:
                item = items[idx]
                stem = Path(clean_name).stem
                final_name = f"{sanitize_filename(stem)}{item.suffix}"
                renamed_map[str(item.path)] = final_name

        return renamed_map
