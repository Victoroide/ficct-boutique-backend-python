"""Sync product metadata + reference image embeddings into DynamoDB."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import List, Optional

import requests
from django.conf import settings

from apps.common.dynamodb.client import table

from .embedding_service import encode_image

logger = logging.getLogger(__name__)


class CatalogSyncService:
    TABLE = "product_embeddings"

    def upsert_embedding(
        self,
        product_id: str,
        embedding: List[float],
        *,
        name: Optional[str] = None,
        category: Optional[str] = None,
        image_url: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> dict:
        """Upsert a product's embedding and metadata into DynamoDB and return
        the stored item."""
        item = {
            "product_id": product_id,
            "embedding": [
                str(v) for v in embedding
            ],  # DynamoDB cannot store floats as numbers cleanly; store as strings
            "embedding_dim": len(embedding),
            "name": name or "",
            "category": category or "",
            "image_url": image_url or "",
            "sku": sku or "",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        table(self.TABLE).put_item(Item=item)
        return item

    def sync_from_image_url(
        self,
        product_id: str,
        image_url: str,
        *,
        name: Optional[str] = None,
        category: Optional[str] = None,
        sku: Optional[str] = None,
    ) -> dict:
        """Download the product image, encode it, and upsert the resulting
        embedding plus metadata."""
        cfg = settings.FICCT_AI
        resp = requests.get(image_url, timeout=cfg["GO_CORE_TIMEOUT_SECONDS"])
        resp.raise_for_status()
        emb = encode_image(resp.content)
        return self.upsert_embedding(
            product_id=product_id,
            embedding=emb,
            name=name,
            category=category,
            image_url=image_url,
            sku=sku,
        )

    def all_embeddings(self) -> List[dict]:
        """Return all stored product embedding items from DynamoDB."""
        scan = table(self.TABLE).scan()
        return scan.get("Items", [])


catalog_sync_service = CatalogSyncService()
