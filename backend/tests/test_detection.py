from PIL import Image

from books.detection import _deduplicate_detections, crop_book_spines


def test_deduplicate_detections_keeps_highest_confidence_overlap():
    detections = [
        {"bbox": [0, 0, 50, 100], "confidence": 0.7},
        {"bbox": [2, 2, 48, 98], "confidence": 0.9},
        {"bbox": [60, 0, 100, 100], "confidence": 0.6},
    ]

    result = _deduplicate_detections(detections)

    assert result == [detections[1], detections[2]]


def test_crop_book_spines_clips_boxes_and_saves_crops(tmp_path):
    image_path = tmp_path / "shelf.jpg"
    Image.new("RGB", (100, 80), "white").save(image_path)

    crop_paths = crop_book_spines(
        image_path,
        [
            {"bbox": [-10, 10, 40, 70]},
            {"bbox": [50, 20, 110, 90]},
        ],
        output_dir=tmp_path / "crops",
    )

    assert len(crop_paths) == 2
    assert Image.open(crop_paths[0]).size == (40, 60)
    assert Image.open(crop_paths[1]).size == (50, 60)
