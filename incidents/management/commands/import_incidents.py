import csv
import os
from django.conf import settings
from pathlib import Path
from django.core.management.base import BaseCommand
from incidents.models import Incident
 
class Command(BaseCommand):
    help = 'Import SafePulse CSV dataset'
 
    def handle(self, *args, **options):
        filepath = filepath = os.path.join(settings.BASE_DIR, "data_files", "safepulse_dataset.csv")
        created = skipped = 0
        with open(filepath, encoding='utf-8-sig') as f:
            for row in csv.DictReader(f):
                raw_time = row['Incident_Time'].split('.')[0]
                obj, was_created = Incident.objects.get_or_create(
                    incident_date = row['Incident_Date'],
                    incident_time = raw_time,
                    location      = row['Location'].strip(),
                    incident_type = row['Incident_Type'].strip(),
                    defaults={
                        'severity_level':           row['Severity_Level'].strip(),
                        'reporting_channel':        row['Reporting_Channel'].strip(),
                        'victim_age':               int(row['Victim_Age']) if row['Victim_Age'] else None,
                        'victim_gender':            row.get('Victim_Gender','').strip(),
                        'perpetrator_relationship': row.get('Perpetrator_Relationship','').strip(),
                        'support_provided':         row.get('Support_Provided','').strip(),
                        'follow_up_status':         row.get('Follow_Up_Status','Ongoing').strip(),
                        'notes':                    row.get('Notes','').strip(),
                    }
                )
                if was_created: created += 1
                else:           skipped += 1
        self.stdout.write(self.style.SUCCESS(f'{created} created, {skipped} skipped.'))
