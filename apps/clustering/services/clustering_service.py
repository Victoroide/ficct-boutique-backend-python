"""Customer clustering using KMeans over RFM (Recency, Frequency, Monetary) features."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List
from uuid import uuid4

import numpy as np
from sklearn.cluster import KMeans

from apps.common.dynamodb.client import table


@dataclass
class CustomerFeatures:
    customer_id: str
    recency_days: float
    frequency: float
    monetary: float


@dataclass
class CustomerSegment:
    customer_id: str
    cluster: int
    distance: float
    recency_days: float
    frequency: float
    monetary: float


class ClusteringService:
    TABLE_SEGMENTS = "customer_segments"
    TABLE_RUNS = "cluster_runs"

    def fit_segments(self, features: Iterable[CustomerFeatures], *, k: int = 4) -> List[CustomerSegment]:
        rows = list(features)
        if not rows:
            return []
        if len(rows) < k:
            k = max(1, len(rows))

        x = np.array([[r.recency_days, r.frequency, r.monetary] for r in rows], dtype=np.float64)
        # standardize columns
        means = np.mean(x, axis=0)
        stds = np.std(x, axis=0)
        stds[stds == 0] = 1.0
        x = (x - means) / stds

        kmeans = KMeans(n_clusters=k, n_init=10, random_state=42)
        labels = kmeans.fit_predict(x)
        distances = np.min(kmeans.transform(x), axis=1)

        out: List[CustomerSegment] = []
        for i, row in enumerate(rows):
            out.append(
                CustomerSegment(
                    customer_id=row.customer_id,
                    cluster=int(labels[i]),
                    distance=float(distances[i]),
                    recency_days=float(row.recency_days),
                    frequency=float(row.frequency),
                    monetary=float(row.monetary),
                )
            )
        return out

    def persist(self, segments: List[CustomerSegment], *, metadata: dict) -> dict:
        run_id = str(uuid4())
        run_meta = {
            "run_id": run_id,
            "computed_at": datetime.now(timezone.utc).isoformat(),
            "segment_count": len(segments),
            "metadata": metadata,
        }
        table(self.TABLE_RUNS).put_item(Item=run_meta)

        # batch write to TABLE_SEGMENTS
        target = table(self.TABLE_SEGMENTS)
        with target.batch_writer() as batch:
            for s in segments:
                batch.put_item(
                    Item={
                        "customer_id": s.customer_id,
                        "cluster": s.cluster,
                        "distance": str(round(s.distance, 6)),
                        "recency_days": str(round(s.recency_days, 6)),
                        "frequency": str(round(s.frequency, 6)),
                        "monetary": str(round(s.monetary, 6)),
                        "run_id": run_id,
                        "computed_at": run_meta["computed_at"],
                    }
                )
        return run_meta

    def segment_for(self, customer_id: str) -> dict:
        resp = table(self.TABLE_SEGMENTS).get_item(Key={"customer_id": customer_id})
        return resp.get("Item") or {}

    def all_segments(self) -> List[dict]:
        resp = table(self.TABLE_SEGMENTS).scan()
        return resp.get("Items", [])


clustering_service = ClusteringService()
