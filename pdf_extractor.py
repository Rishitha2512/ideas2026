"""
pdf_extractor.py
----------------
Extracts clean text from earnings call transcript PDFs.

Features
--------
✓ pdfplumber extraction
✓ pypdf fallback
✓ OCR-ready architecture
✓ Multi-page support
✓ Automatic cleaning
✓ Quarter detection
✓ Company detection
✓ Smart chunking for LLM
"""

from __future__ import annotations

import re
from pathlib import Path

# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def extract_text_from_pdf(
    pdf_path: Path,
    max_pages: int = 80,
) -> str:
    """
    Extract readable text from a PDF.

    Parameters
    ----------
    pdf_path
        Path to PDF.

    max_pages
        Maximum pages to extract.

    Returns
    -------
    str
    """

    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)

    text = _extract_with_pdfplumber(
        pdf_path,
        max_pages=max_pages,
    )

    if len(text.strip()) < 100:
        text = _extract_with_pypdf(
            pdf_path,
            max_pages=max_pages,
        )

    if len(text.strip()) < 100:

        raise ValueError(
            f"Unable to extract readable text from {pdf_path.name}"
        )

    return _clean_text(text)


# -----------------------------------------------------------------------------
# pdfplumber
# -----------------------------------------------------------------------------

def _extract_with_pdfplumber(
    pdf_path: Path,
    max_pages: int,
) -> str:

    try:

        import pdfplumber

    except ImportError:
        return ""

    pages = []

    try:

        with pdfplumber.open(pdf_path) as pdf:

            for page_no, page in enumerate(pdf.pages):

                if page_no >= max_pages:
                    break

                text = page.extract_text(
                    x_tolerance=3,
                    y_tolerance=3,
                )

                if not text:
                    continue

                pages.append(
                    f"\n\n--- Page {page_no+1} ---\n\n{text}"
                )

    except Exception as e:

        print(f"[pdfplumber] {e}")

        return ""

    return "\n".join(pages)


# -----------------------------------------------------------------------------
# pypdf
# -----------------------------------------------------------------------------

def _extract_with_pypdf(
    pdf_path: Path,
    max_pages: int,
) -> str:

    try:

        from pypdf import PdfReader

    except ImportError:
        return ""

    pages = []

    try:

        reader = PdfReader(str(pdf_path))

        for page_no, page in enumerate(reader.pages):

            if page_no >= max_pages:
                break

            text = page.extract_text()

            if not text:
                continue

            pages.append(
                f"\n\n--- Page {page_no+1} ---\n\n{text}"
            )

    except Exception as e:

        print(f"[pypdf] {e}")

        return ""

    return "\n".join(pages)
# -----------------------------------------------------------------------------
# Cleaning
# -----------------------------------------------------------------------------

UNICODE_REPLACEMENTS = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "--",
        "\u00A0": " ",
    }
)

NOISE_PATTERNS = [

    re.compile(r"Page\s+\d+\s+of\s+\d+", re.I),

    re.compile(
        r"This transcript has been edited",
        re.I,
    ),

    re.compile(
        r"Strictly Confidential",
        re.I,
    ),

    re.compile(
        r"\[inaudible\]",
        re.I,
    ),

    re.compile(
        r"\[crosstalk\]",
        re.I,
    ),

    re.compile(
        r"\x00",
    ),

    re.compile(
        r"^\s*\d+\s*$",
        re.M,
    ),
]


def _clean_text(text: str) -> str:
    """
    Remove common PDF artefacts.
    """

    text = text.translate(
        UNICODE_REPLACEMENTS
    )

    for pattern in NOISE_PATTERNS:
        text = pattern.sub("", text)

    # Remove trailing spaces
    text = "\n".join(
        line.rstrip()
        for line in text.splitlines()
    )

    # Collapse long blank regions
    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    # Collapse spaces
    text = re.sub(
        r"[ \t]{2,}",
        " ",
        text,
    )

    return text.strip()


# -----------------------------------------------------------------------------
# Quarter Detection
# -----------------------------------------------------------------------------

def detect_quarter_from_text(
    text: str,
) -> str | None:
    """
    Detect quarter like Q3FY25.
    """

    sample = text[:4000]

    patterns = [

        r"(Q[1-4])\s*FY\s*(\d{2,4})",

        r"(Q[1-4])\s*(\d{2,4})",

        r"(first|second|third|fourth)\s+quarter.*?(\d{4})",

        r"([1-4])(st|nd|rd|th)\s+quarter.*?(\d{4})",

    ]

    names = {

        "first": "Q1",
        "second": "Q2",
        "third": "Q3",
        "fourth": "Q4",

    }

    for pattern in patterns:

        m = re.search(
            pattern,
            sample,
            re.I | re.S,
        )

        if not m:
            continue

        if m.group(1).lower() in names:

            quarter = names[m.group(1).lower()]
            year = m.group(2)

        elif m.group(1).upper().startswith("Q"):

            quarter = m.group(1).upper()
            year = m.group(2)

        else:

            quarter = "Q" + m.group(1)
            year = m.group(3)

        if len(year) == 4:
            year = year[-2:]

        return f"{quarter}FY{year}"

    return None


# -----------------------------------------------------------------------------
# Company Detection
# -----------------------------------------------------------------------------

def detect_company_from_text(
    text: str,
) -> str | None:
    """
    Try extracting company name from first pages.
    """

    sample = text[:3000]

    pattern = (
        r"([A-Z][A-Za-z0-9&.,\- ]+?)\s+"
        r"(?:Limited|Ltd|Technologies|Technology|Industries|"
        r"Corporation|Holdings|Bank|Finance)"
    )

    m = re.search(
        pattern,
        sample,
    )

    if m:

        return (
            m.group(1).strip()
            + " "
            + sample[m.end()-8:m.end()].strip()
        )

    return None
# -----------------------------------------------------------------------------
# Batch Extraction
# -----------------------------------------------------------------------------

def extract_from_paths(
    pdf_paths: list[Path],
    quarter_hints: list[str] | None = None,
) -> list[dict]:
    """
    Extract text from multiple PDF files.

    Returns
    -------
    list[dict]
    """

    results = []

    for index, pdf_path in enumerate(pdf_paths):

        pdf_path = Path(pdf_path)

        hint = None

        if (
            quarter_hints
            and index < len(quarter_hints)
        ):
            hint = quarter_hints[index]

        try:

            text = extract_text_from_pdf(pdf_path)

            quarter = (
                hint
                or detect_quarter_from_text(text)
                or f"Q{index+1}_Unknown"
            )

            results.append(
                {
                    "pdf_path": pdf_path,
                    "quarter": quarter,
                    "text": text,
                    "pages": text.count("--- Page"),
                    "error": None,
                }
            )

            print(
                f"✓ {pdf_path.name} "
                f"({quarter}) "
                f"{len(text):,} chars"
            )

        except Exception as e:

            results.append(
                {
                    "pdf_path": pdf_path,
                    "quarter": hint or f"Q{index+1}",
                    "text": "",
                    "pages": 0,
                    "error": str(e),
                }
            )

            print(f"✗ {pdf_path.name}: {e}")

    return results


# -----------------------------------------------------------------------------
# Manual Mode (used by main.py)
# -----------------------------------------------------------------------------

def load_manual_pdfs(
    pdf_files: list[str],
) -> list[dict]:
    """
    Used by:

        python main.py --manual a.pdf b.pdf

    Returns transcript dictionaries expected by llm_analyser.
    """

    paths = [Path(p) for p in pdf_files]

    extracted = extract_from_paths(paths)

    transcripts = []

    for item in extracted:

        if item["error"]:
            continue

        transcripts.append(
            {
                "quarter": item["quarter"],
                "source": "Manual PDF",
                "pdf_path": item["pdf_path"],
                "text": smart_chunk(item["text"]),
            }
        )

    return transcripts


# -----------------------------------------------------------------------------
# Auto Fetch Mode (used by main.py)
# -----------------------------------------------------------------------------

def enrich_with_text(
    metadata: list[dict],
) -> list[dict]:
    """
    Convert fetcher output into transcript objects.

    Input
    -----
    [
        {
            "quarter": "...",
            "pdf_path": Path(...),
            ...
        }
    ]

    Output
    ------
    Same dictionaries with extracted text added.
    """

    transcripts = []

    for item in metadata:

        try:

            text = extract_text_from_pdf(
                item["pdf_path"]
            )

            record = dict(item)

            record["text"] = smart_chunk(text)

            transcripts.append(record)

            print(
                f"✓ Extracted {item['quarter']} "
                f"({len(text):,} chars)"
            )

        except Exception as e:

            print(
                f"✗ Failed {item['pdf_path'].name}: {e}"
            )

    return transcripts
# -----------------------------------------------------------------------------
# Smart Chunking
# -----------------------------------------------------------------------------

def smart_chunk(
    text: str,
    max_chars: int = 80000,
) -> str:
    """
    Reduce transcript size while preserving the most useful
    sections for LLM analysis.

    Strategy
    --------
    1. Keep opening management discussion.
    2. Keep complete Q&A if possible.
    3. Otherwise keep first + last portions.
    """

    if len(text) <= max_chars:
        return text

    lower = text.lower()

    qa_markers = [
        "question and answer",
        "q&a",
        "question-and-answer",
        "operator:",
        "moderator:",
        "we will now begin the question",
    ]

    qa_start = -1

    for marker in qa_markers:

        idx = lower.find(marker)

        if idx > len(text) * 0.20:
            qa_start = idx
            break

    if qa_start == -1:

        half = max_chars // 2

        return (
            text[:half]
            + "\n\n"
            + "[ ... CONTENT TRUNCATED ... ]"
            + "\n\n"
            + text[-half:]
        )

    opening_budget = int(max_chars * 0.45)

    qa_budget = max_chars - opening_budget - 200

    opening = text[:opening_budget]

    qa = text[
        qa_start:
        qa_start + qa_budget
    ]

    return (
        opening
        + "\n\n"
        + "[ ... MANAGEMENT DISCUSSION TRUNCATED ... ]"
        + "\n\n"
        + qa
    )
# ───────────────────────────────────────────────────────────
# Helper functions used by main.py
# ───────────────────────────────────────────────────────────

from pathlib import Path


def load_manual_pdfs(pdf_paths):
    """
    Load PDFs supplied manually through the CLI.

    Returns:
        [
            {
                "quarter": "...",
                "pdf_path": Path(...),
                "text": "...",
                "source": "Manual"
            }
        ]
    """
    transcripts = []

    for path in pdf_paths:
        path = Path(path)

        if not path.exists():
            print(f"❌ PDF not found: {path}")
            continue

        try:
            text = extract_text_from_pdf(path)

            quarter = (
                detect_quarter_from_text(text)
                or path.stem
            )

            transcripts.append(
                {
                    "quarter": quarter,
                    "pdf_path": path,
                    "text": smart_chunk(text),
                    "source": "Manual",
                }
            )

        except Exception as e:
            print(f"❌ Failed to load {path.name}: {e}")

    return transcripts
from pathlib import Path

PDF_ROOT = Path("pdfs")


def get_company_folder(company_name: str) -> Path | None:
    """
    Find matching company folder (case-insensitive).
    """
    company_name = company_name.lower().strip()

    for folder in PDF_ROOT.iterdir():
        if folder.is_dir() and folder.name.lower() == company_name:
            return folder

    return None
def load_company_pdfs(company_name: str):
    """
    Load all PDFs from a company folder.
    """

    folder = get_company_folder(company_name)

    if not folder:
        raise ValueError(f"No folder found for company: {company_name}")

    pdf_files = list(folder.glob("*.pdf"))

    if not pdf_files:
        raise ValueError(f"No PDFs found in folder: {folder}")

    return load_manual_pdfs([str(p) for p in pdf_files])


def enrich_with_text(metadata):
    """
    Takes metadata returned by fetcher.fetch_concalls()
    and appends extracted transcript text.

    Input:
        [
            {
                "quarter": "...",
                "pdf_path": Path(...),
                ...
            }
        ]

    Output:
        [
            {
                "quarter": "...",
                "pdf_path": Path(...),
                "text": "...",
                ...
            }
        ]
    """

    enriched = []

    for item in metadata:

        pdf_path = Path(item["pdf_path"])

        try:
            text = extract_text_from_pdf(pdf_path)

            new_item = dict(item)
            new_item["text"] = smart_chunk(text)

            enriched.append(new_item)

        except Exception as e:
            print(f"❌ Could not read {pdf_path.name}: {e}")

    return enriched



# -----------------------------------------------------------------------------
# CLI Test
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    import sys

    if len(sys.argv) < 2:

        print(
            "Usage:\n"
            "python pdf_extractor.py transcript.pdf"
        )

        raise SystemExit(1)

    pdf = Path(sys.argv[1])

    text = extract_text_from_pdf(pdf)

    print("=" * 70)
    print("PDF EXTRACTION TEST")
    print("=" * 70)

    print(f"Characters : {len(text):,}")

    print(
        "Quarter :",
        detect_quarter_from_text(text),
    )

    print(
        "Company :",
        detect_company_from_text(text),
    )

    print("\nFirst 1000 characters\n")
    print("-" * 70)
    print(text[:1000])