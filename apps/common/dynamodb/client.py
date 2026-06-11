"""DynamoDB client + table abstraction for the AI service."""

from __future__ import annotations

import functools
from typing import Any

import boto3
from botocore.config import Config
from django.conf import settings


@functools.lru_cache(maxsize=1)
def get_resource() -> Any:
    cfg = settings.FICCT_AI
    return boto3.resource(
        "dynamodb",
        endpoint_url=cfg["DYNAMODB_ENDPOINT"],
        region_name=cfg["DYNAMODB_REGION"],
        aws_access_key_id=cfg["DYNAMODB_ACCESS_KEY_ID"],
        aws_secret_access_key=cfg["DYNAMODB_SECRET_ACCESS_KEY"],
        config=Config(retries={"max_attempts": 3, "mode": "standard"}),
    )


def table_name(suffix: str) -> str:
    return f"{settings.FICCT_AI['DYNAMODB_TABLE_PREFIX']}{suffix}"


def table(suffix: str) -> Any:
    return get_resource().Table(table_name(suffix))
