# FICCT Boutique — AI Service (MS2)

Django + DRF service that hosts the AI-flavored endpoints of the boutique system. It does **not** own products, sales, inventory, or customers — those live in the Go core (MS1). It does **not** mint tokens — it only verifies them with the public key shared by Go.

## What is real in this repo

This service implements three AI features, each backed by a real Python algorithm:

1. **Image similarity search** — cosine similarity over a 112-dimensional embedding made of a perceptual hash (64 dims) plus an HSV color histogram (48 dims). No CLIP. No ResNet. No deep CNN. The embedding function is in [apps/ai_catalog/services/embedding_service.py](apps/ai_catalog/services/embedding_service.py) and is named `encode_image`. A code seam exists so it could be swapped for a learned model later, but **today it is `phash + HSV histogram`**.
2. **Demand forecasting** — Holt's linear (double-exponential) smoothing implemented in pure numpy in [apps/forecasting/services/forecast_service.py](apps/forecasting/services/forecast_service.py). No statsmodels, no ARIMA, no Prophet.
3. **Customer clustering** — `sklearn.cluster.KMeans` over 3-dimensional RFM features (Recency / Frequency / Monetary). Features are standardized per-batch (mean 0, std 1). See [apps/clustering/services/clustering_service.py](apps/clustering/services/clustering_service.py).

Every other claim about this service in any other document should be checked against the code in `apps/` before being repeated. There are no training pipelines, no GPU code paths, no model files, no LLM calls.

## What this service does at runtime

- Exposes REST endpoints under `/api/v1/`.
- Verifies RS256 bearer tokens issued by Go (audience must include `ficct-django`).
- Reads and writes to DynamoDB Local (four tables, prefix `ficct_`).
- Serves an OpenAPI schema + Swagger UI from `drf-spectacular`.
- Fetches product images from URLs supplied by the Go catalog when running `POST /ai/catalog/sync/`.

---

## Tech stack

| Concern | Choice |
|---------|--------|
| Runtime | Python 3.12, Django 5, DRF |
| Database | DynamoDB Local (PROD: regular DynamoDB) via `boto3` |
| Auth | `PyJWT[crypto]` RS256 verify-only |
| ML libs | `numpy`, `scikit-learn`, `Pillow`, `imagehash` |
| API docs | `drf-spectacular` (OpenAPI + Swagger UI + ReDoc) |
| Server | `gunicorn` in prod containers, `runserver` in dev |
| Lint / test | `black`, `isort`, `flake8`, `pytest` |

---

## Directory layout

```
config/
  settings/
    base.py
    dev.py
    prod.py
  urls.py             namespaces /api/v1/ai/*, /api/v1/forecasting/*, /api/v1/clustering/*
apps/
  common/
    auth/             RS256JWTAuthentication, IsAdminOrStaff
    dynamodb/
      client.py       boto3 resource (lru_cache'd) + table() helper
      tables.py       TABLES list used by ensure_tables management cmd
    management/
      commands/
        ensure_tables.py
    views/
      health.py       GET /api/v1/health/
  ai_catalog/
    services/
      embedding_service.py    encode_image(): pHash + HSV histogram
      similarity_service.py   cosine search over DynamoDB embeddings
      catalog_sync_service.py upsert and batch sync from image URLs
    serializers/
    viewsets/                 SimilaritySearchView, CatalogSyncView, EmbeddingListView
    urls.py
  forecasting/
    services/forecast_service.py    Holt linear smoothing + persist
    viewsets/                       RunForecastView, LatestForecastView
    urls.py
  clustering/
    services/clustering_service.py  KMeans over RFM, persist segments + runs
    viewsets/                       RunClusteringView, AllSegmentsView, CustomerSegmentView
    urls.py
requirements/
  base.txt   prod.txt   dev.txt   (pinned)
```

---

## Running it

### Standalone

```powershell
copy .env.example .env
docker compose up -d --build
# API:     http://localhost:8000/
# Swagger: http://localhost:8000/api/v1/schema/swagger/
# ReDoc:   http://localhost:8000/api/v1/schema/redoc/
# Health:  http://localhost:8000/api/v1/health/
```

The compose file brings up DynamoDB Local (`amazon/dynamodb-local`) and this service. The container command runs `python manage.py ensure_tables && python manage.py runserver 0.0.0.0:8000` — `ensure_tables` is idempotent and recreates only what's missing.

### Full system

Under `docker-compose.full.yml` in the Go repo, this service is at host port **8092**, DynamoDB has no exposed port (only reachable from inside the Docker network), and the `GO_CORE_BASE_URL` env points at `http://go-core:8080` (the in-network hostname).

---

## REST endpoints

All under `/api/v1/`. All require `Authorization: Bearer <token>` except `/health/` and the schema/swagger/redoc endpoints.

| Method | Path | Roles | Purpose |
|--------|------|-------|---------|
| GET | `/health/` | (public) | Liveness |
| GET | `/schema/` | (public) | OpenAPI 3 JSON |
| GET | `/schema/swagger/` | (public) | Swagger UI |
| GET | `/schema/redoc/` | (public) | ReDoc UI |
| POST | `/ai/similarity/search/` (multipart) | any auth | Search top-K similar products by uploaded image |
| POST | `/ai/catalog/sync/` | admin, staff | Batch upsert product embeddings from image URLs |
| GET | `/ai/catalog/embeddings/` | admin, staff | List stored embeddings (vector field is stripped from the response) |
| POST | `/forecasting/run/` | admin, staff | Run a forecast on a provided series |
| GET | `/forecasting/latest/<scope>/` | admin, staff | Read the latest forecast for a scope |
| POST | `/clustering/run/` | admin, staff | Cluster a batch of customers by RFM |
| GET | `/clustering/segments/` | admin, staff | List all stored segments |
| GET | `/clustering/segments/<customer_id>/` | admin, staff | Single customer's segment |

Request/response shapes are in [docs/architecture/REST_API.md](docs/architecture/REST_API.md).

---

## DynamoDB tables

The `DYNAMODB_TABLE_PREFIX` (default `ficct_`) is prepended to each name:

| Table | PK | SK | Purpose |
|-------|----|----|---------|
| `ficct_product_embeddings` | `product_id` (S) | — | One embedding per product |
| `ficct_forecast_results` | `scope` (S) | `computed_at` (S) | History of forecasts per scope |
| `ficct_customer_segments` | `customer_id` (S) | — | Latest cluster assignment per customer |
| `ficct_cluster_runs` | `run_id` (S) | — | Metadata for each clustering run |

All tables are `PAY_PER_REQUEST` mode. The `ensure_tables` management command creates anything missing on startup.

---

## Authentication

`RS256JWTAuthentication` (DRF authentication class) loads the public PEM at `JWT_PUBLIC_KEY_PATH` once at startup. Every request:

1. Reads `Authorization: Bearer ...`.
2. Verifies signature, `iss`, `aud`, `exp`.
3. Populates `request.user` with a lightweight user wrapping the claims (`sub`, `email`, `role`).

`IsAdminOrStaff` (DRF permission) checks `request.user.role in {'admin', 'staff'}`. Customers can call `/ai/similarity/search/` (any authenticated user can) but cannot trigger catalog sync, forecasting, or clustering runs.

---

## Catalog sync

`POST /ai/catalog/sync/` takes a batch of `{ product_id, image_url, name, category, sku }` objects. For each one:

1. The service performs an HTTP GET against `image_url` (timeout from `GO_CORE_TIMEOUT_SECONDS`, default 30s).
2. Pillow loads the bytes; `encode_image` produces the 112-dim float vector.
3. The vector and the metadata are upserted into `product_embeddings`.

**The fetch is anonymous.** It does not pass the user's bearer token. The `image_url` must therefore be reachable without auth from inside the Django container's network. In the full-system compose this works because the demo products use `/static/products/<sku>.svg` served by the Go service on `http://go-core:8080/static/products/<sku>.svg`. For Express-hosted documents, the operator must trigger sync *after* generating a presigned GET URL on the Express side and pass that URL into the body.

---

## Security notes

- **Token verification only** — this service holds no signing key. A compromised Django container cannot mint tokens, only impersonate the role claims of tokens it received.
- **`DEBUG=False` in prod** (`config/settings/prod.py`). The `dev.py` settings module enables `DEBUG=True` and the Swagger UI without authentication.
- **CORS** — strict allow-list from `CORS_ALLOWED_ORIGINS`.
- **No SQL**. The only databases this service speaks to are DynamoDB. It uses Django's ORM exclusively for the built-in apps (sessions/auth tables Django installs by default).
- **No file persistence**. Uploaded images for similarity search are read into memory and discarded after `encode_image`. They are never written to disk and never sent to a third party.

---

## Known limitations

- The embedding is **deliberately simple**. It distinguishes "similar overall color/shape" but cannot match across major lighting changes the way a deep network would. The seam at `encode_image` allows swapping it later — none of the call sites care about the vector dimension as long as it's consistent across the catalog.
- The catalog sync fetcher is synchronous and single-threaded. Syncing N products takes ≈ N × (HTTP fetch + encode) seconds. For 4 demo SKUs this is fine.
- Forecasts and clustering are computed synchronously inside the request handler. No background worker.
- DynamoDB Local is **in-memory** in the meta-compose (`-inMemory -sharedDb`). Restarting the container loses every embedding, segment, and forecast. The `ensure_tables` step re-creates the schema but obviously not the rows.

---

## Documentation index

- [docs/architecture/SYSTEM_OVERVIEW.md](docs/architecture/SYSTEM_OVERVIEW.md) — role in the FICCT Boutique stack.
- [docs/architecture/REST_API.md](docs/architecture/REST_API.md) — every endpoint's request and response shape.
- [docs/architecture/ALGORITHMS.md](docs/architecture/ALGORITHMS.md) — the actual math: pHash + HSV embedding, Holt smoothing, KMeans on standardized RFM.
- [docs/development/RUNNING_LOCALLY.md](docs/development/RUNNING_LOCALLY.md) — bring-up + smoke tests.
- [docs/development/ENVIRONMENT.md](docs/development/ENVIRONMENT.md) — env variable reference.
