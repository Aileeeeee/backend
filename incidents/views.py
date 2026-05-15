from django.shortcuts import render
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Count

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from incidents.models import Incident
from incidents.serializers import IncidentSerializer, IncidentSubmissionSerializer


# ── INCIDENT LIST — for dashboard cards ──────────────────────────────────
class IncidentListView(ListAPIView):
    serializer_class = IncidentSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        queryset = Incident.objects.all().order_by('-incident_date', '-incident_time')

        # Filter by location — e.g. ?location=Lagos
        location = self.request.query_params.get('location')
        if location:
            queryset = queryset.filter(location__icontains=location)

        # Filter by incident type — e.g. ?type=Domestic Violence
        incident_type = self.request.query_params.get('type')
        if incident_type:
            queryset = queryset.filter(incident_type=incident_type)

        # Filter by severity — e.g. ?severity=Critical
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(severity_level=severity)

        # Filter by number of days — e.g. ?days=7 returns last 7 days only
        days = self.request.query_params.get('days')
        if days:
            queryset = queryset.filter(
                incident_date__gte=date.today() - timedelta(days=int(days))
            )

        # Filter by acknowledged status — e.g. ?acknowledged=false
        acknowledged = self.request.query_params.get('acknowledged')
        if acknowledged is not None:
            is_ack = acknowledged.lower() == 'true'
            queryset = queryset.filter(is_acknowledged=is_ack)

        return queryset


# INCIDENT SUBMISSION — from mobile app
class IncidentSubmitView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = IncidentSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            incident = serializer.save()
            return Response(
                {'id': incident.id, 'message': 'Report received. You are not alone.'},
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  ACKNOWLEDGE — David acknowledges an incident 
class AcknowledgeIncidentView(APIView):
    permission_classes = [permissions.AllowAny]

    def patch(self, request, pk):
        try:
            incident = Incident.objects.get(pk=pk)
        except Incident.DoesNotExist:
            return Response(
                {'error': 'Incident not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Mark as acknowledged and record when it happened
        incident.is_acknowledged = True
        incident.acknowledged_at = timezone.now()
        incident.save()

        return Response(
            {
                'message': f'Incident {pk} acknowledged.',
                'acknowledged_at': incident.acknowledged_at
            },
            status=status.HTTP_200_OK
        )


#  STATS — summary counts for dashboard charts 
class IncidentStatsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Incident.objects.all()
        return Response({
            'total_incidents': qs.count(),
            'critical_ongoing': qs.filter(
                severity_level='Critical',
                follow_up_status='Ongoing'
            ).count(),
            'closed_cases': qs.filter(follow_up_status='Closed').count(),
            'pending_acknowledgement': qs.filter(is_acknowledged=False).count(),
            'by_location': list(
                qs.values('location')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'by_type': list(
                qs.values('incident_type')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'by_severity': list(
                qs.values('severity_level')
                .annotate(count=Count('id'))
            ),
            'by_channel': list(
                qs.values('reporting_channel')
                .annotate(count=Count('id'))
            ),
        })