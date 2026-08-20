from types import SimpleNamespace

import httpx

from books import vlm


def test_read_book_spine_parses_json_and_passes_api_key(monkeypatch, tmp_path):
    image_path = tmp_path / "book.jpg"
    image_path.write_bytes(b"image")
    captured = {}

    class FakeModels:
        async def generate_content(self, **kwargs):
            captured["request"] = kwargs
            return SimpleNamespace(
                text='{"title": "The Hobbit", "author": "J.R.R. Tolkien"}'
            )

    class FakeClient:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vlm.genai, "Client", FakeClient)

    result = vlm.read_book_spine(image_path)

    assert result == {"title": "The Hobbit", "author": "J.R.R. Tolkien"}
    assert captured["client"]["api_key"] == "test-key"
    assert captured["client"]["http_options"].timeout == 10000
    assert captured["request"]["config"].response_mime_type == "application/json"


def test_read_book_spine_returns_parse_failed_for_malformed_json(monkeypatch, tmp_path):
    image_path = tmp_path / "book.jpg"
    image_path.write_bytes(b"image")

    class FakeModels:
        async def generate_content(self, **kwargs):
            return SimpleNamespace(text="not json")

    class FakeClient:
        def __init__(self, **kwargs):
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vlm.genai, "Client", FakeClient)

    assert vlm.read_book_spine(image_path) == {
        "title": None,
        "author": None,
        "error": "parse_failed",
    }


def test_read_book_spine_returns_timeout_for_api_timeout(monkeypatch, tmp_path):
    image_path = tmp_path / "book.jpg"
    image_path.write_bytes(b"image")

    class FakeModels:
        async def generate_content(self, **kwargs):
            raise httpx.TimeoutException("timed out")

    class FakeClient:
        def __init__(self, **kwargs):
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vlm.genai, "Client", FakeClient)

    assert vlm.read_book_spine(image_path) == {
        "title": None,
        "author": None,
        "error": "timeout",
    }


def test_read_book_spine_returns_timeout_for_gateway_deadline(monkeypatch, tmp_path):
    image_path = tmp_path / "book.jpg"
    image_path.write_bytes(b"image")

    class FakeModels:
        async def generate_content(self, **kwargs):
            raise vlm.genai_errors.ServerError(504, {"error": "deadline"})

    class FakeClient:
        def __init__(self, **kwargs):
            self.aio = SimpleNamespace(models=FakeModels())

    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(vlm.genai, "Client", FakeClient)

    assert vlm.read_book_spine(image_path)["error"] == "timeout"
