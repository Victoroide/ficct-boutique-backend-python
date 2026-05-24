from django.urls import path

from .viewsets import CatalogSyncView, EmbeddingListView, SimilaritySearchView

urlpatterns = [
    path("similarity/search/", SimilaritySearchView.as_view(), name="similarity-search"),
    path("catalog/sync/", CatalogSyncView.as_view(), name="catalog-sync"),
    path("catalog/embeddings/", EmbeddingListView.as_view(), name="embeddings-list"),
]
