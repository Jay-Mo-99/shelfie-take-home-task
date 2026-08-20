import logging
import time
from pathlib import Path

from PIL import Image
from ultralytics import YOLO

logger = logging.getLogger(__name__)

MODEL_PATH = "yolov8n.pt"
DETECTION_CONFIDENCE = 0.25
IOU_THRESHOLD = 0.5
# Full-resolution phone photos make crops far larger than spine text needs.
# Capping the long edge keeps upload size (and Gemini image tokens) down
# without hurting OCR legibility.
CROP_MAX_DIMENSION = 1024
CROP_JPEG_QUALITY = 85
_model = None


# Reuse one model instance so repeated scans avoid model load overhead.
def _get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


# IoU gives a model-agnostic way to identify duplicate boxes from dense shelves.
def _intersection_over_union(first_bbox, second_bbox):
    first_left, first_top, first_right, first_bottom = first_bbox
    second_left, second_top, second_right, second_bottom = second_bbox
    intersection_left = max(first_left, second_left)
    intersection_top = max(first_top, second_top)
    intersection_right = min(first_right, second_right)
    intersection_bottom = min(first_bottom, second_bottom)
    intersection_width = max(0, intersection_right - intersection_left)
    intersection_height = max(0, intersection_bottom - intersection_top)
    intersection_area = intersection_width * intersection_height

    first_area = max(0, first_right - first_left) * max(0, first_bottom - first_top)
    second_area = max(0, second_right - second_left) * max(
        0, second_bottom - second_top
    )
    union_area = first_area + second_area - intersection_area
    return intersection_area / union_area if union_area else 0.0


# Keep precision at the chosen threshold; duplicate boxes should not create extra VLM calls.
def _deduplicate_detections(detections):
    """Keep the highest-confidence box when book boxes overlap too much."""
    remaining = sorted(
        detections, key=lambda detection: detection["confidence"], reverse=True
    )
    kept = []
    while remaining:
        current = remaining.pop(0)
        kept.append(current)
        remaining = [
            detection
            for detection in remaining
            if _intersection_over_union(current["bbox"], detection["bbox"])
            <= IOU_THRESHOLD
        ]
    return kept


# CPU inference keeps the local stage free, reproducible, and runnable without a hosted CV service.
def detect_books(image_path):
    """Detect COCO book objects in an image using YOLOv8n on the CPU."""
    image_path = Path(image_path)
    started_at = time.time()

    try:
        results = _get_model().predict(
            source=str(image_path),
            device="cpu",
            conf=DETECTION_CONFIDENCE,
            verbose=False,
        )
        detections = []
        for result in results:
            names = result.names
            for box in result.boxes:
                class_id = int(box.cls[0].item())
                label = names[class_id]
                if label != "book":
                    continue

                #
                coordinates = [round(value, 2) for value in box.xyxy[0].tolist()]
                detections.append(
                    {
                        "bbox": coordinates,
                        "confidence": round(float(box.conf[0].item()), 4),
                        "class_id": class_id,
                        "label": label,
                    }
                )
        return _deduplicate_detections(detections)
    finally:
        elapsed_seconds = time.time() - started_at
        logger.info(
            "YOLO book detection took %.3f seconds for %s",
            elapsed_seconds,
            image_path,
        )


# Send one spine at a time so the VLM cannot confuse neighboring books in the full shelf image.
def crop_book_spines(image_path, detections, output_dir=None):
    """Crop detected book boxes from any image and return the saved crop paths."""
    image_path = Path(image_path)
    output_dir = Path(output_dir) if output_dir else image_path.parent / "crops"
    output_dir.mkdir(parents=True, exist_ok=True)

    crop_paths = []
    with Image.open(image_path) as image:
        image_width, image_height = image.size
        for index, detection in enumerate(detections, start=1):
            left, top, right, bottom = detection["bbox"]
            box = (
                max(0, min(image_width, round(left))),
                max(0, min(image_height, round(top))),
                max(0, min(image_width, round(right))),
                max(0, min(image_height, round(bottom))),
            )
            if box[2] <= box[0] or box[3] <= box[1]:
                logger.warning("Skipping invalid crop box %s for %s", box, image_path)
                continue

            crop_path = output_dir / f"{image_path.stem}_book_{index:02d}.jpg"
            crop = image.crop(box).convert("RGB")
            crop.thumbnail((CROP_MAX_DIMENSION, CROP_MAX_DIMENSION), Image.LANCZOS)
            crop.save(crop_path, quality=CROP_JPEG_QUALITY)
            crop_paths.append(crop_path)

    logger.info("Saved %d book crops for %s", len(crop_paths), image_path)
    return crop_paths
