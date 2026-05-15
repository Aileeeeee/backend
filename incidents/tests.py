from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from incidents.models import Incident
from datetime import date, time


class IncidentSubmitTest(TestCase):

    def setUp(self):
        Incident.objects.all().delete()
        self.client = APIClient()
        self.url = '/api/incidents/submit/'
        self.valid_data = {
            'incident_date': '2026-05-08',
            'incident_time': '14:30:00',
            'location': 'Lagos',
            'incident_type': 'Domestic Violence',
            'severity_level': 'High',
            'reporting_channel': 'Mobile App',
            'victim_gender': 'Female'
        }

    def test_submit_valid_report_returns_201(self):
        response = self.client.post(self.url, self.valid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Incident.objects.count(), 1)
        self.assertIn('id', response.data)
        self.assertIn('message', response.data)

    def test_submit_sets_anonymous_true(self):
        self.client.post(self.url, self.valid_data, format='json')
        incident = Incident.objects.first()
        self.assertTrue(incident.is_anonymous)

    def test_submit_sets_follow_up_status_ongoing(self):
        self.client.post(self.url, self.valid_data, format='json')
        incident = Incident.objects.first()
        self.assertEqual(incident.follow_up_status, 'Ongoing')

    def test_submit_missing_required_field_returns_400(self):
        incomplete_data = {
            'incident_date': '2026-05-08',
            'incident_time': '14:30:00',
            'incident_type': 'Domestic Violence',
            'severity_level': 'High',
            'reporting_channel': 'Mobile App',
        }
        response = self.client.post(self.url, incomplete_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Incident.objects.count(), 0)

    def test_submit_invalid_incident_type_returns_400(self):
        bad_data = self.valid_data.copy()
        bad_data['incident_type'] = 'Random Crime'
        response = self.client.post(self.url, bad_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class IncidentListTest(TestCase):

    def setUp(self):
        Incident.objects.all().delete()
        self.client = APIClient()
        self.url = '/api/incidents/'
        Incident.objects.create(
            incident_date=date(2026, 5, 1),
            incident_time=time(14, 30),
            location='Lagos',
            incident_type='Domestic Violence',
            severity_level='High',
            reporting_channel='Mobile App',
            follow_up_status='Ongoing',
        )
        Incident.objects.create(
            incident_date=date(2026, 5, 2),
            incident_time=time(10, 0),
            location='Abuja',
            incident_type='Harassment',
            severity_level='Low',
            reporting_channel='SMS',
            follow_up_status='Closed',
        )

    def test_list_returns_all_incidents(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check 'results' instead of response.data directly
        self.assertEqual(len(response.data['results']), 2)

    def test_filter_by_location(self):
        response = self.client.get(self.url, {'location': 'Lagos'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['location'], 'Lagos')

    def test_filter_by_severity(self):
        # NOTE: Ensure your backend filter field is named 'severity' or 'severity_level'
        response = self.client.get(self.url, {'severity': 'High'}) 
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
        self.assertEqual(response.data['results'][0]['severity_level'], 'High')


class AcknowledgeIncidentTest(TestCase):

    def setUp(self):
        Incident.objects.all().delete()
        self.client = APIClient()
        self.incident = Incident.objects.create(
            incident_date=date(2026, 5, 1),
            incident_time=time(14, 30),
            location='Lagos',
            incident_type='Domestic Violence',
            severity_level='Critical',
            reporting_channel='Mobile App',
            follow_up_status='Ongoing',
        )
        self.url = f'/api/incidents/{self.incident.id}/acknowledge/'

    def test_acknowledge_sets_is_acknowledged_true(self):
        response = self.client.patch(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.incident.refresh_from_db()
        self.assertTrue(self.incident.is_acknowledged)

    def test_acknowledge_sets_acknowledged_at(self):
        self.client.patch(self.url)
        self.incident.refresh_from_db()
        self.assertIsNotNone(self.incident.acknowledged_at)

    def test_acknowledge_nonexistent_incident_returns_404(self):
        response = self.client.patch('/api/incidents/99999/acknowledge/')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class IncidentStatsTest(TestCase):

    def setUp(self):
        Incident.objects.all().delete()
        self.client = APIClient()
        self.url = '/api/incidents/stats/'
        Incident.objects.create(
            incident_date=date(2026, 5, 1),
            incident_time=time(14, 30),
            location='Lagos',
            incident_type='Domestic Violence',
            severity_level='Critical',
            reporting_channel='Mobile App',
            follow_up_status='Ongoing',
        )
        Incident.objects.create(
            incident_date=date(2026, 5, 2),
            incident_time=time(10, 0),
            location='Abuja',
            incident_type='Harassment',
            severity_level='Low',
            reporting_channel='SMS',
            follow_up_status='Closed',
        )

    def test_stats_returns_correct_total(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_incidents'], 2)

    def test_stats_returns_correct_critical_ongoing(self):
        response = self.client.get(self.url)
        self.assertEqual(response.data['critical_ongoing'], 1)

    def test_stats_contains_required_keys(self):
        response = self.client.get(self.url)
        self.assertIn('total_incidents', response.data)
        self.assertIn('by_location', response.data)
        self.assertIn('by_type', response.data)
        self.assertIn('by_severity', response.data)