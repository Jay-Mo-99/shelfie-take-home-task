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

## Setup

From a clean clone:

```powershell
# Backend
cd backend
py -m venv ..\.venv
..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```

Set `backend/.env` before using the hosted VLM:

```text
GEMINI_API_KEY=your-key-here
```

The Expo app is in a separate directory. In another terminal:

```powershell
cd frontend
npm install
npm start
```

The backend API is available at `http://127.0.0.1:8000`. The main routes are
`POST /api/scan/`, `POST /api/books/`, and `GET /api/books/`.

## Architecture

`POST /api/scan/` saves the upload temporarily, runs YOLOv8n on the CPU,
crops each detected book, sends each crop sequentially to Gemini 3.6 Flash,
and passes only the returned title/author text to the local RapidFuzz matcher.
The matcher returns canonical catalog data, confidence, and ambiguity
candidates. Only `auto_matched` results are persisted to SQLite; review and
unmatched results remain in the response for a later user decision.

The local model handles location detection because it has no API cost and can
run offline. The hosted VLM handles reading spine text because that is the
multimodal task. The VLM is intentionally not given catalog data and is not
allowed to guess catalog membership.

## Catalog

`catalog.csv` contains 102 entries with `title`, `author`, and
`alternate_titles`. It deliberately includes duplicate titles with different
authors, separate editions, US/UK alternate titles, omnibus and individual
volumes, substring titles, and varied author formatting such as initials and
`Last, First` order. The catalog is weighted toward commonly owned books so
that live presentation photos have a reasonable chance of matching.

## Cost Estimate

The local YOLO and RapidFuzz stages cost $0 per request. Gemini 3.6 Flash
standard paid pricing is $0.75 per 1M input tokens and $3.75 per 1M output
tokens through December 31, 2026. Using a planning estimate of 560 image input
tokens plus 50 JSON output tokens per crop gives approximately `$0.00061 per
crop`, or `$0.00549` for the 9-crop `1.jpg` experiment. Actual cost depends on
the usage tokens returned by Gemini and should be verified in the billing
dashboard; this implementation currently logs latency but does not yet expose
provider token usage in the API response.

## Decisions And Tradeoffs

- YOLOv8n was chosen as an off-the-shelf CPU model within the time budget. It
  is easy to run locally, but its general COCO training causes missed or
  merged book spines in dense shelves.
- Sequential VLM calls were chosen first for simpler error isolation and
  logging. This makes a 9-crop scan take about 42 seconds in the best recorded
  run; bounded parallelism would reduce wall-clock latency later.
- An 8-second local VLM cutoff is used while the provider transport deadline
  remains 10 seconds because the Gemini API rejects deadlines below 10 seconds.
- Ambiguous matches are never silently auto-saved. This protects the library
  from choosing the wrong author when identical titles exist.

## Unfinished

- The Expo app is still the SDK 54 starter screen; camera/gallery upload,
  result rendering, review controls, and the library list are not connected to
  the API yet.
- Review confirmation, correction, and discard are represented by the API
  contract and `POST /api/books/`, but there is no dedicated review queue UI.
- The detector is not book-spine-specific, so recall on tightly packed shelves
  is limited. A labeled spine detector or stronger post-processing would be
  the next CV improvement.
- The API does not yet expose Gemini usage tokens or a persisted scan/review
  record. Temporary crops are deleted after each request by design.
