# Shelfie

## CV Detection Experiment

The current local CV step uses Ultralytics YOLOv8n with CPU inference and the
COCO `book` class. Detection confidence is fixed at `0.25`. After inference,
overlapping book boxes are deduplicated with IoU non-maximum suppression at
`0.50`; when boxes overlap above that threshold, the higher-confidence box is
kept.

The test image `backend/test_photos/1.jpg` contains 12 visible books. On
the CPU test machine, an YOLOv8n run took `2.626 seconds`, produced 10 raw
book detections, and returned 9 detections after IoU deduplication at
confidence `0.25`. Lowering confidence to `0.10` produced
12 `book` labels, but also overlapping duplicate boxes and incorrect labels
such as `remote` and `tie`. Increasing the inference size to 1280 did not
make the result stable: it produced 15 book labels at confidence `0.10` and 6
at `0.25`.

## VLM Model Comparison

The first paid-plan run used `gemini-3.7-flash`: 5 of 9 VLM calls returned
HTTP 200, 4 returned HTTP 503, and total latency was `40.405 seconds`.

`gemini-2.5-flash` was also tested, but the API returned HTTP 404 for all 9
calls because that model is no longer available to new users. The API error
recommended `gemini-3.6-flash`, so the implementation now uses that model.

With `gemini-3.6-flash` and the previous 30-second timeout, 7 of 9 calls
returned HTTP 200, 0 returned HTTP 503, and 2 returned HTTP 504. Total latency
was `96.987 seconds`.

The current implementation keeps `gemini-3.6-flash` and applies an 8-second
local async cutoff. Google's API rejects provider deadlines below 10 seconds,
so the transport deadline is set to 10 seconds while the local cutoff returns
the safe `timeout` result at 8 seconds. In the repeated run, all 9 calls
returned HTTP 200 with 0 timeouts and total latency of `42.451 seconds`.

This is a known limitation of using a general COCO detector for book spines:
the model is not trained to separate adjacent spines, and some spines are
classified as other objects. The current implementation favors precision at
`0.25` and makes duplicate suppression explicit. A book-spine-specific model
or a labeled local dataset would be the next step for higher recall.

## End-to-End Scan Experiment

`POST /api/scan/` now runs the stages sequentially: local YOLO detection,
Pillow crops, one Gemini VLM request per crop, and catalog matching. On
`backend/test_photos/1.jpg`, the pipeline produced 9 crops and completed in
`27.522 seconds` on the test machine. The first 6 VLM calls returned HTTP 200;
the remaining 3 returned HTTP 429 because the Gemini free tier limit for
`gemini-3.7-flash` was 5 requests per minute. Those failures were returned as
safe per-book errors instead of aborting the scan.

The endpoint response includes the detected/cropped counts, each crop's VLM
reading, matched catalog entry, title/author scores, combined confidence, and
the total `latency_seconds`. Temporary upload and crop files are deleted after
the request completes.

Matching uses `AUTO_SAVE_THRESHOLD=0.85` and `REVIEW_THRESHOLD=0.5`. Scan
results are labeled `auto_matched`, `needs_review`, or `unmatched`. Near-tied
catalog candidates from different authors are returned as `ambiguous` with up
to three candidates and always require review.
