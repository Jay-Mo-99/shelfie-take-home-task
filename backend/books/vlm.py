import asyncio
import json
import logging
import mimetypes
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

logger = logging.getLogger(__name__)

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

MODEL_NAME = "gemini-3.6-flash"
# The local cutoff must stay above the transport deadline below it, not under
# it — otherwise we abandon responses that were still within the budget we
# already gave the HTTP client, and every slow-but-successful call gets
# misreported as a timeout.
GEMINI_HTTP_TIMEOUT_SECONDS = 10
VLM_TIMEOUT_SECONDS = 12
PROMPT = (
    "Read the book title and author exactly as they appear in this image. "
    "Do not match against a catalog or guess. Return null for anything that "
    "is not visible or that you are not confident about. Return JSON only."
)
RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "title": {"type": "STRING", "nullable": True},
        "author": {"type": "STRING", "nullable": True},
    },
    "required": ["title", "author"],
}


# Return a stable shape so one failed crop does not blank the entire scan result.
def _safe_result(error=None):
    result = {"title": None, "author": None}
    if error:
        result["error"] = error
    return result


# Keep reading separate from catalog matching so the hosted model cannot invent catalog membership.
def read_book_spine(image_path):
    """Read visible title and author text from one cropped book-spine image."""
    image_path = Path(image_path)
    started_at = time.time()

    try:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return _safe_result("missing_api_key")

        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/jpeg"
        image_bytes = image_path.read_bytes()
        client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(timeout=GEMINI_HTTP_TIMEOUT_SECONDS * 1000),
        )
        response = asyncio.run(
            asyncio.wait_for(
                client.aio.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        types.Part.from_text(text=PROMPT),
                        types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=RESPONSE_SCHEMA,
                    ),
                ),
                timeout=VLM_TIMEOUT_SECONDS,
            )
        )

        try:
            parsed = json.loads(response.text or "")
            return {
                "title": parsed.get("title"),
                "author": parsed.get("author"),
            }
        except (AttributeError, TypeError, json.JSONDecodeError):
            return _safe_result("parse_failed")
    except (TimeoutError, httpx.TimeoutException):
        return _safe_result("timeout")
    except genai_errors.ServerError as error:
        if getattr(error, "code", None) == 504:
            return _safe_result("timeout")
        logger.exception("Gemini VLM server error for %s", image_path)
        return _safe_result("request_failed")
    except Exception:
        logger.exception("Gemini VLM request failed for %s", image_path)
        return _safe_result("request_failed")
    finally:
        elapsed_seconds = time.time() - started_at
        logger.info(
            "Gemini VLM reading took %.3f seconds for %s",
            elapsed_seconds,
            image_path,
        )
