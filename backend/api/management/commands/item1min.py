from django.core.management.base import BaseCommand
from api.models import *

class Command(BaseCommand):
    help = 'Aggregates Item data by millisecond and populates Item_1ms table with min and max prices.'

    def handle(self, *args, **options):
        self.stdout.write("Starting millisecond aggregation...")

        count = 0

        items_to_process = Item_10s.objects.all()

        n = 60000000

        for x in items_to_process:
            time_10ms = x.time.replace(microsecond=(x.time.microsecond // n) * n)
            millisecond_entry, created = Item_1min.objects.get_or_create(
                time=time_10ms,
                symbol=x.symbol,
                defaults={
                    'min': x.min,
                    'max': x.max
                }
            )

            if not created:
                updated = False
                if x.min < millisecond_entry.min:
                    millisecond_entry.min = x.min
                    updated = True
                if x.max > millisecond_entry.max:
                    millisecond_entry.max = x.max
                    updated = True

                if updated:
                    millisecond_entry.save(update_fields=['min', 'max'])

            count += 1
            if count % 1000 == 0:
                self.stdout.write(f"Processed {count} items...")

        self.stdout.write(self.style.SUCCESS(f"Done. Processed {count} items total."))
