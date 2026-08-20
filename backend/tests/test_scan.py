from io import BytesIO
import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient


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

    def fake_read(crop_path):
        calls.append("vlm")
        return {"title": "1984", "author": "George Orwell"}

    def fake_match(title, author):
        calls.append("match")
        return {
            "matched_book": {"title": title, "author": author},
            "confidence": 1.0,
            "title_score": 1.0,
            "author_score": 1.0,
        }

    monkeypatch.setattr("books.views.detect_books", fake_detect)
    monkeypatch.setattr("books.views.crop_book_spines", fake_crop)
    monkeypatch.setattr("books.views.read_book_spine", fake_read)
    monkeypatch.setattr("books.views.match_book", fake_match)

    image = BytesIO()
    Image.new("RGB", (20, 20), "white").save(image, format="JPEG")
    image.seek(0)
    response = APIClient().post(
        "/api/scan/",
        {"photo": SimpleUploadedFile("shelf.jpg", image.read(), "image/jpeg")},
        format="multipart",
    )

    assert response.status_code == 200
    assert calls == ["detect", "crop", "vlm", "match"]
    assert response.json()["crop_count"] == 1
    assert response.json()["books"][0]["confidence"] == 1.0


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
