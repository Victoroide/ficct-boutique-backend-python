# Environment variables

Source of truth: [.env.example](../../.env.example) plus [config/settings/base.py](../../config/settings/base.py) (the `FICCT_AI` dict).

## Django core

| Variable | Default | Effect |
|----------|---------|--------|
| `DJANGO_SETTINGS_MODULE` | `config.settings.dev` | Selects the settings module. Use `config.settings.prod` in production. |
| `SECRET_KEY` | — (required) | Django session/CSRF secret. Generate a fresh 50-char random string per environment. |
| `DEBUG` | `True` in dev | `False` in prod settings. Affects error pages, static-file behavior, etc. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated. In the full-system compose, `*` is used (development only). |
| `LOG_LEVEL` | `INFO` | Standard Python logging level. |

## JWT (verifier only)

| Variable | Default | Effect |
|----------|---------|--------|
| `JWT_PUBLIC_KEY_PATH` | `/app/.tools/keys/jwt_public_dev.pem` | RSA public PEM. Required. |
| `JWT_ISSUER` | `ficct-go` | Required `iss` claim. |
| `JWT_AUDIENCE` | `ficct-django` | Token's `aud` must include this value. |

## DynamoDB

| Variable | Default | Effect |
|----------|---------|--------|
| `DYNAMODB_ENDPOINT` | `http://dynamodb:8000` | Local container. In prod, point at the real DynamoDB regional endpoint or remove to use the SDK default. |
| `DYNAMODB_REGION` | `us-east-1` | |
| `DYNAMODB_ACCESS_KEY_ID` | `local` | DynamoDB Local accepts any non-empty value. |
| `DYNAMODB_SECRET_ACCESS_KEY` | `local` | Same as above. |
| `DYNAMODB_TABLE_PREFIX` | `ficct_` | Prepended to every table name. Useful for multi-tenant or multi-env on the same DynamoDB. |

## CORS

| Variable | Default | Effect |
|----------|---------|--------|
| `CORS_ALLOWED_ORIGINS` | `http://localhost:4200,http://localhost:19006,exp://localhost:19000` | Comma-separated. The `exp://` origin is for Expo development. |

## Go core integration

| Variable | Default | Effect |
|----------|---------|--------|
| `GO_CORE_BASE_URL` | `http://host.docker.internal:8080` | Used only as a documentation hint today. The catalog-sync endpoint accepts a full URL per item, so this env var is not strictly read by the sync code path. |
| `GO_CORE_TIMEOUT_SECONDS` | `30` | HTTP timeout for the image fetches inside catalog sync. |

## How these are read

`config/settings/base.py` defines a `FICCT_AI` dict from environment variables; the rest of the code accesses values via `settings.FICCT_AI['KEY_NAME']`. Adding a new variable means:

1. Add it to `.env.example`.
2. Add it to the `FICCT_AI` dict in `config/settings/base.py`.
3. Read it through `settings.FICCT_AI[...]` rather than `os.environ[...]` directly.

The pattern keeps the entire config surface visible in one place.
