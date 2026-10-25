# ✨ NeatPC: Intelligent Desktop & File Automation Workstation

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

**NeatPC** is a high-speed, safety-first desktop and file automation workstation. Inspired by tools like [**`tfeldmann/organize`**](https://github.com/tfeldmann/organize) and [**`midnightdim/declutter`**](https://github.com/midnightdim/declutter), NeatPC elevates file organization by combining **deep content-level inspection (PDF, DOCX, HTML)** with **multi-provider AI (Google Gemini & Local Ollama)**, **cryptographic duplicate quarantine**, **live background watching**, and a **100% reversible undo engine**.

---

## 🌟 Key Capabilities & Upgrades

| Feature | Description |
| :--- | :--- |
| **🧠 Multi-Provider AI (Gemini + Local Ollama)** | Use **Google Gemini Cloud AI** or run **100% offline & private** using **Local Ollama** (`llama3.2`, `mistral`, `phi-3`) with zero data leaving your machine. |
| **🔍 Deep Content Parsing** | Opens and reads internal text snippets of PDFs, Word documents (`.docx`), and HTML title tags to classify files based on what they *actually are* (court rulings, invoices, resumes, syllabi). |
| **⚡ Live Background Watcher Daemon (`--watch`)** | Continuously monitors folders (like `~/Downloads` or `~/Desktop`) and auto-organizes newly downloaded files the moment they finish downloading. |
| **📷 Photo EXIF Camera & Date Sorting** | Reads EXIF tags (Year, Month, Camera Make & Model) to chronologically organize photos into `Media/Pictures/YYYY/MM-Month`. |
| **⚠️ Multi-Stage Duplicate Quarantine** | Uses file-size clustering and SHA-256 byte hashing to isolate duplicate copies into `_Duplicates/`, automatically picking the cleanest master copy to keep. |
| **⚙️ User YAML Configuration (`config.yaml`)** | Easily define your own custom rules, keywords, and extension overrides in `~/.neatpc/config.yaml` without editing code. |
| **🎯 Interactive Action Selection** | When previewing plans, choose between: **[A] Apply All**, **[D] Duplicates Only**, **[R] Renames Only**, or **[S] Specific Category Only**. |
| **🛡️ 100% Reversible Rollback (Undo)** | Full transaction journal recorded at `~/.neatpc/history.json`. Run `python main.py --undo` anytime to restore files to their original names and locations. |

---

## 🆚 Comparison with Popular GitHub File Organizers

| Feature | `tfeldmann/organize` | `midnightdim/declutter` | **✨ NeatPC** |
| :--- | :--- | :--- | :--- |
| **Document Content Reading** | ❌ (Regex only) | ❌ (Filename only) | ✅ **Deep PDF / DOCX parsing** |
| **AI Semantic Understanding** | ❌ None | ❌ None | ✅ **Gemini + Local Ollama** |
| **1-Click Rollback / Undo** | ❌ (Trash only) | ❌ None | ✅ **Full transaction rollback** |
| **Duplicate Quarantine & Scoring** | ⚠️ Basic hash filter | ❌ None | ✅ **SHA-256 + Best master selection** |
| **Desktop Shortcuts (.lnk)** | ❌ None | ❌ None | ✅ **App suites categorization** |
| **Live Background Watcher** | ✅ Yes (`organize run`) | ⚠️ Basic | ✅ **Yes (`--watch`)** |
| **Simulation Mode** | ✅ `organize sim` | ❌ None | ✅ **`python main.py --sim`** |
| **Custom YAML Rules** | ✅ Yes | ❌ GUI only | ✅ **Yes (`~/.neatpc/config.yaml`)** |

---

## 🌐 Universal Clean Taxonomy (Max 2–3 Levels Deep)

```
📁 Organized Root (Desktop, Downloads, or Custom Folder)
├── 📁 _Duplicates/                (Quarantined identical duplicate copies)
├── 📁 Documents/
│   ├── 📁 Legal & Contracts/      (Court Filings, Affidavits, Petitions, Regulatory Notices, MOUs)
│   ├── 📁 Finance & Invoices/     (Receipts, Commercial Bills, Tax Filings, Bank Statements)
│   ├── 📁 Academic & College/     (Course Guides, Syllabi, Lab Handbooks, Timetables, Rosters)
│   ├── 📁 Career & Resumes/       (Professional Resumes, CVs, Portfolios, Summit Proposals)
│   ├── 📁 Work & Reports/         (Meeting Minutes, Technical Specs, Project Briefs)
│   └── 📁 General/                (General documents)
├── 📁 Projects & Code/
│   ├── 📁 Software & Web/         (Web apps, scripts, Python, JS/TS, Java, repos)
│   ├── 📁 Hardware & Electronics/ (Arduino sketches, PCB gerber/schematic files)
│   └── 📁 Hackathons & SIH/       (Hackathon concept decks, problem submissions)
├── 📁 Presentations/              (PowerPoint decks, .pptx, .ppt, .key)
├── 📁 Spreadsheets/               (Excel tables, CSV datasets, .xlsx, .csv)
├── 📁 Shortcuts/                  (Development, Browsers, Creative, AI, Gaming, Utilities)
├── 📁 Media/
│   ├── 📁 Pictures/YYYY/MM/       (Chronological photos sorted via camera EXIF tags)
│   ├── 📁 Screenshots/            (Screen captures)
│   └── 📁 Videos/                 (Recordings, tutorials, MP4, MKV)
├── 📁 Installers/                 (Software setups, .exe, .msi, .iso)
└── 📁 Archives/                   (Zip packages, .zip, .rar, .7z)
```

---

## 🚀 Quickstart & Usage

### 1. Installation

```bash
git clone https://github.com/your-username/neatpc.git
cd neatpc

# Setup virtual environment
python -m venv .venv
.\.venv\Scripts\activate   # Windows
# source .venv/bin/activate # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Interactive Workstation Menu
Double-click `run.bat` or run:
```bash
python main.py
```

### 3. Direct Command Flags

```bash
# Simulation mode: Preview changes without moving any files (like 'organize sim')
python main.py --desktop --sim
python main.py --downloads --sim

# Live background watcher daemon (auto-organize downloads as they finish)
python main.py --watch ~/Downloads

# Organize Desktop files, folders & app shortcuts
python main.py --desktop

# Organize Downloads folder and quarantine duplicate copies
python main.py --downloads

# Organize only specific file types
python main.py --shortcuts    # Desktop app icons only
python main.py --documents    # Documents only (Legal, Finance, Academic, Career)
python main.py --code         # Source code and project repositories only
python main.py --duplicates   # Scan and quarantine duplicate files only
python main.py --rename       # Smart-rename cryptic document filenames

# 1-Click Rollback: Restore files to original locations & original names
python main.py --undo

# View audit history of past organization runs
python main.py --history
```

---

## ⚙️ Custom Configuration (`~/.neatpc/config.yaml`)

NeatPC automatically generates a configuration file at `~/.neatpc/config.yaml`:

```yaml
# AI Provider: 'auto', 'gemini', 'ollama', or 'none'
ai_provider: auto

# Google Gemini Settings
gemini:
  model: "gemini-3.8-flash"
  api_key: ""  # Or export $GEMINI_API_KEY

# Local Ollama Settings (100% private & offline)
ollama:
  endpoint: "http://localhost:11434"
  model: "llama3.2"

# Photo & Video EXIF Sorting
exif_photo_sorting: true

# Custom File Extension Overrides
custom_extensions:
  .torrent: "Downloads/Torrents"
  .blend: "3D Models/Blender"

# Custom Keyword Rules
custom_rules:
  - keyword: "tax"
    destination: "Documents/Finance/Tax"
```

---

## 📄 License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
