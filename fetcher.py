"""
fetcher.py
----------
Auto-fetches concall transcripts / investor presentation PDFs for a given
company from two public sources:

1. BSE India
2. Screener.in

Returns:
[
    {
        "quarter": "...",
        "source": "...",
        "pdf_path": "...",
        "url": "...",
        "date": "..."
    }
]
"""

from __future__ import annotations

import hashlib
import re
import tempfile
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)

DOWNLOAD_DIR = Path(tempfile.gettempdir()) / "concall_pdfs"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


# -----------------------------------------------------------------------------
# Utility Functions
# -----------------------------------------------------------------------------

def _is_concall_related(text: str) -> bool:
    """
    Check whether announcement title appears related to
    earnings call / analyst meet / investor presentation.
    """

    if not text:
        return False

    text = text.lower()

    keywords = [
        "conference call",
        "concall",
        "con call",
        "earnings call",
        "earnings conference",
        "analyst",
        "investor",
        "transcript",
        "presentation",
        "investor meet",
        "conference",
        "q1",
        "q2",
        "q3",
        "q4",
        "quarterly",
        "results",
    ]

    return any(k in text for k in keywords)


def _infer_quarter(subject: str, date_string: str = "") -> str:
    """
    Infer quarter like Q3FY25.
    """

    m = re.search(
        r"(Q[1-4])\s*[- ]?\s*(FY\s*\d{2,4})",
        subject,
        re.I,
    )

    if m:
        q = m.group(1).upper()
        fy = m.group(2).replace(" ", "").upper()

        if fy.startswith("FY20"):
            fy = "FY" + fy[-2:]

        return q + fy

    m = re.search(r"(Q[1-4])\s+(\d{4})", subject, re.I)

    if m:
        return f"{m.group(1).upper()}FY{m.group(2)[2:]}"

    if date_string:

        try:

            for fmt in (
                "%Y%m%d",
                "%Y-%m-%d",
                "%d/%m/%Y",
                "%d %b %Y",
                "%Y-%m-%dT%H:%M:%S",
            ):

                try:
                    d = datetime.strptime(date_string[:19], fmt)
                    break
                except Exception:
                    continue
            else:
                return "Unknown"

            month = d.month
            year = d.year

            if month in (4, 5, 6):
                q = "Q1"
                fy = year + 1

            elif month in (7, 8, 9):
                q = "Q2"
                fy = year + 1

            elif month in (10, 11, 12):
                q = "Q3"
                fy = year + 1

            else:
                q = "Q4"
                fy = year

            return f"{q}FY{str(fy)[2:]}"

        except Exception:
            pass

    return "Unknown"


# -----------------------------------------------------------------------------
# BSE Search
# -----------------------------------------------------------------------------

def _bse_search(company: str) -> str | None:
    """
    Resolve company name to BSE scrip code.
    """

    if company.isdigit():
        return company

    url = "https://api.bseindia.com/BseIndiaAPI/api/AutoCompletelist/w"

    params = {
        "text": company,
        "type": "0",
        "flag": "0",
    }

    try:

        r = SESSION.get(
            url,
            params=params,
            timeout=20,
        )

        r.raise_for_status()

        data = r.json()

        if data:

            code = (
                data[0].get("scripcode")
                or data[0].get("Scripcode")
            )

            if code:
                return str(code)

    except Exception as e:
        print(f"[BSE Search] {e}")

    return None
# -----------------------------------------------------------------------------
# BSE Announcements
# -----------------------------------------------------------------------------

def _bse_announcements(
    scrip_code: str,
    max_results: int = 25,
) -> list[dict]:
    """
    Fetch corporate announcements from BSE and filter
    concall / analyst related documents.
    """

    url = (
        "https://api.bseindia.com/"
        "BseIndiaAPI/api/AnnSubCategoryGetData/w"
    )

    params = {
        "pageno": "1",
        "strCat": "-1",
        "strPrevDate": "20200101",
        "strScrip": scrip_code,
        "strSearch": "P",
        "strToDate": datetime.today().strftime("%Y%m%d"),
        "strType": "C",
        "subcategory": "-1",
    }

    results = []

    try:

        r = SESSION.get(
            url,
            params=params,
            timeout=25,
        )

        r.raise_for_status()

        data = r.json()

        announcements = data.get("Table", [])

        for ann in announcements:

            subject = ann.get("NEWSSUB", "").strip()

            if not _is_concall_related(subject):
                continue

            attachment = ann.get("ATTACHMENTNAME", "")
            newsid = ann.get("NEWSID", "")

            if attachment:

                pdf_url = (
                    "https://www.bseindia.com/"
                    "xml-data/corpfiling/AttachLive/"
                    + attachment
                )

            elif newsid:

                pdf_url = (
                    "https://www.bseindia.com/"
                    f"corporates/ann.html?newsid={newsid}"
                )

            else:
                continue

            results.append(
                {
                    "subject": subject,
                    "url": pdf_url,
                    "date": ann.get("NEWS_DT", ""),
                    "source": "BSE",
                }
            )

            if len(results) >= max_results:
                break

    except Exception as e:
        print(f"[BSE Announcements] {e}")

    return results


# -----------------------------------------------------------------------------
# Screener.in
# -----------------------------------------------------------------------------

def _screener_fetch(
    company: str,
    max_results: int = 15,
) -> list[dict]:
    """
    Fetch transcript links from Screener.in
    """

    company = company.upper().strip()

    urls = [
        f"https://www.screener.in/company/{company}/",
        f"https://www.screener.in/company/{company}/consolidated/",
    ]

    results = []

    for page_url in urls:

        try:

            r = SESSION.get(
                page_url,
                timeout=20,
            )

            if r.status_code == 404:
                continue

            r.raise_for_status()

            soup = BeautifulSoup(
                r.text,
                "lxml",
            )

            section = (
                soup.find("section", id="documents")
                or soup.find("div", class_="documents")
                or soup
            )

            links = section.find_all(
                "a",
                href=True,
            )

            for link in links:

                href = link["href"]

                text = link.get_text(
                    " ",
                    strip=True,
                )

                if (
                    not _is_concall_related(text)
                    and not _is_concall_related(href)
                ):
                    continue

                if href.startswith("http"):
                    full_url = href
                else:
                    full_url = urllib.parse.urljoin(
                        "https://www.screener.in",
                        href,
                    )

                parent = (
                    link.find_parent("li")
                    or link.find_parent("div")
                    or link.find_parent("tr")
                )

                date_text = ""

                if parent:

                    m = re.search(
                        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{4}",
                        parent.get_text(" ", strip=True),
                    )

                    if m:
                        date_text = m.group(0)

                results.append(
                    {
                        "subject": text,
                        "url": full_url,
                        "date": date_text,
                        "source": "Screener",
                    }
                )

                if len(results) >= max_results:
                    break

            if results:
                break

        except Exception as e:
            print(f"[Screener] {e}")

    return results
# -----------------------------------------------------------------------------
# PDF Downloader
# -----------------------------------------------------------------------------

def _download_pdf(
    url: str,
    filename_hint: str = "",
) -> Path | None:
    """
    Download a PDF and save it locally.

    Returns
    -------
    Path | None
    """

    try:

        response = SESSION.get(
            url,
            stream=True,
            timeout=40,
        )

        response.raise_for_status()

        content_type = response.headers.get(
            "Content-Type",
            "",
        ).lower()

        # Validate PDF
        if (
            "pdf" not in content_type
            and not url.lower().endswith(".pdf")
        ):

            first_chunk = b""

            for chunk in response.iter_content(1024):
                first_chunk = chunk
                break

            if not first_chunk.startswith(b"%PDF"):
                print(f"Skipping non-PDF: {url}")
                return None

            response = SESSION.get(
                url,
                timeout=40,
            )

            response.raise_for_status()

        safe_name = re.sub(
            r"[^\w]+",
            "_",
            filename_hint,
        )[:40]

        url_hash = hashlib.md5(
            url.encode("utf-8")
        ).hexdigest()[:8]

        output_file = (
            DOWNLOAD_DIR /
            f"{safe_name}_{url_hash}.pdf"
        )

        if output_file.exists():
            return output_file

        with open(output_file, "wb") as fp:

            for chunk in response.iter_content(8192):

                if chunk:
                    fp.write(chunk)

        return output_file

    except Exception as e:

        print(f"[Downloader] {e}")

        return None


# -----------------------------------------------------------------------------
# Sorting Helper
# -----------------------------------------------------------------------------

def _sort_key(item: dict):

    date_text = item.get(
        "date",
        "",
    )

    formats = [

        "%Y%m%d",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%d/%m/%Y",
        "%d %b %Y",

    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                date_text[:19],
                fmt,
            )
        except Exception:
            pass

    return datetime.min


# -----------------------------------------------------------------------------
# Remove Duplicate URLs
# -----------------------------------------------------------------------------

def _deduplicate(items: list[dict]) -> list[dict]:

    seen = set()

    cleaned = []

    for item in items:

        url = item.get("url")

        if not url:
            continue

        if url in seen:
            continue

        seen.add(url)

        cleaned.append(item)

    return cleaned
# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def fetch_concalls(
    company_name_or_code: str,
    max_quarters: int = 5,
    verbose: bool = True,
) -> list[dict]:
    """
    Fetch the latest concall / earnings call PDFs.

    Parameters
    ----------
    company_name_or_code : str
        NSE symbol, company name or BSE scrip code.

    max_quarters : int
        Maximum number of PDFs to download.

    verbose : bool
        Print progress messages.

    Returns
    -------
    list[dict]
    """

    if verbose:
        print(f"\nSearching concalls for: {company_name_or_code}")

    raw_results: list[dict] = []

    # ------------------------------------------------------------------
    # Source 1 : BSE
    # ------------------------------------------------------------------

    scrip_code = _bse_search(company_name_or_code)

    if scrip_code:

        if verbose:
            print(f"BSE scrip code : {scrip_code}")

        bse_results = _bse_announcements(
            scrip_code,
            max_results=30,
        )

        if verbose:
            print(f"BSE results : {len(bse_results)}")

        raw_results.extend(bse_results)

        time.sleep(0.5)

    else:

        if verbose:
            print("Unable to resolve BSE scrip code.")

    # ------------------------------------------------------------------
    # Source 2 : Screener
    # ------------------------------------------------------------------

    screener_results = _screener_fetch(
        company_name_or_code,
        max_results=20,
    )

    if verbose:
        print(f"Screener results : {len(screener_results)}")

    raw_results.extend(screener_results)

    # ------------------------------------------------------------------
    # Nothing found
    # ------------------------------------------------------------------

    if not raw_results:

        if verbose:
            print("No transcripts found.")

        return []

    # ------------------------------------------------------------------
    # Remove duplicate URLs
    # ------------------------------------------------------------------

    raw_results = _deduplicate(raw_results)

    # ------------------------------------------------------------------
    # Sort newest first
    # ------------------------------------------------------------------

    raw_results.sort(
        key=_sort_key,
        reverse=True,
    )

    final_results: list[dict] = []

    # ------------------------------------------------------------------
    # Download PDFs
    # ------------------------------------------------------------------

    for item in raw_results:

        if len(final_results) >= max_quarters:
            break

        quarter = _infer_quarter(
            item.get("subject", ""),
            item.get("date", ""),
        )

        filename_hint = (
            f"{company_name_or_code}_{quarter}"
        )

        if verbose:
            print(f"Downloading : {item['subject']}")

        pdf_path = _download_pdf(
            item["url"],
            filename_hint,
        )

        if pdf_path is None:

            if verbose:
                print("Download failed.")

            continue

        final_results.append(
            {
                "quarter": quarter,
                "subject": item["subject"],
                "source": item["source"],
                "pdf_path": pdf_path,
                "url": item["url"],
                "date": item["date"],
            }
        )

        time.sleep(0.25)

    if verbose:
        print(
            f"\nDownloaded {len(final_results)} transcript(s)."
        )

    return final_results
# -----------------------------------------------------------------------------
# CLI Test
# -----------------------------------------------------------------------------

if __name__ == "__main__":

    import json
    import sys

    if len(sys.argv) > 1:
        company = sys.argv[1]
    else:
        company = "INFY"

    print("=" * 70)
    print("Concall Fetcher Test")
    print("=" * 70)

    results = fetch_concalls(
        company_name_or_code=company,
        max_quarters=5,
        verbose=True,
    )

    print("\n")
    print("=" * 70)
    print(f"Fetched {len(results)} transcript(s)")
    print("=" * 70)

    for index, item in enumerate(results, start=1):

        print(f"\nTranscript {index}")

        print(
            json.dumps(
                {
                    key: str(value)
                    for key, value in item.items()
                },
                indent=4,
            )
        )

    print("\nDone.")