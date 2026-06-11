"""Idempotently create all DynamoDB tables required by the AI service."""

from django.core.management.base import BaseCommand

from apps.common.dynamodb.schema import ensure_all


class Command(BaseCommand):
    help = "Idempotently create all DynamoDB tables used by the AI service."

    def handle(self, *args, **options) -> None:
        created = ensure_all()
        if created:
            self.stdout.write(self.style.SUCCESS(f"created: {', '.join(created)}"))
        else:
            self.stdout.write("all tables already exist")
