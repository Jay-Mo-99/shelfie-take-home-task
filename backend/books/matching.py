"""
matching.py

Matches VLM-extracted book text (title, author) against catalog.csv
to find the most likely catalog entry, using fuzzy string matching.

NOTE on the two different thresholds used in this pipeline:
  - The 70/30 WEIGHTING below is a FORMULA used once, to combine
    title_score and author_score into a single confidence number.

  - The 85/60 THRESHOLDS (used later, in the /api/scan/ view) are
    DECISION RULES applied AFTER confidence is already calculated,
    to decide what the app should DO with that score
    (auto-save / send to review / treat as no match).

"""

import csv
import re
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog.csv"
MATCH_THRESHOLD = 0.5


def _normalize(value):
    normalized = unicodedata.normalize("NFKD", value or "")
    normalized = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()


def _title_score(input_title, catalog_title, alternate_titles):
    candidates = [catalog_title]
    candidates.extend(
        alternate_title.strip()
        for alternate_title in (alternate_titles or "").split(";")
        if alternate_title.strip()
    )
    return max(
        fuzz.token_set_ratio(_normalize(input_title), _normalize(candidate))
        for candidate in candidates
    )


def match_book(title, author, catalog_path=CATALOG_PATH):
    """
    Find the best matching catalog entry for a book read by the VLM.

    Step 1: Compute title_score — fuzzy similarity between the input
            title and each catalog row's title + alternate_titles.
    Step 2: Compute author_score — fuzzy similarity between the input
            author and each catalog row's author.
    Step 3: Combine into one confidence score using a weighted average:
            confidence = (title_score * 0.7) + (author_score * 0.3)
            (Title is weighted higher because it's usually longer and
            more distinctive than author names, which collide more often.)
    Step 4: If confidence is below 0.5, we consider the best candidate
            too unreliable to even suggest — return matched_book=None.
            (This is a "floor" check, separate from the 85/60 tiers
            used downstream to decide auto-save vs. review.)

    Returns:
        {
            "matched_book": {...} or None,
            "confidence": float (0.0 - 1.0),
            "title_score": float,
            "author_score": float,
        }
    """
    normalized_title = _normalize(title)
    normalized_author = _normalize(author)
    best_match = None
    best_scores = (0.0, 0.0, 0.0)

    with Path(catalog_path).open(newline="", encoding="utf-8") as catalog_file:
        for entry in csv.DictReader(catalog_file):
            title_score = _title_score(
                normalized_title,
                entry.get("title", ""),
                entry.get("alternate_titles", ""),
            )
            author_score = fuzz.token_set_ratio(
                normalized_author,
                _normalize(entry.get("author", "")),
            )
            confidence = (title_score * 0.7 + author_score * 0.3) / 100
            if confidence > best_scores[0]:
                best_match = entry
                best_scores = (confidence, title_score, author_score)

    confidence, title_score, author_score = best_scores
    return {
        "matched_book": best_match if confidence >= MATCH_THRESHOLD else None,
        "confidence": round(confidence, 4),
        "title_score": round(title_score / 100, 4),
        "author_score": round(author_score / 100, 4),
    }
