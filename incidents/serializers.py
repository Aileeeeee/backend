from rest_framework import serializers
from .models import Incident

#Serializers for the Incidents
class IncidentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Incident
        fields = [
            'id',
            'incident_type',
            'location',
            'incident_date',
            'incident_time',
            'severity_level',
            'follow_up_status',
            'created_at',
            ]