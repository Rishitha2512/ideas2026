"""
utils.py
---------

Common utility functions used throughout the project.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


# =============================================================================
# Date Helpers
# =============================================================================

_DATE_FORMATS = (
    "%Y%m%d",
    "%Y-%m-%d",
    "%Y-%m-%dT%H:%M:%S",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%d %b %Y",
    "%d %B %Y",
)


def parse_date(date_str: str | None) -> datetime | None:
    """Parse a date using several common formats."""
    if not date_str:
        return None

    date_str = date_str.strip()

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(date_str, fmt)
        except Exception:
            continue

    return None


# =============================================================================
# Quarter Helpers
# =============================================================================

_QUARTER_REGEX = re.compile(
    r"(Q[1-4])\s*[- ]*\s*(FY)?\s*(\d{2,4})",
    re.IGNORECASE,
)


def detect_quarter(text: str) -> str | None:
    """
    Detect quarter like Q3FY25 from text.
    """

    m = _QUARTER_REGEX.search(text)

    if not m:
        return None

    q = m.group(1).upper()
    year = m.group(3)

    if len(year) == 4:
        year = year[-2:]

    return f"{q}FY{year}"


# =============================================================================
# Text Helpers
# =============================================================================

def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace."""

    text = text.replace("\r", "")

    text = re.sub(r"[ \t]+", " ", text)

    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def remove_control_characters(text: str) -> str:
    """Remove null bytes and other control chars."""

    return re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)


def clean_text(text: str) -> str:
    """
    Clean transcript text.
    """

    text = remove_control_characters(text)

    text = normalize_whitespace(text)

    return text


# =============================================================================
# JSON Helpers
# =============================================================================

def safe_json_loads(text: str) -> dict:
    """
    Parse JSON safely.

    Claude sometimes wraps JSON inside markdown.
    """

    text = text.strip()

    if text.startswith("```json"):
        text = text.replace("```json", "", 1)

    if text.startswith("```"):
        text = text.replace("```", "", 1)

    if text.endswith("```"):
        text = text[:-3]

    text = text.strip()

    return json.loads(text)


def write_json(path: Path, data: Any) -> None:

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=2,
            ensure_ascii=False,
        )


def read_json(path: Path) -> Any:

    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =============================================================================
# Cache Helpers
# =============================================================================

def hash_string(text: str) -> str:
    """
    MD5 hash of string.
    """

    return hashlib.md5(
        text.encode("utf-8")
    ).hexdigest()


def cache_exists(path: Path) -> bool:

    return path.exists() and path.is_file()


# =============================================================================
# File Helpers
# =============================================================================

def ensure_directory(path: Path) -> None:

    path.mkdir(
        parents=True,
        exist_ok=True,
    )


def file_size_mb(path: Path) -> float:

    return path.stat().st_size / (1024 * 1024)


# =============================================================================
# Retry Decorator
# =============================================================================

def retry(
    retries: int = 3,
    delay: int = 3,
):
    """
    Retry decorator.

    Example:

    @retry()
    def func():
        ...
    """

    def decorator(func: Callable):

        @wraps(func)
        def wrapper(*args, **kwargs):

            last_error = None

            for attempt in range(1, retries + 1):

                try:
                    return func(*args, **kwargs)

                except Exception as e:

                    last_error = e

                    logger.warning(
                        "Attempt %d/%d failed: %s",
                        attempt,
                        retries,
                        e,
                    )

                    if attempt < retries:
                        time.sleep(delay)

            raise last_error

        return wrapper

    return decorator


# =============================================================================
# Logging Helpers
# =============================================================================

def banner(title: str) -> str:

    line = "=" * 70

    return f"\n{line}\n{title}\n{line}\n"


def log_exception(e: Exception) -> None:

    logger.exception(str(e))


# =============================================================================
# Statistics
# =============================================================================

def percentage(part: float, whole: float) -> float:

    if whole == 0:
        return 0.0

    return round((part / whole) * 100, 2)


# =============================================================================
# Transcript Helpers
# =============================================================================

def transcript_summary(text: str) -> dict:
    """
    Returns quick transcript statistics.
    """

    words = text.split()

    return {
        "characters": len(text),
        "words": len(words),
        "lines": len(text.splitlines()),
    }


# =============================================================================
# Sorting
# =============================================================================

def sort_by_date(items: list[dict]) -> list[dict]:
    """
    Sort list of dictionaries by 'date' descending.
    """

    def key(item):

        d = parse_date(item.get("date"))

        if d is None:
            return datetime.min

        return d

    return sorted(
        items,
        key=key,
        reverse=True,
    )


# =============================================================================
# CLI Test
# =============================================================================

if __name__ == "__main__":

    print(detect_quarter("Infosys Q3 FY25 Earnings Call"))

    print(parse_date("2025-01-15"))

    print(
        transcript_summary(
            "Hello world\nThis is a transcript."
        )
    )