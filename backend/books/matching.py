"""Match VLM-extracted book text against the local catalog."""

import csv
import re
import unicodedata
from pathlib import Path

from rapidfuzz import fuzz

CATALOG_PATH = Path(__file__).resolve().parents[2] / "catalog.csv"
AUTO_SAVE_THRESHOLD = 0.85
REVIEW_THRESHOLD = 0.5
AMBIGUITY_MARGIN = 0.05
MAX_CANDIDATES = 3


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
    Candidates within AMBIGUITY_MARGIN of the best score are returned for
    human review instead of selecting one arbitrarily.

    Returns:
        {
            "matched_book": {...} or None,
            "confidence": float (0.0 - 1.0),
            "title_score": float,
            "author_score": float,
            "ambiguous": bool,
            "candidates": [...],
        }
    """
    normalized_title = _normalize(title)
    normalized_author = _normalize(author)
    scored_entries = []

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
            scored_entries.append(
                {
                    "entry": entry,
                    "confidence": confidence,
                    "title_score": title_score / 100,
                    "author_score": author_score / 100,
                }
            )

    scored_entries.sort(key=lambda item: item["confidence"], reverse=True)
    best = scored_entries[0] if scored_entries else None
    confidence = best["confidence"] if best else 0.0
    candidates = [
        item
        for item in scored_entries
        if confidence - item["confidence"] <= AMBIGUITY_MARGIN
    ][:MAX_CANDIDATES]
    distinct_authors = []
    for item in candidates:
        author = _normalize(item["entry"].get("author", ""))
        if not any(
            fuzz.token_set_ratio(author, known_author) >= 95
            for known_author in distinct_authors
        ):
            distinct_authors.append(author)
    ambiguous = len(candidates) > 1 and len(distinct_authors) > 1
    matched_book = None
    if best and confidence >= REVIEW_THRESHOLD and not ambiguous:
        matched_book = best["entry"]

    return {
        "matched_book": matched_book,
        "confidence": round(confidence, 4),
        "title_score": round(best["title_score"], 4) if best else 0.0,
        "author_score": round(best["author_score"], 4) if best else 0.0,
        "ambiguous": ambiguous,
        "candidates": [
            {
                **item["entry"],
                "confidence": round(item["confidence"], 4),
                "title_score": round(item["title_score"], 4),
                "author_score": round(item["author_score"], 4),
            }
            for item in candidates
        ],
    }
