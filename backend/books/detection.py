import logging
import time
from pathlib import Path

from ultralytics import YOLO

logger = logging.getLogger(__name__)

MODEL_PATH = "yolov8n.pt"
_model = None


def _get_model():
    global _model
    if _model is None:
        _model = YOLO(MODEL_PATH)
    return _model


def detect_books(image_path, confidence_threshold=0.25):
    """Detect COCO book objects in an image using YOLOv8n on the CPU."""
    image_path = Path(image_path)
    started_at = time.time()

    try:
        results = _get_model().predict(
            source=str(image_path),
            device="cpu",
            conf=confidence_threshold,
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

                coordinates = [round(value, 2) for value in box.xyxy[0].tolist()]
                detections.append(
                    {
                        "bbox": coordinates,
                        "confidence": round(float(box.conf[0].item()), 4),
                        "class_id": class_id,
                        "label": label,
                    }
                )
        return detections
    finally:
        elapsed_seconds = time.time() - started_at
        logger.info(
            "YOLO book detection took %.3f seconds for %s",
            elapsed_seconds,
            image_path,
        )
