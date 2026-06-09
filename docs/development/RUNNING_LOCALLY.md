# Running the AI service locally

## Standalone (this repo only)

```powershell
copy .env.example .env
docker compose up -d --build
# API:     http://localhost:8000/
# Swagger: http://localhost:8000/api/v1/schema/swagger/
# Health:  http://localhost:8000/api/v1/health/
```

Two containers come up:

| Container | Image | Port |
|-----------|-------|------|
| `dynamodb` | `amazon/dynamodb-local:2.5.2` | container 8000 (no host map) |
| `app` | this Dockerfile (REQUIREMENTS=dev.txt) | host **8000** |

Container command: `python manage.py ensure_tables && python manage.py runserver 0.0.0.0:8000`.

## Full system

Under the meta-compose in the Go repo:

- API host port becomes **8092** (`localhost:8092/api/v1/...`).
- DynamoDB Local is in-memory (`-inMemory -sharedDb`) and has no host port at all. Use the AWS CLI from inside the network to inspect:

  ```powershell
  docker compose -f docker-compose.full.yml exec django-ai python manage.py shell -c "from apps.common.dynamodb.client import get_resource; print(list(get_resource().tables.all()))"
  ```

## Required setup

The Dockerfile copies `.tools/keys/` into the image. Before the first build, put the **public** RSA key (matching what Go's `cmd/server` signs with) at:

```
.tools/keys/jwt_public_dev.pem
```

Without it, every authenticated endpoint returns `401`. See [../../go/ficct-boutique-backend-go/docs/development/JWT_KEYS.md](../../../../../go/ficct-boutique-backend-go/docs/development/JWT_KEYS.md) for how to generate it.

## Smoke tests

```powershell
# 1. Health
curl http://localhost:8000/api/v1/health/

# 2. Anonymous call to a protected route — must be denied
curl -i http://localhost:8000/api/v1/clustering/segments/
# HTTP/1.1 401 Unauthorized
```

Authenticated calls (token from Go):

```powershell
$resp = curl -s -X POST http://localhost:8093/graphql `
  -H "Content-Type: application/json" `
  -d '{\"query\":\"mutation { login(input:{email:\\\"<admin-email>\\\",password:\\\"<admin-password>\\\"}) { accessToken } }\"}'
$token = ($resp | ConvertFrom-Json).data.login.accessToken

curl http://localhost:8000/api/v1/clustering/segments/ -H "Authorization: Bearer $token"
# {"segments": []}
```

Seed an embedding via catalog sync:

```powershell
curl -X POST http://localhost:8000/api/v1/ai/catalog/sync/ `
  -H "Authorization: Bearer $token" `
  -H "Content-Type: application/json" `
  -d '{"items":[{"product_id":"<uuid>","image_url":"http://host.docker.internal:8093/static/products/BLZ-001.svg","name":"Blusa","sku":"BLZ-001"}]}'
```

Then run a similarity search:

```powershell
curl -X POST http://localhost:8000/api/v1/ai/similarity/search/ `
  -H "Authorization: Bearer $token" `
  -F "image=@/path/to/test.jpg" `
  -F "top_k=3"
```

## Resetting

DynamoDB Local in the standalone compose is also non-persistent (no volume mount). Restarting the `dynamodb` container clears everything. `ensure_tables` rebuilds the table definitions but the rows are gone.

If you need persistence in dev, edit `docker-compose.yml` and remove `-inMemory` from the dynamodb command, then add a named volume — but be aware that the meta-compose intentionally keeps it ephemeral to keep the developer experience reproducible.

## Running tests

```powershell
docker compose exec app pytest
# OR locally with a venv that has requirements/dev.txt installed:
python -m pytest
```

Tests live next to the apps (`apps/<app>/tests/`). They are unit tests; nothing in the test suite reaches out to DynamoDB or the network.
