from rest_framework import generics, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Book
from .serializers import BookSerializer


class ScanView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if "photo" not in request.FILES:
            return Response(
                {"detail": "A photo file is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "mock",
                "message": "Scan pipeline is not implemented yet.",
                "books": [],
            }
        )


class BookListCreateView(generics.ListCreateAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializer
