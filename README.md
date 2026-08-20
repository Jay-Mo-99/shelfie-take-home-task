# Shelfie

## CV Detection Experiment

The current local CV step uses Ultralytics YOLOv8n with CPU inference and the
COCO `book` class. Detection confidence is fixed at `0.25`. After inference,
overlapping book boxes are deduplicated with IoU non-maximum suppression at
`0.50`; when boxes overlap above that threshold, the higher-confidence box is
kept.

The test image `backend/test_photos/easy-case1.jpg` contains 12 visible books. On
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

`POST /api/scan/` runs local YOLO detection and Pillow crops, then reads all
crops from one photo through Gemini **concurrently** (bounded to 4 requests
at a time — see `VLM_MAX_CONCURRENCY` in `vlm.py`), then does catalog
matching. VLM calls were originally sequential (one request, wait, next
request); on `backend/test_photos/easy-case1.jpg` (7 crops) that took `100+ seconds`.
Switching to bounded concurrency dropped the same scan to `19.477 seconds` —
total latency now tracks roughly the slowest single call instead of the sum
of every call. Per-crop read reliability is unchanged by this (each call
still succeeds or fails independently); only the wall-clock time to run a
full scan improved. Failed or slow individual crops are still returned as
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
..\.venv\Scripts\python.exe manage.py runserver 0.0.0.0:8000
```

`0.0.0.0:8000` is required, not optional — Django's default `runserver` binds
to `127.0.0.1` only, which a phone on the same Wi-Fi cannot reach even if
every firewall rule is correct.

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

Scan the printed QR code with Expo Go on a phone connected to the **same
Wi-Fi network** as your computer. The app detects your computer's LAN IP
automatically (via Expo's `hostUri`), so no manual configuration is needed
for this path.

### If Expo Go can't connect ("request timed out")

This is almost always local network/firewall, not the app. In order of
likelihood:

1. **Backend not bound to `0.0.0.0`** — see above.
2. **Firewall blocking Node's inbound connections.** On Windows, an inbound
   allow rule for Node.js often exists for a *previous* Node install/version
   and silently doesn't match the one actually running (common after
   switching Node version managers). Check with:
   ```powershell
   Get-Command node   # confirm the active node.exe path
   Get-NetFirewallRule -Direction Inbound -Enabled True | Where-Object { $_.DisplayName -match 'node' } | Get-NetFirewallApplicationFilter
   ```
   If the active path isn't listed, add a rule for it (as Administrator):
   ```powershell
   New-NetFirewallRule -DisplayName "Node.js (dev)" -Direction Inbound -Program "<path from Get-Command node>" -Action Allow -Profile Any
   ```
3. **Router/office Wi-Fi client (AP) isolation** — phones can't reach laptops
   even on the same SSID. This is the one that actually bit us during
   development on a home network. The tell: a phone browser hangs on a
   loading spinner (not an instant error) when opening
   `http://<computer-LAN-IP>:8000/api/books/` directly, while the same URL
   works fine from a browser on the computer itself.

   Tunnel mode alone does **not** fix this — `npm run start:tunnel` only
   proxies the JS bundle, so the app will load, but every API call will still
   fail with "Could not reach the server," because Django is still only
   reachable over the LAN. Confirmed fixes, in order of convenience:
   - **Wire the computer to the router with an Ethernet cable**, if
     available. AP isolation typically only isolates *wireless* clients from
     each other, so a wired computer is usually unaffected. Free and instant.
   - **Turn off AP/client isolation in the router's admin page** (often
     `http://192.168.1.1` or `http://192.168.2.1` — check the router itself).
     Look for "AP Isolation," "Client Isolation," or "Wireless Isolation" in
     the Wi-Fi settings. Free and permanent, but needs router admin access.
   - **Connect both the phone and the computer to the phone's personal
     hotspot** instead of the router. This sidesteps the router entirely.
     Only the computer's own outbound traffic (the Gemini calls) uses
     cellular data — the phone-to-computer traffic (JS bundle, photo
     upload, book list) stays on the hotspot's local Wi-Fi and costs
     nothing. Good live-demo fallback if the venue's Wi-Fi is uncooperative.
   - **Last resort — tunnel both Metro and the backend**, if none of the
     above are possible (no cable, no router access, no hotspot). This only
     needs the computer to have outbound internet access; it works
     regardless of any local network restriction. Run two tunnels:
     ```powershell
     # Terminal A — tunnel Django (needs no signup)
     npx cloudflared tunnel --url http://localhost:8000
     ```
     Copy the `https://<random-name>.trycloudflare.com` URL it prints, then:
     ```powershell
     # Terminal B — tunnel Metro and point the app at the Django tunnel
     $env:EXPO_PUBLIC_API_BASE_URL = "https://<random-name>.trycloudflare.com/api"
     npm run start:tunnel
     ```
     Scan the new QR code. Tunneling only Django (skipping Metro) is not
     enough on an isolated network — the app would fail to even load, since
     Metro would still be unreachable the same way. Both tunnels are needed
     together.

   If tunnel mode is used on a network that turns out not to have isolation,
   set the LAN IP explicitly before starting, since the automatic `hostUri`
   detection returns a public tunnel hostname instead of the LAN IP in this
   mode:
   ```powershell
   $env:EXPO_PUBLIC_API_BASE_URL = "http://<your-computer-LAN-IP>:8000/api"
   npm run start:tunnel
   ```
   Find `<your-computer-LAN-IP>` with `ipconfig` (Windows) or `ifconfig`/`ip a`
   (macOS/Linux).

The backend API is available at `http://127.0.0.1:8000` on the host machine.
The main routes are `POST /api/scan/`, `POST /api/books/`, and
`GET /api/books/`.

## Architecture

`POST /api/scan/` saves the upload temporarily, runs YOLOv8n on the CPU,
crops each detected book, sends all crops to Gemini 3.6 Flash concurrently
(bounded to 4 in flight), and passes only the returned title/author text to
the local RapidFuzz matcher.
The matcher returns canonical catalog data, confidence, and ambiguity
candidates. Only `auto_matched` results are persisted to SQLite; review and
unmatched results remain in the response for a later user decision.

The local model handles location detection because it has no API cost and can
run offline. The hosted VLM handles reading spine text because that is the
multimodal task. The VLM is intentionally not given catalog data and is not
allowed to guess catalog membership.

## Catalog

`catalog.csv` contains 119 entries with `title`, `author`, and
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
crop`, or `$0.00549` for a 9-crop scan of `easy-case1.jpg`. Actual cost depends on
the usage tokens returned by Gemini and should be verified in the billing
dashboard; this implementation currently logs latency but does not yet expose
provider token usage in the API response.

## Decisions And Tradeoffs

- YOLOv8n was chosen as an off-the-shelf CPU model within the time budget. It
  is easy to run locally, but its general COCO training causes missed or
  merged book spines in dense shelves.
- VLM calls were sequential at first, for simpler error isolation and
  logging. Once the pipeline worked, they were switched to bounded
  concurrency (max 4 in flight) since it only reduces wall-clock time and
  does not change per-crop success/failure behavior — a 7-crop scan dropped
  from 100+ seconds to 19.5 seconds on the same test photo.
- The local VLM cutoff (12s) is kept slightly above the provider transport
  deadline (10s, the Gemini API's own minimum) rather than below it — an
  earlier version had this backwards and was discarding responses that were
  still within the budget already given to the HTTP client.
- Ambiguous matches are never silently auto-saved. This protects the library
  from choosing the wrong author when identical titles exist.

## Unfinished

- The detector is not book-spine-specific, so recall on tightly packed shelves
  is limited. A labeled spine detector or stronger post-processing would be
  the next CV improvement.
- The API does not yet expose Gemini usage tokens or a persisted scan/review
  record. Temporary crops are deleted after each request by design.
- The review queue holds state only in memory on the Expo app; a scan result
  is lost if the app is closed before the user confirms or discards every
  item. Persisting an in-progress scan to the backend would be the next step.
- Uploads are sequential (one photo scanned at a time); there is no queue for
  scanning multiple photos in one session.
