# AI Usage

I used two AI assistants during this take-home project: GitHub Copilot Chat (in VS Code) for implementation, and Claude for architecture discussion, debugging strategy, and review.

## GitHub Copilot Chat - implementation

- Repository scaffolding and Expo SDK 54 setup.
- Django and Django REST Framework project wiring.
- YOLOv8n CPU detection integration, Pillow cropping, and IoU deduplication.
- Gemini multimodal client integration, structured JSON parsing, timeout handling, and error fallbacks.
- RapidFuzz catalog matching, confidence scoring, ambiguity detection, and focused tests.
- README experiment notes and implementation documentation.

## Claude - architecture, debugging strategy, and review

- Discussed and decided the pipeline architecture (local CV for detection, hosted VLM for reading only, custom matching logic) before implementation started.
- Diagnosed real API issues as they occurred (Gemini 429 rate limits, 503 capacity errors, the API's minimum 10s deadline) and decided how to respond to each.
- Identified that same-title/different-author catalog matches (for example, "The Stranger") were being silently resolved instead of flagged for review, which led to the ambiguity-detection fix in `matching.py`.
- Reviewed Copilot-generated code and results before accepting them, and helped structure this README and AI_USAGE.md.

## Human Decisions And Verification

I made the final calls on architecture, model routing, confidence thresholds, and the sequential VLM strategy. I reviewed and adjusted generated code, ran the backend tests and Django system checks, and manually exercised the real scan pipeline with the committed bookshelf photos. The Gemini API key stayed in the ignored `backend/.env` file and was never committed.

The real experiments also informed the documented tradeoffs: YOLOv8n misses or merges some adjacent book spines, Gemini requests can return transient 503/504 responses or quota errors, and ambiguous catalog matches are kept for human review rather than silently saved.
