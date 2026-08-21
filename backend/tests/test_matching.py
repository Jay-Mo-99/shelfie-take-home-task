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


def test_same_title_with_unknown_author_is_ambiguous():
    result = match_book("The Stranger", None)

    assert result["ambiguous"] is True
    assert result["matched_book"] is None
    assert len(result["candidates"]) == 2
    assert {candidate["author"] for candidate in result["candidates"]} == {
        "Albert Camus",
        "Harlan Coben",
    }


def test_substring_title_does_not_match_longer_title():
    # "It" should not fuzzy-match into "It Ends with Us"
    result = match_book("It", "Stephen King")

    assert result["matched_book"]["title"] == "It"
    assert result["confidence"] > 0.9


def test_matches_author_name_in_different_form():
    # catalog has "Fyodor Dostoyevsky"; VLM read a different transliteration
    result = match_book("The Brothers Karamazov", "Fyodor Dostoevsky")

    assert result["matched_book"]["title"] == "The Brothers Karamazov"
    assert result["confidence"] > 0.7
