# REST API Reference

All paths are under `/api/v1/`. Auth: `Authorization: Bearer <accessToken>` minted by the Go service, with `aud` including `ficct-django`. Tokens must be RS256-signed.

URL configuration: [config/urls.py](../../config/urls.py).

## Auth-free endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/v1/health/` | Returns `{"status": "ok"}` |
| GET | `/api/v1/schema/` | OpenAPI 3 spec JSON (drf-spectacular) |
| GET | `/api/v1/schema/swagger/` | Swagger UI |
| GET | `/api/v1/schema/redoc/` | ReDoc UI |

The Swagger/ReDoc pages are useful but are mounted **without authentication**. Remove them or wrap them in a permission class before any public deployment.

---

## `/ai/similarity/search/` — image similarity

**Method:** POST
**Permissions:** any authenticated user
**Body:** `multipart/form-data`

| Field | Type | Notes |
|-------|------|-------|
| `image` | file | required, JPEG/PNG/WEBP supported by Pillow |
| `top_k` | int | optional, default 5 |

Server reads the file fully into memory, calls `embedding_service.encode_image`, then iterates over every row in `product_embeddings` and computes cosine similarity. Returns the top-K rows sorted by descending score.

```jsonc
// 200 response
{
  "results": [
    {
      "product_id": "...",
      "name": "Blusa Seda Marfil",
      "category": "blusas",
      "image_url": "/static/products/BLZ-001.svg",
      "sku": "BLZ-001",
      "score": 0.9134
    },
    ...
  ]
}
```

If no embeddings have been synced, `results` is empty. The endpoint never errors on "no data".

---

## `/ai/catalog/sync/` — batch upsert embeddings

**Method:** POST
**Permissions:** admin, staff
**Body:** JSON

```jsonc
{
  "items": [
    {
      "product_id": "<uuid>",
      "image_url": "http://go-core:8080/static/products/BLZ-001.svg",
      "name": "Blusa Seda Marfil",
      "category": "blusas",
      "sku": "BLZ-001"
    },
    ...
  ]
}
```

For each item: fetch `image_url` (anonymous GET, configurable timeout via `GO_CORE_TIMEOUT_SECONDS`), compute the embedding, upsert into `product_embeddings`. Errors per item are reported individually; one bad URL does not abort the batch.

```jsonc
// 200 response
{
  "synced": [
    {"product_id": "...", "embedding_dim": 112}
  ],
  "errors": [
    {"product_id": "...", "error": "HTTPConnectionPool... timeout"}
  ]
}
```

---

## `/ai/catalog/embeddings/` — list embeddings (no vector)

**Method:** GET
**Permissions:** admin, staff

Returns every row in `product_embeddings` with the `embedding` field stripped (it's a 112-element list and listing endpoints don't need it).

```jsonc
{
  "items": [
    {
      "product_id": "...",
      "embedding_dim": 112,
      "name": "...",
      "category": "...",
      "image_url": "...",
      "sku": "...",
      "updated_at": "..."
    },
    ...
  ]
}
```

---

## `/forecasting/run/` — Holt linear smoothing

**Method:** POST
**Permissions:** admin, staff
**Body:** JSON

```jsonc
{
  "scope": "category:blusas",     // arbitrary string, used as DynamoDB PK
  "series": [12, 14, 11, 17, 22], // historical observations, oldest first
  "horizon": 4                    // optional, default 4
}
```

The service runs `forecast_service.forecast_series(series, horizon=horizon)` with `alpha=0.6, beta=0.2` (currently hard-coded in `forecast_service.py`) and persists the result with `computed_at = now()`.

```jsonc
// 200 response
{
  "scope": "category:blusas",
  "horizon": 4,
  "computed_at": "2026-05-23T19:30:00+00:00",
  "points": [
    {"period_index": 1, "value": 24.32},
    {"period_index": 2, "value": 26.10},
    {"period_index": 3, "value": 27.88},
    {"period_index": 4, "value": 29.66}
  ]
}
```

---

## `/forecasting/latest/<scope>/` — most recent forecast

**Method:** GET
**Permissions:** admin, staff

Queries `forecast_results` with `KeyConditionExpression="scope = :s"` and `ScanIndexForward=False, Limit=1` to get the newest row for that scope.

```jsonc
// 200 response (or {"forecast": null} if none)
{
  "scope": "category:blusas",
  "horizon": 4,
  "computed_at": "...",
  "points": [...]
}
```

---

## `/clustering/run/` — KMeans over RFM

**Method:** POST
**Permissions:** admin, staff
**Body:** JSON

```jsonc
{
  "k": 4,
  "customers": [
    {"customer_id": "<uuid>", "recency_days": 12, "frequency": 4, "monetary": 1450.0},
    {"customer_id": "<uuid>", "recency_days": 60, "frequency": 1, "monetary": 320.0},
    ...
  ]
}
```

Server:

1. Builds a 3-column matrix (recency, frequency, monetary).
2. Standardizes columns to mean 0 / std 1.
3. Runs `sklearn.cluster.KMeans(n_clusters=k, n_init=10, random_state=42)`.
4. Returns each customer's cluster label and distance to centroid.
5. Persists a `cluster_runs` row keyed by a fresh `run_id`, plus one `customer_segments` row per customer (write replaces any previous segment for that customer).

```jsonc
// 200 response
{
  "run": {
    "run_id": "<uuid>",
    "computed_at": "...",
    "segment_count": 24,
    "metadata": {"k": 4, "n": 24}
  },
  "segments": [
    {"customer_id": "...", "cluster": 2, "distance": 0.413},
    ...
  ]
}
```

If `n < k`, `k` is silently lowered to `n`. If `n == 0`, the response is `{"run": {...zero segments...}, "segments": []}`.

---

## `/clustering/segments/` — list all segments

**Method:** GET
**Permissions:** admin, staff

`scan()` over the entire `customer_segments` table. For demo scale this is fine; for production scale it would need pagination.

```jsonc
{
  "segments": [
    {"customer_id": "...", "cluster": 2, "distance": 0.413, "run_id": "..."},
    ...
  ]
}
```

---

## `/clustering/segments/<customer_id>/` — single customer

**Method:** GET
**Permissions:** admin, staff

`get_item({customer_id})` — returns `{"segment": null}` if no row exists.

```jsonc
{
  "segment": {
    "customer_id": "...",
    "cluster": 2,
    "distance": 0.413,
    "run_id": "...",
    "computed_at": "..."
  }
}
```

---

## Error responses

DRF's default error envelope is preserved:

| HTTP | Meaning |
|------|---------|
| 400 | Validation error (DRF serializer rejected the body) |
| 401 | Missing / invalid bearer token |
| 403 | Authenticated but role is insufficient |
| 404 | Path not matched |
| 500 | Unhandled exception (logged with traceback) |
