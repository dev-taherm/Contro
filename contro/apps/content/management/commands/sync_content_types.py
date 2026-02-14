from django.core.management.base import BaseCommand

from contro.apps.content.models import ContentTypeDefinition
from contro.apps.content.services.schema import sync_schema


class Command(BaseCommand):
    help = "Sync database tables for all content types."

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-inactive",
            action="store_true",
            help="Include inactive content types.",
        )

    def handle(self, *args, **options):
        qs = ContentTypeDefinition.objects.all()
        if not options.get("include_inactive"):
            qs = qs.filter(is_active=True)

        for content_type in qs:
            result = sync_schema(content_type)
            self.stdout.write(
                self.style.SUCCESS(
                    f"{content_type.slug}: table={'created' if result.created_table else 'existing'}, "
                    f"added={len(result.added_columns)}, m2m={len(result.created_m2m_tables)}"
                )
            )
