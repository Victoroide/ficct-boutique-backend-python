"""DynamoDB table definitions used by `ensure_tables` management command."""
from .client import get_resource, table_name


TABLES = [
    {
        "TableName": "product_embeddings",
        "KeySchema": [{"AttributeName": "product_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "product_id", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "forecast_results",
        "KeySchema": [
            {"AttributeName": "scope", "KeyType": "HASH"},
            {"AttributeName": "computed_at", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "scope", "AttributeType": "S"},
            {"AttributeName": "computed_at", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "customer_segments",
        "KeySchema": [{"AttributeName": "customer_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "customer_id", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
    {
        "TableName": "cluster_runs",
        "KeySchema": [{"AttributeName": "run_id", "KeyType": "HASH"}],
        "AttributeDefinitions": [{"AttributeName": "run_id", "AttributeType": "S"}],
        "BillingMode": "PAY_PER_REQUEST",
    },
]


def ensure_all() -> list[str]:
    resource = get_resource()
    existing = {t.name for t in resource.tables.all()}
    created = []
    for spec in TABLES:
        full = table_name(spec["TableName"])
        if full in existing:
            continue
        params = dict(spec)
        params["TableName"] = full
        resource.create_table(**params).wait_until_exists()
        created.append(full)
    return created
