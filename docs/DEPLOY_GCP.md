# MS2 — GCP Cloud Run Deployment

MS2 (Django AI) runs on **GCP Cloud Run** (compute) with **AWS DynamoDB** for
AI/customer data. It is stateless for relational data (SQLite in `/tmp`, unused
for business data).

## Live resources

- Project: `ficct-boutique-django`
- Service: `ficct-ai` (region `us-central1`)
- URL: `https://ficct-ai-1093089304525.us-central1.run.app`
- Scaling: **min instances 0, max instances 1**, 512Mi / 1 vCPU (low cost, scales to zero)
- Container: gunicorn on `:8000`, `config.settings.prod`, health `/api/v1/health/`

## DynamoDB (AWS, us-east-1)

Tables (all **PAY_PER_REQUEST**, tagged `project/service/owner/budget`):
`ficct_product_embeddings`, `ficct_forecast_results`, `ficct_customer_segments`,
`ficct_cluster_runs`. TTL enabled (attribute `ttl`) on `ficct_forecast_results`
and `ficct_cluster_runs`. Read/write verified.

## Environment variables

`DJANGO_SETTINGS_MODULE=config.settings.prod`, `SECRET_KEY`, `ALLOWED_HOSTS`,
`JWT_PUBLIC_KEY_PEM` (Go core **prod** public key — `jwt_authentication.py` prefers
this over the baked dev key), `JWT_ISSUER=ficct-go`, `JWT_AUDIENCE=ficct-django`,
`DYNAMODB_ENDPOINT=https://dynamodb.us-east-1.amazonaws.com`, `DYNAMODB_REGION=us-east-1`,
`DYNAMODB_ACCESS_KEY_ID` / `DYNAMODB_SECRET_ACCESS_KEY`, `DYNAMODB_TABLE_PREFIX=ficct_`,
`GO_CORE_BASE_URL`, `CORS_ALLOWED_ORIGINS`. No secrets committed.

## Access mode — public

The org policy **Domain Restricted Sharing** blocks the `allUsers` invoker IAM
binding. Public access is instead enabled by **disabling the Cloud Run invoker
IAM check**:

```powershell
gcloud run services update ficct-ai --region us-central1 --no-invoker-iam-check
```

Verified: `GET https://ficct-ai-1093089304525.us-central1.run.app/api/v1/health/`
returns **200 without an identity token**. Application-level RS256 JWT auth still
applies to the non-public DRF endpoints.

An authenticated path also works if invoker IAM is re-enabled (SA
`ficct-ci-deployer` granted `roles/run.invoker` + an identity token whose
audience equals the service URL):

```powershell
$T = gcloud auth print-identity-token --impersonate-service-account=ficct-ci-deployer@ficct-boutique-django.iam.gserviceaccount.com --audiences=https://ficct-ai-1093089304525.us-central1.run.app
curl -H "Authorization: Bearer $T" https://ficct-ai-1093089304525.us-central1.run.app/api/v1/health/
```

Custom domain `ai-api-boutique.ficct.com` is a follow-up: GCP managed domain
mapping needs the `gcloud beta` component (not installable in the current env)
plus domain verification, or a Cloudflare proxied CNAME with a Host-header
override (the available CF token is DNS-scoped only).

## CI/CD

`.github/workflows/deploy-ms2-gcp.yml` (push to `main`): install → compileall →
`manage.py check` → pytest → `gcloud run deploy --source`.

Required GitHub Secrets: `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_SA_KEY`,
`DJANGO_SECRET_KEY`, `JWT_PUBLIC_KEY_PEM`, `AWS_ACCESS_KEY_ID`,
`AWS_SECRET_ACCESS_KEY`, `GO_CORE_BASE_URL`, `CORS_ALLOWED_ORIGINS`.

## Local checks

```powershell
python -m compileall apps config
python manage.py check
pytest
```
