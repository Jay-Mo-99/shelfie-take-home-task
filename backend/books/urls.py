from django.urls import path

from .views import BookListCreateView, ScanView

urlpatterns = [
    path("scan/", ScanView.as_view(), name="scan"),
    path("books/", BookListCreateView.as_view(), name="book-list-create"),
]