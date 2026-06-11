"""Image similarity search against catalog embeddings."""

from __future__ import annotations

from typing import List

from .catalog_sync_service import catalog_sync_service
from .embedding_service import cosine_similarity, encode_image


class SimilarityService:
    def search(self, image_bytes: bytes, *, top_k: int = 5) -> List[dict]:
        """Encode the query image and return the top_k catalog products
        ranked by cosine similarity to its embedding."""
        query_vec = encode_image(image_bytes)
        items = catalog_sync_service.all_embeddings()
        scored = []
        for item in items:
            try:
                emb = [float(x) for x in item.get("embedding", [])]
            except (TypeError, ValueError):
                continue
            if not emb:
                continue
            score = cosine_similarity(query_vec, emb)
            scored.append(
                {
                    "product_id": item["product_id"],
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "image_url": item.get("image_url", ""),
                    "sku": item.get("sku", ""),
                    "score": round(score, 4),
                }
            )
        scored.sort(key=lambda r: r["score"], reverse=True)
        return scored[:top_k]


similarity_service = SimilarityService()
