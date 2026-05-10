from django.shortcuts import render
from rest_framework.generics import ListAPIView
from incidents.models import Incident
from incidents.serializers import IncidentSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class IncidentListView(ListAPIView):
    serializer_class = IncidentSerializer
    queryset = Incident.objects.all().order_by('-created_at')


#
class AcknowledgeIncidentView(APIView):
    def patch(self, request, pk):
        try:
            incident = Incident.objects.get(pk=pk)
        except Incident.DoesNotExist:
            return Response({'error': 'Incident not found'}, status=status.HTTP_404_NOT_FOUND)

        incident.follow_up_status = 'Ongoing'  # or 'Closed' depending on your logic
        incident.save()
        return Response({'message': f'Incident {pk} acknowledged.'}, status=status.HTTP_200_OK)

# In IncidentListView, add filtering by recent time if needed
from django.utils import timezone
from datetime import timedelta

class IncidentListView(ListAPIView):
    serializer_class = IncidentSerializer

    def get_queryset(self):
        queryset = Incident.objects.all().order_by('-created_at')
        since = self.request.query_params.get('since')
        if since:
            queryset = queryset.filter(created_at__gte=since)
        return queryset