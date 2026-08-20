# AI Usage

I used two AI assistants during this take-home project: GitHub Copilot Chat (in VS Code) for backend implementation, and Claude for architecture discussion, the entire Expo frontend, debugging, and review.

## GitHub Copilot Chat — backend implementation

- Repository scaffolding and Expo SDK 54 setup.
- Django and Django REST Framework project wiring.
- YOLOv8n CPU detection integration, Pillow cropping, and IoU deduplication.
- Gemini multimodal client integration, structured JSON parsing, timeout handling, and error fallbacks.
- RapidFuzz catalog matching, confidence scoring, ambiguity detection, and focused tests.
- README experiment notes and implementation documentation.

## Claude — frontend, architecture, debugging, and review

- Discussed and decided the pipeline architecture (local CV for detection, hosted VLM for reading only, custom matching logic) before implementation started.
- Built the entire Expo frontend: `App.tsx`, `PhotoCapture`/`ReviewQueue`/`ReviewItem`/`BookList` components, and `services/api.ts`, and wired it to the existing backend endpoints.
- Diagnosed real API issues as they occurred (Gemini 429 rate limits, 503 capacity errors, the API's minimum 10s deadline) and decided how to respond to each.
- Identified that same-title/different-author catalog matches (for example, "The Stranger") were being silently resolved instead of flagged for review, which led to the ambiguity-detection fix in `matching.py`.
- Found and fixed a real bug: the local VLM timeout (8s) was shorter than the transport deadline already given to the HTTP client (10s), so genuine slow-but-successful responses were being discarded as timeouts.
- Added crop downscaling before the VLM call to cut upload size and Gemini image tokens.
- Switched VLM calls from sequential to bounded concurrency after measuring that a 7-crop scan took 100+ seconds sequentially; concurrent calls (capped at 4 in flight) brought the same scan to 19.5 seconds, with no change to per-crop success/failure behavior.
- Diagnosed a real local-network connectivity problem (the phone couldn't reach the dev machine over Wi-Fi) down to router-level AP/client isolation, after ruling out the backend bind address, Windows Firewall, and third-party (McAfee) firewall settings one at a time. Set up and verified a Cloudflare Tunnel fallback for both Metro and Django, and wrote the corresponding README troubleshooting section.
- Reviewed Copilot-generated code and results before accepting them, and helped structure this README and AI_USAGE.md.

## Human Decisions And Verification

I made the final calls on architecture, model routing, confidence thresholds, and the VLM concurrency strategy. I reviewed and adjusted generated code, ran the backend tests and Django system checks, and manually exercised the real scan pipeline — both with the committed test photos and with bookshelf photos taken during development — from a physical phone through Expo Go. The Gemini API key stayed in the ignored `backend/.env` file and was never committed.

The real experiments also informed the documented tradeoffs: YOLOv8n misses or merges some adjacent book spines, Gemini requests can return transient 503/504 responses, quota errors, or plain timeouts, and ambiguous or unmatched catalog results are kept for human review rather than silently saved or dropped.
