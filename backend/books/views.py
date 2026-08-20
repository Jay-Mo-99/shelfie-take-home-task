import logging
import tempfile
import time
from pathlib import Path

from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book
from .serializers import BookSerializer
from .detection import crop_book_spines, detect_books
from .matching import AUTO_SAVE_THRESHOLD, REVIEW_THRESHOLD, match_book
from .vlm import read_book_spine

logger = logging.getLogger(__name__)


class ScanView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    # Persist only high-confidence canonical matches; uncertain results must remain visible for human review.
    def post(self, request):
        uploaded_photo = request.FILES.get("photo")
        if uploaded_photo is None:
            return Response(
                {"detail": "A photo file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        started_at = time.time()
        try:
            with tempfile.TemporaryDirectory(prefix="shelfie-scan-") as temp_dir:
                image_path = Path(temp_dir) / (uploaded_photo.name or "scan.jpg")
                with image_path.open("wb") as image_file:
                    for chunk in uploaded_photo.chunks():
                        image_file.write(chunk)

                detections = detect_books(image_path)
                crop_paths = crop_book_spines(
                    image_path, detections, output_dir=Path(temp_dir) / "crops"
                )
                books = []
                for crop_path in crop_paths:
                    reading = read_book_spine(crop_path)
                    matching = match_book(reading.get("title"), reading.get("author"))
                    confidence = matching.get("confidence", 0.0)
                    if not reading.get("title") and not reading.get("author"):
                        scan_status = "unmatched"
                    elif confidence < REVIEW_THRESHOLD:
                        scan_status = "unmatched"
                    elif matching.get("ambiguous") or confidence < AUTO_SAVE_THRESHOLD:
                        scan_status = "needs_review"
                    else:
                        scan_status = "auto_matched"
                    saved_book_id = None
                    if scan_status == "auto_matched" and matching.get("matched_book"):
                        canonical_book = matching["matched_book"]
                        saved_book = Book.objects.create(
                            title=canonical_book["title"],
                            author=canonical_book["author"],
                            confidence=confidence,
                        )
                        saved_book_id = saved_book.id
                    books.append(
                        {
                            "crop": crop_path.name,
                            "reading": reading,
                            "match": matching.get("matched_book"),
                            "candidates": matching.get("candidates", []),
                            "ambiguous": matching.get("ambiguous", False),
                            "confidence": confidence,
                            "title_score": matching.get("title_score", 0.0),
                            "author_score": matching.get("author_score", 0.0),
                            "status": scan_status,
                            "saved_book_id": saved_book_id,
                        }
                    )

            elapsed_seconds = time.time() - started_at
            logger.info(
                "Scan pipeline processed %d crops in %.3f seconds",
                len(books),
                elapsed_seconds,
            )
            return Response(
                {
                    "status": "completed",
                    "message": "Scan pipeline completed.",
                    "detection_count": len(detections),
                    "crop_count": len(crop_paths),
                    "books": books,
                    "latency_seconds": round(elapsed_seconds, 3),
                }
            )
        except Exception:
            logger.exception("Scan pipeline failed")
            elapsed_seconds = time.time() - started_at
            return Response(
                {
                    "status": "failed",
                    "message": "The scan could not be completed.",
                    "books": [],
                    "latency_seconds": round(elapsed_seconds, 3),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# Reuse the same serializer for manual review confirmation and normal library additions.
class BookListCreateView(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
