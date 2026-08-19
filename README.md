# Shelfie

## CV Detection Experiment

The current local CV step uses Ultralytics YOLOv8n with CPU inference and the
COCO `book` class. Detection confidence is fixed at `0.25`. After inference,
overlapping book boxes are deduplicated with IoU non-maximum suppression at
`0.50`; when boxes overlap above that threshold, the higher-confidence box is
kept.

The test image `backend/test_photos/1.jpg` contains 12 visible books. On the
CPU test machine, an YOLOv8n run took `2.626 seconds`, produced 10 raw
book detections, and returned 9 detections after IoU deduplication at
confidence `0.25`. Lowering confidence to `0.10` produced
12 `book` labels, but also overlapping duplicate boxes and incorrect labels
such as `remote` and `tie`. Increasing the inference size to 1280 did not
make the result stable: it produced 15 book labels at confidence `0.10` and 6
at `0.25`.

This is a known limitation of using a general COCO detector for book spines:
the model is not trained to separate adjacent spines, and some spines are
classified as other objects. The current implementation favors precision at
`0.25` and makes duplicate suppression explicit. A book-spine-specific model
or a labeled local dataset would be the next step for higher recall.
