"""Universal Classifier for NeatPC with Multi-Provider LLM Integration.

Classifies files into clean, logical, and universally applicable categories
for any computer in the world using fast heuristics and Unified LLMs (Gemini / Ollama).
Includes privacy-first safeguards to prevent sensitive documents from leaving the device.
"""

import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from .config import EXTENSION_MAPPINGS, SHORTCUT_CATEGORIES
from .scanner import FileItem
from .analyzer import analyze_file_item, CAT_SHORTCUTS, CAT_DOCUMENTS_GENERAL, DOC_GENERAL
from .llm import UnifiedLLMClient

# Sensitive keywords that must NEVER have content sent to external cloud APIs
SENSITIVE_KEYWORDS = {
    "password", "passwd", "secret", "credential", "api_key", "apikey",
    "private_key", "seed_phrase", "recovery_phrase", "token", "ssn",
    "social_security", "credit_card", "cvv", "bank_statement", "tax_return",
    "w2", "1099", "confidential", "kyc"
}


def is_sensitive_file(item: FileItem) -> bool:
    """Detect if a file name or path suggests confidential/sensitive private data."""
    name_lower = item.name.lower()
    return any(kw in name_lower for kw in SENSITIVE_KEYWORDS)


class Classifier:
    """Classifies files into universal structured destination folders."""

    def __init__(self, use_ai: bool = True, llm_client: Optional[UnifiedLLMClient] = None):
        self.use_ai = use_ai
        self.llm = llm_client or UnifiedLLMClient() if use_ai else None

    def classify_shortcut(self, item: FileItem) -> str:
        """Classify a desktop shortcut (.lnk, .url) into functional categories."""
        lower_stem = item.stem.lower()

        for category, keywords in SHORTCUT_CATEGORIES.items():
            for kw in keywords:
                if kw in lower_stem:
                    return f"Shortcuts/{category}"

        return "Shortcuts/Utilities"

    def rule_based_classify(self, item: FileItem) -> Tuple[str, str]:
        """
        Universal heuristic classification.
        Returns: (category_path, reason)
        """
        if item.is_shortcut:
            return self.classify_shortcut(item), "Application shortcut"

        if is_sensitive_file(item):
            # Route sensitive documents to safe folder without external API calls
            if item.suffix in [".pdf", ".docx", ".doc", ".txt", ".csv"]:
                return "Documents/Finance & Invoices/Confidential & Personal", "Confidential document (protected by local privacy filter)"

        return analyze_file_item(item)

    def classify_batch(self, items: List[FileItem]) -> Dict[str, Tuple[str, str]]:
        """
        Classifies a list of FileItems.
        Returns mapping: { str(item.path): (category_path, reason) }
        """
        results: Dict[str, Tuple[str, str]] = {}
        ai_candidates: List[FileItem] = []

        # Step 1: Fast universal heuristic pass
        for item in items:
            cat, reason = self.rule_based_classify(item)
            results[str(item.path)] = (cat, reason)

            # Collect unclassified documents for deep AI inspection if available
            if (
                self.use_ai 
                and self.llm 
                and self.llm.is_available
                and not item.is_dir 
                and not item.is_shortcut
                and item.suffix in [".pdf", ".docx", ".doc", ".txt", ".csv"]
                and not is_sensitive_file(item)  # Privacy safeguard!
            ):
                if cat == DOC_GENERAL:
                    ai_candidates.append(item)

        # Step 2: Batch AI Semantic Analysis with Gemini / Ollama
        if ai_candidates and self.llm and self.llm.is_available:
            ai_results = self._llm_classify_batch(ai_candidates)
            for path_str, (ai_cat, ai_reason) in ai_results.items():
                provider_tag = self.llm.active_provider.capitalize()
                results[path_str] = (ai_cat, f"{provider_tag}: {ai_reason}")

        return results

    def _llm_classify_batch(self, items: List[FileItem]) -> Dict[str, Tuple[str, str]]:
        """Query LLM to semantically inspect document contents into universal categories."""
        batch_data = []
        for idx, item in enumerate(items):
            preview = item.extract_preview(max_chars=900)
            batch_data.append({
                "id": idx,
                "filename": item.name,
                "text_snippet": preview
            })

        prompt = f"""
You are an intelligent desktop file organizer.
Examine each document's filename and content snippet, and categorize it into the most accurate universal category:
- "Documents/Legal & Contracts/Court Filings & Orders" (court rulings, affidavits, petitions, orders)
- "Documents/Legal & Contracts/Agreements & MOUs" (contracts, agreements, NDAs, MOUs)
- "Documents/Finance & Invoices/Receipts & Invoices" (receipts, bills, commercial invoices)
- "Documents/Finance & Invoices/Bank & Tax Statements" (bank statements, salary slips, tax returns)
- "Documents/Academic & Education/Courses & Syllabi" (course guides, university syllabi, curriculum)
- "Documents/Academic & Education/Lab Records & Handbooks" (lab manuals, practical handbooks)
- "Documents/Career & Resumes/Resumes & CVs" (resumes, CVs, portfolios, job applications)
- "Documents/Career & Resumes/Job Descriptions" (hiring specs, job roles, interview guides)
- "Documents/Technical & Engineering/Specifications & Manuals" (architecture docs, engineering datasheets)
- "Documents/Work & Reports/Meeting Notes" (meeting minutes, action items)
- "Documents/General" (if ambiguous or general)

Documents:
{json.dumps(batch_data, indent=2)}

Respond with a JSON object with a single key "classifications" containing an array of objects:
[
  {{"id": 0, "category": "Documents/Legal & Contracts/Court Filings & Orders", "reason": "Supreme court case ruling text"}}
]
Respond ONLY with the JSON object.
"""
        response_text = self.llm.generate(prompt)
        if not response_text:
            return {}

        try:
            clean_json = response_text.strip()
            if "```json" in clean_json:
                clean_json = clean_json.split("```json")[1].split("```")[0].strip()
            elif "```" in clean_json:
                clean_json = clean_json.split("```")[1].split("```")[0].strip()

            parsed = json.loads(clean_json)
            classifications = parsed.get("classifications", [])
            mapping: Dict[str, Tuple[str, str]] = {}

            for c in classifications:
                cid = c.get("id")
                if cid is not None and 0 <= cid < len(items):
                    item = items[cid]
                    cat = c.get("category", DOC_GENERAL)
                    reason = c.get("reason", "AI content match")
                    mapping[str(item.path)] = (cat, reason)

            return mapping
        except Exception:
            return {}
