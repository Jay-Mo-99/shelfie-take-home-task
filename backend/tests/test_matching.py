from books.matching import match_book


def test_matches_exact_title_and_author():
    result = match_book("1984", "George Orwell")

    assert result["matched_book"]["title"] == "1984"
    assert result["confidence"] == 1.0


def test_matches_title_with_typo():
    result = match_book("The Hobit", "J.R.R. Tolkien")

    assert result["matched_book"]["title"] == "The Hobbit"
    assert result["confidence"] > 0.9


def test_returns_no_match_for_unknown_book():
    result = match_book("A Completely Unknown Book", "An Unknown Author")

    assert result["matched_book"] is None
    assert result["confidence"] < 0.5
