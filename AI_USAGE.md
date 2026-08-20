# AI Usage

I used AI coding assistants during this take-home project.

## Where AI Helped

- Repository scaffolding and Expo SDK 54 setup.
- Django and Django REST Framework project wiring.
- YOLOv8n CPU detection integration, Pillow cropping, and IoU deduplication.
- Gemini multimodal client integration, structured JSON parsing, timeout handling, and error fallbacks.
- RapidFuzz catalog matching, confidence scoring, ambiguity detection, and focused tests.
- README experiment notes and implementation documentation.

## Human Decisions And Verification

I selected the application architecture, model routing, confidence thresholds, and sequential VLM strategy. I reviewed and adjusted generated code, ran the backend tests and Django system checks, and manually exercised the real scan pipeline with the committed bookshelf photos. The Gemini API key stayed in the ignored `backend/.env` file and was never committed.

The real experiments also informed the documented tradeoffs: YOLOv8n misses or merges some adjacent book spines, Gemini requests can return transient 503/504 responses or quota errors, and ambiguous catalog matches are kept for human review rather than silently saved.
