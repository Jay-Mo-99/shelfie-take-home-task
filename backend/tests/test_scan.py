from io import BytesIO
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient
from unittest.mock import patch


def test_scan_runs_detection_vlm_and_matching_in_order(monkeypatch):
    calls = []

    def fake_detect(image_path):
        calls.append("detect")
        return [{"bbox": [0, 0, 20, 40], "confidence": 0.9}]

    def fake_crop(image_path, detections, output_dir):
        calls.append("crop")
        output_dir.mkdir(parents=True, exist_ok=True)
        crop_path = output_dir / "scan_book_01.jpg"
        Image.new("RGB", (20, 40), "white").save(crop_path)
        return [crop_path]

    def fake_read_batch(crop_paths):
        calls.append("vlm")
        return [{"title": "1984", "author": "George Orwell"} for _ in crop_paths]

    def fake_match(title, author):
        calls.append("match")
        return {
            "matched_book": {"title": title, "author": author},
            "confidence": 1.0,
            "title_score": 1.0,
            "author_score": 1.0,
            "ambiguous": False,
            "candidates": [],
        }

    monkeypatch.setattr("books.views.detect_books", fake_detect)
    monkeypatch.setattr("books.views.crop_book_spines", fake_crop)
    monkeypatch.setattr("books.views.read_book_spines_batch", fake_read_batch)
    monkeypatch.setattr("books.views.match_book", fake_match)

    image = BytesIO()
    Image.new("RGB", (20, 20), "white").save(image, format="JPEG")
    image.seek(0)
    with patch("books.views.Book.objects.create") as create_book:
        create_book.return_value.id = 42
        response = APIClient().post(
            "/api/scan/",
            {"photo": SimpleUploadedFile("shelf.jpg", image.read(), "image/jpeg")},
            format="multipart",
        )

    assert response.status_code == 200
    assert calls == ["detect", "crop", "vlm", "match"]
    assert response.json()["crop_count"] == 1
    assert response.json()["books"][0]["confidence"] == 1.0
    assert response.json()["books"][0]["status"] == "auto_matched"
    assert response.json()["books"][0]["saved_book_id"] == 42
    create_book.assert_called_once_with(
        title="1984", author="George Orwell", confidence=1.0
    )


def test_scan_does_not_save_review_items(monkeypatch):
    monkeypatch.setattr(
        "books.views.detect_books", lambda image_path: [{"bbox": [0, 0, 20, 40]}]
    )

    def fake_crop(image_path, detections, output_dir):
        output_dir.mkdir(parents=True, exist_ok=True)
        crop_path = output_dir / "scan_book_01.jpg"
        Image.new("RGB", (20, 40), "white").save(crop_path)
        return [crop_path]

    monkeypatch.setattr("books.views.crop_book_spines", fake_crop)
    monkeypatch.setattr(
        "books.views.read_book_spines_batch",
        lambda crop_paths: [{"title": "The Stranger", "author": None}],
    )
    monkeypatch.setattr(
        "books.views.match_book",
        lambda title, author: {
            "matched_book": None,
            "confidence": 0.7,
            "title_score": 1.0,
            "author_score": 0.0,
            "ambiguous": True,
            "candidates": [],
        },
    )

    with patch("books.views.Book.objects.create") as create_book:
        response = APIClient().post(
            "/api/scan/",
            {"photo": SimpleUploadedFile("shelf.jpg", b"image", "image/jpeg")},
            format="multipart",
        )

    assert response.status_code == 200
    assert response.json()["books"][0]["status"] == "needs_review"
    assert response.json()["books"][0]["saved_book_id"] is None
    create_book.assert_not_called()


def test_scan_returns_empty_result_when_no_books_are_detected(monkeypatch):
    monkeypatch.setattr("books.views.detect_books", lambda image_path: [])
    monkeypatch.setattr(
        "books.views.crop_book_spines",
        lambda image_path, detections, output_dir: [],
    )

    response = APIClient().post(
        "/api/scan/",
        {"photo": SimpleUploadedFile("shelf.jpg", b"image", "image/jpeg")},
        format="multipart",
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["detection_count"] == 0
    assert response.json()["books"] == []
