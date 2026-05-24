"""Lightweight demand forecasting.

For an academic deliverable, we ship a Holt-Winters double exponential smoothing
implementation that runs on Python+numpy without statsmodels. It is enough to
demonstrate the architecture: take a list of historical observations per scope
(product, category, branch) and return a forecast horizon.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, List, Optional

import numpy as np

from apps.common.dynamodb.client import table


@dataclass
class ForecastPoint:
    period_index: int
    value: float


class ForecastService:
    TABLE = "forecast_results"

    def forecast_series(
        self,
        series: Iterable[float],
        *,
        horizon: int = 4,
        alpha: float = 0.6,
        beta: float = 0.2,
    ) -> List[ForecastPoint]:
        """Holt's linear (double) exponential smoothing forecast."""
        data = [float(x) for x in series]
        n = len(data)
        if n == 0:
            return []
        if n == 1:
            return [ForecastPoint(period_index=i + 1, value=data[0]) for i in range(horizon)]

        level = data[0]
        trend = data[1] - data[0]
        for t in range(1, n):
            prev_level = level
            level = alpha * data[t] + (1 - alpha) * (level + trend)
            trend = beta * (level - prev_level) + (1 - beta) * trend

        out = []
        for h in range(1, horizon + 1):
            value = max(0.0, level + h * trend)
            out.append(ForecastPoint(period_index=h, value=value))
        return out

    def persist(self, scope: str, points: List[ForecastPoint], metadata: Optional[dict] = None) -> dict:
        computed_at = datetime.now(timezone.utc).isoformat()
        item = {
            "scope": scope,
            "computed_at": computed_at,
            "horizon": len(points),
            "points": [{"period_index": p.period_index, "value": str(round(p.value, 4))} for p in points],
            "metadata": metadata or {},
        }
        table(self.TABLE).put_item(Item=item)
        return item

    def latest(self, scope: str) -> Optional[dict]:
        resp = table(self.TABLE).query(
            KeyConditionExpression="#s = :s",
            ExpressionAttributeNames={"#s": "scope"},
            ExpressionAttributeValues={":s": scope},
            ScanIndexForward=False,
            Limit=1,
        )
        items = resp.get("Items", [])
        return items[0] if items else None


forecast_service = ForecastService()


def standardize_series(values: Iterable[float]) -> List[float]:
    """Return values divided by their max so the chart is human-readable."""
    data = np.array(list(values), dtype=np.float32)
    if data.size == 0:
        return []
    m = float(np.max(np.abs(data)))
    if m == 0:
        return [float(v) for v in data.tolist()]
    return [float(v / m) for v in data.tolist()]
