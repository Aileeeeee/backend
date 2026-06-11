import csv
import os
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand
from incidents.models import Incident


class Command(BaseCommand):
    help = 'Import SafePulse CSV dataset'

    def handle(self, *args, **options):
        filepath = os.path.join(settings.BASE_DIR, "data_files", "safepulse_dataset.csv")
        created = skipped = 0

        with open(filepath, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):

                # Normalize date to YYYY-MM-DD regardless of source format
                raw_date = row['incident_date'].strip()
                try:
                    incident_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                except ValueError:
                    incident_date = datetime.strptime(raw_date, '%m/%d/%Y').date()

                raw_time = row['incident_time'].strip().split('.')[0]

                # Parse booleans safely
                def to_bool(val, default=False):
                    if isinstance(val, bool):
                        return val
                    return str(val).strip().lower() in ('true', '1', 'yes')

                # Parse nullable datetime fields
                def to_datetime(val):
                    val = str(val).strip()
                    if not val or val.lower() in ('', 'none', 'nan'):
                        return None
                    try:
                        return datetime.strptime(val, '%Y-%m-%d %H:%M:%S')
                    except ValueError:
                        return None

                obj, was_created = Incident.objects.get_or_create(
                    incident_date=incident_date,
                    incident_time=raw_time,
                    location=row['location'].strip(),
                    incident_type=row['incident_type'].strip(),
                    defaults={
                        'severity_level':            row['severity_level'].strip(),
                        'reporting_channel':          row['reporting_channel'].strip(),
                        'victim_age':                 int(row['victim_age']) if row.get('victim_age') else None,
                        'victim_gender':              row.get('victim_gender', '').strip(),
                        'perpetrator_relationship':   row.get('perpetrator_relationship', '').strip(),
                        'support_provided':           row.get('support_provided', '').strip(),
                        'follow_up_status':           row.get('follow_up_status', 'Ongoing').strip(),
                        'notes':                      row.get('notes', '').strip(),
                        'is_anonymous':               to_bool(row.get('is_anonymous', False)),
                        'is_acknowledged':            to_bool(row.get('is_acknowledged', False)),
                        'acknowledged_at':            to_datetime(row.get('acknowledged_at')),
                        'reporter_type':              row.get('reporter_type', '').strip(),
                        'last_verified_location':     row.get('last_verified_location', '').strip(),
                        'location_confidence':        row.get('location_confidence', '').strip(),
                        'location_source':            row.get('location_source', '').strip(),
                        'latitude':                   float(row['latitude']) if row.get('latitude') else None,
                        'longitude':                  float(row['longitude']) if row.get('longitude') else None,
                        'location_accuracy':          float(row['location_accuracy']) if row.get('location_accuracy') else None,
                        'created_at':                 to_datetime(row.get('created_at')),
                        'updated_at':                 to_datetime(row.get('updated_at')),
                    }
                )

                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(self.style.SUCCESS(f'{created} created, {skipped} skipped.'))
