from django.shortcuts import render
from django.utils import timezone
from datetime import date, timedelta
from django.db.models import Count

from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from incidents.models import Incident,RegisteredUser, TrustedContact
from incidents.serializers import IncidentSerializer, IncidentSubmissionSerializer,RegisteredUserSerializer, TrustedContactSerializer

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

class IncidentDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            incident = Incident.objects.get(pk=pk)
        except Incident.DoesNotExist:
            return Response(
                {'error': 'Incident not found.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Build timeline dynamically from incident state
        timeline = []

        # Step 1 — always exists
        timeline.append({
            'time':        incident.created_at.strftime('%I:%M %p'),
            'title':       'Report received',
            'description': f'Anonymous report submitted from {incident.location}',
            'status':      'done',
            'color':       'green',
        })

        # Step 2 — triage (acknowledged)
        if incident.is_acknowledged:
            timeline.append({
                'time':        incident.acknowledged_at.strftime('%I:%M %p') if incident.acknowledged_at else '',
                'title':       'Triage completed',
                'description': f'Assigned {incident.severity_level.lower()} priority',
                'status':      'done',
                'color':       'orange',
            })

            # Step 3 — case assigned
            timeline.append({
                'time':        incident.acknowledged_at.strftime('%I:%M %p') if incident.acknowledged_at else '',
                'title':       'Case assigned',
                'description': f'Assigned to NGO',
                'status':      'done',
                'color':       'blue',
            })

        # Step 4 — trusted contact notified
        trusted_contacts = []
        if incident.registered_user:
            try:
                registered_user = RegisteredUser.objects.get(
                    phone_hash=incident.phone_hash
                )
                contacts = TrustedContact.objects.filter(
                    registered_user=incident.registered_user
                )
                trusted_contacts = [
                    {
                        'name':         c.contact_name,
                        'relation':     c.relationship,
                        'phone':        c.contact_phone,
                        'notified_at':  incident.created_at.strftime('%I:%M %p'),
                    }
                    for c in contacts
                ]
                if trusted_contacts:
                    timeline.append({
                        'time':        incident.created_at.strftime('%I:%M %p'),
                        'title':       'Trusted contact attempted',
                        'description': 'Safe outreach initiated',
                        'status':      'done',
                        'color':       'purple',
                    })
            except RegisteredUser.DoesNotExist:
                pass

        # Step 5 — support provided
        if incident.support_provided:
            timeline.append({
                'time':        '',
                'title':       'Support provided',
                'description': f'Referral sent to local NGO',
                'status':      'done',
                'color':       'green',
            })

        # Step 6 — closed
        if incident.follow_up_status == 'Closed':
            timeline.append({
                'time':        incident.updated_at.strftime('%I:%M %p'),
                'title':       'Case closed',
                'description': 'No further escalation reported',
                'status':      'done',
                'color':       'green',
            })
        else:
            timeline.append({
                'time':        '',
                'title':       'Awaiting acknowledgement' if not incident.is_acknowledged else 'Case ongoing',
                'description': '',
                'status':      'pending',
                'color':       'grey',
            })

        serializer = IncidentSerializer(incident)
        return Response({
            **serializer.data,
            'timeline':         timeline,
            'trusted_contacts': trusted_contacts,
        })

# INCIDENT SUBMISSION — from mobile app
class IncidentSubmitView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = IncidentSubmissionSerializer(data=request.data)
        if serializer.is_valid():
            incident = serializer.save()

            # Build location string from coordinates if address not provided
            lat = request.data.get('latitude')
            lng = request.data.get('longitude')
            
            if lat and lng:
                update_fields = []
                if incident.location in ['Unknown', '', None]:
                    incident.location = f'{float(lat):.4f}, {float(lng):.4f}'
                    update_fields.append('location')
                incident.latitude = float(lat)
                incident.longitude = float(lng)
                if request.data.get('location_accuracy'):
                    incident.location_accuracy = float(request.data.get('location_accuracy'))
                    update_fields.append('location_accuracy')
                update_fields += ['latitude', 'longitude']
                incident.save(update_fields=update_fields)
                
            # Fire SMS alerts if this is a mobile pulse
            is_pulse = (
                request.data.get('severity_level') == 'Critical' and
                request.data.get('reporting_channel') == 'Mobile App'
            )

            if is_pulse:
                try:
                    from sms.handlers import dispatch_pulse
                    landmark = incident.location
                    if lat and lng:
                        landmark = f'GPS: {float(lat):.4f}, {float(lng):.4f} — {incident.location}'
                    dispatch_pulse(
                        phone_hash=request.data.get('phone_hash', ''),
                        zone=incident.location,
                        landmark=landmark,
                        carrier='Mobile App',
                        location_confidence='HIGH' if lat and lng else 'LOW',
                        location_source='GPS' if lat and lng else 'UNKNOWN',
                        network_code='',
                        skip_incident_creation=True, 
                    )
                except Exception as e:
                    print(f'Mobile pulse dispatch error: {e}')

            return Response(
                {
                    'id': incident.id,
                    'message': 'Report received. You are not alone.',
                    'location_received': bool(lat and lng),
                },
                status=status.HTTP_201_CREATED
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


#  ACKNOWLEDGE — David acknowledges an incident 
class AcknowledgeIncidentView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
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
    
from accounts.permissions import IsCoordinator, IsFieldStaffOrAbove


class NGODashboardView(APIView):
    """
    GET /api/incidents/dashboard/
    Any logged in NGO user — sees incidents in their city only.
    """
    permission_classes = [IsFieldStaffOrAbove]

    def get(self, request):
        coverage_area = request.user.coverage_area

        qs = Incident.objects.filter(
            location__icontains=coverage_area
        ).order_by('-incident_date', '-incident_time')

        return Response({
            'coverage_area': coverage_area,
            'organisation': request.user.organisation_name,
            'role': request.user.role,
            'total_in_area': qs.count(),
            'critical_ongoing': qs.filter(
                severity_level='Critical',
                follow_up_status='Ongoing'
            ).count(),
            'pending_acknowledgement': qs.filter(
                is_acknowledged=False
            ).count(),
            'incidents': IncidentSerializer(qs, many=True).data,
        })


class CoordinatorDashboardView(APIView):
    """
    GET /api/incidents/coordinator-dashboard/
    Coordinators only — sees all incidents across their state.
    """
    permission_classes = [IsCoordinator]

    def get(self, request):
        from django.db.models import Count
        from django.utils import timezone
        from datetime import timedelta

        state = request.user.organisation.state if request.user.organisation else ''

        qs = Incident.objects.filter(
            location__icontains=state
        ).order_by('-incident_date', '-incident_time')

        if not qs.exists():
            qs = Incident.objects.all().order_by('-incident_date', '-incident_time')

        # ── New reports (last 24 hours) ───────────────────────────────────────
        now           = timezone.now()
        last_24h      = now - timedelta(hours=24)
        last_48h      = now - timedelta(hours=48)

        new_reports   = qs.filter(created_at__gte=last_24h).count()

        # Delta = today's count minus yesterday's count
        yesterday     = qs.filter(
            created_at__gte=last_48h,
            created_at__lt=last_24h,
        ).count()
        new_reports_delta = new_reports - yesterday

        return Response({
            'state':                   state,
            'organisation':            request.user.organisation_name,
            'role':                    'COORDINATOR',
            'total_incidents':         qs.count(),
            'new_reports':             new_reports,        # ← added
            'new_reports_delta':       new_reports_delta,  # ← added
            'critical_ongoing':        qs.filter(
                                           severity_level='Critical',
                                           follow_up_status='Ongoing'
                                       ).count(),
            'pending_acknowledgement': qs.filter(
                                           is_acknowledged=False
                                       ).count(),
            'by_city': list(
                qs.values('location')
                .annotate(count=Count('id'))
                .order_by('-count')
            ),
            'incidents': IncidentSerializer(qs, many=True).data,
        })
    

class RegisterDeviceView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        phone_hash = request.data.get('phone_hash')
        zone = request.data.get('registered_zone', 'Unknown')
        landmark = request.data.get('landmark', 'Mobile App User')

        if not phone_hash:
            return Response(
                {'error': 'phone_hash is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user, created = RegisteredUser.objects.get_or_create(
            phone_hash=phone_hash,
            defaults={
                'registered_zone': zone,
                'landmark': landmark,
            }
        )

        return Response(
            {
                'id': user.id,
                'phone_hash': user.phone_hash,
                'registered_zone': user.registered_zone,
                'created': created,
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )


class TrustedContactListCreateView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        phone_hash = request.query_params.get('phone_hash')
        if not phone_hash:
            return Response([], status=status.HTTP_200_OK)
        try:
            user = RegisteredUser.objects.get(phone_hash=phone_hash)
            contacts = TrustedContact.objects.filter(registered_user=user)
            return Response(
                TrustedContactSerializer(contacts, many=True).data,
                status=status.HTTP_200_OK
            )
        except RegisteredUser.DoesNotExist:
            return Response([], status=status.HTTP_200_OK)

    def post(self, request):
        phone_hash = request.data.get('phone_hash')
        if not phone_hash:
            return Response(
                {'error': 'phone_hash is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = RegisteredUser.objects.get(phone_hash=phone_hash)
        except RegisteredUser.DoesNotExist:
            return Response(
                {'error': 'Device not registered'},
                status=status.HTTP_404_NOT_FOUND
            )

        contact = TrustedContact.objects.create(
            registered_user=user,
            contact_name=request.data.get('contact_name', ''),
            contact_phone=request.data.get('contact_phone', ''),
            relationship=request.data.get('relationship', 'Unknown'),
        )
        return Response(
            TrustedContactSerializer(contact).data,
            status=status.HTTP_201_CREATED
        )


class TrustedContactDeleteView(APIView):
    permission_classes = [permissions.AllowAny]

    def delete(self, request, pk):
        try:
            contact = TrustedContact.objects.get(pk=pk)
            contact.delete()
            return Response(
                {'message': 'Contact removed'},
                status=status.HTTP_200_OK
            )
        except TrustedContact.DoesNotExist:
            return Response(
                {'error': 'Contact not found'},
                status=status.HTTP_404_NOT_FOUND
            )
