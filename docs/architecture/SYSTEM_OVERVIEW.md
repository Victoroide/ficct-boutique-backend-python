# System Overview — Django AI Service (MS2)

This service hosts the AI features. It is the lightest of the three backends in terms of state — it owns no relational schema, only four DynamoDB tables. Its inputs come from clients (the Angular admin app, the React Native customer app) and from the Go core (via product image URLs).

## Role in the stack

```
+----------------+      +------------------+      +--------------------+
|  Go (MS1)      |      |  Django (MS2)    |      |  Express (MS3)     |
|  GraphQL       |      |  this service    |      |  documents + S3    |
|  Postgres      |      |  DynamoDB Local  |      |  Postgres          |
+----------------+      +------------------+      +--------------------+
       |                        ^
       | mints RS256 token       \ 
       v                          \   verifies token with shared public key
   +----------------+              \ 
   |  Angular  /    | -----------+  +---------+
   |  React Native  |           Bearer token
   +----------------+
```

This service:

- Verifies JWTs but does not mint them.
- Stores embeddings, forecasts, and customer segments in DynamoDB.
- Does **not** write to the Go database, the Express database, or the S3 bucket.
- Reaches out to image URLs (typically served by Go's `/static/products/<sku>.svg` route) to fetch bytes during catalog sync.

## Features in scope

| Feature | Algorithm | Storage |
|---------|-----------|---------|
| Image similarity search | pHash (64 dims) + HSV histogram (48 dims) → cosine similarity | `product_embeddings` |
| Catalog sync | HTTP GET image, `encode_image`, upsert | `product_embeddings` |
| Demand forecast | Holt linear (double-exponential) smoothing | `forecast_results` |
| Customer clustering | KMeans on standardized RFM features | `customer_segments`, `cluster_runs` |

There is no other AI feature in this codebase. There is no model training, no nightly job, no GPU code path, no third-party AI API call.

## What the service receives

| From | What | When |
|------|------|------|
| Angular admin | Multipart image (similarity search), batch catalog sync requests, forecast inputs, clustering inputs | On-demand from the admin UI |
| React Native customer | Multipart image (similarity search) | When the user uses the "buscar por foto" feature in the customer app |
| Go core | Indirect — image URLs supplied in catalog sync request bodies | Only when catalog sync is invoked |

## What the service emits

It only returns HTTP responses. There is no outbound webhook, no event bus, no cron job that pushes data elsewhere.

## Why DynamoDB rather than Postgres?

The data shapes are simple key-value reads with no joins:

- "Give me the embedding for `product_id`."
- "Give me the latest forecast for `scope`."
- "Give me the segment for `customer_id`."

DynamoDB's PK / PK+SK access pattern is a natural fit, and using a different database than the other two services keeps the responsibility boundary obvious. The downside is that DynamoDB Local is in-memory in our meta-compose, so the AI state is ephemeral across restarts — which is acceptable for a demo.

## Auth model

The token is the only thing this service trusts about a caller. Once verified:

| Claim | Used as |
|-------|---------|
| `sub` | persisted as `customer_id` or `actor` in DynamoDB items where applicable |
| `email` | passed through into logged events |
| `role` | gates which endpoints the caller can use (`IsAdminOrStaff`) |

There is no per-tenant scoping, no resource-level ACL, no row-level filtering. The token's `aud` claim must include `ficct-django`; tokens issued for `ficct-express` only are rejected.

## Networking

In the full-system compose:

| Host | Port | Reachable from |
|------|------|----------------|
| `django-ai` | 8000 (container) → **8092** (host) | host browser, other containers via `http://django-ai:8000` |
| `dynamodb` | 8000 (container, no host map) | only other containers via `http://dynamodb:8000` |

The React Native customer app uses a nginx reverse-proxy in front of itself (`mobile-web` container) so calls to `/api/ai/...` reach this service at the in-network hostname. The Angular admin runs in a separate container but uses the host port directly (`http://localhost:8092` in dev).
