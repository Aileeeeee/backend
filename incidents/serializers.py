from rest_framework import serializers
from .models import Incident

class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'is_acknowledged', 'acknowledged_at']


class IncidentSubmissionSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Incident
        fields = [
            'incident_date', 'incident_time', 'location', 'incident_type',
            'victim_age', 'victim_gender', 'perpetrator_relationship',
            'reporting_channel', 'severity_level', 'support_provided',
        ]

    def create(self, validated_data):
        validated_data['follow_up_status'] = 'Ongoing'
        validated_data['is_anonymous'] = True
        return super().create(validated_data)