from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.http import HttpResponse
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from incidents.models import (
    Incident, RegisteredUser, NGOContact,
    PulseSession
)
from .at_utils import send_sms, carrier_from_code
from .handlers import (
    handle_pulse, handle_pulse_reply, handle_reg,
    handle_add, handle_report, handle_tips,
    handle_unknown, dispatch_pulse, _fire_timeout_pulse
)
import hashlib

# ══════════════════════════════════════════════════════════════════════════
# SMS RECEIVE VIEW
# ══════════════════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class SMSReceiveView(APIView):
    """
    POST /api/sms/receive/
    Routes every inbound SMS to the correct handler.

    KEY LOGIC: Before routing by command keyword, check if this number
    has an open PulseSession. If yes, this message is a reply to the
    location confirmation flow — route to handle_pulse_reply first.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        from_number  = request.data.get('from', '')
        text         = request.data.get('text', '').strip()
        network_code = request.data.get('networkCode', '')

        phone_hash = hashlib.sha256(from_number.strip().encode()).hexdigest()

        # ── CHECK FOR OPEN PULSE SESSION FIRST ────────────────────────
        # If this number has a pending session, this message is a
        # YES/NO/landmark reply — not a new command.
        open_session = PulseSession.objects.filter(
            phone_hash=phone_hash,
            state__in=['WAITING_CONFIRM', 'WAITING_LANDMARK']
        ).first()

        if open_session:
            # Check if it expired while waiting
            if open_session.is_expired():
                open_session.state = 'TIMED_OUT'
                open_session.save()
                carrier = carrier_from_code(network_code)
                reply = _fire_timeout_pulse(phone_hash, carrier, network_code)
            else:
                reply = handle_pulse_reply(from_number, text, network_code)
                if reply is None:
                    # Fallback — treat as unknown command
                    reply = handle_unknown(text.split()[0] if text else '')

            send_sms(from_number, reply)
            return HttpResponse('OK', content_type='text/plain', status=200)

        # ── NORMAL COMMAND ROUTING ─────────────────────────────────────
        parts_upper    = text.upper().split()
        parts_original = text.split()
        command        = parts_upper[0] if parts_upper else ''

        if command == 'PULSE':
            reply = handle_pulse(from_number, network_code)

        elif command == 'REG':
            reply = handle_reg(from_number, parts_original, network_code)

        elif command == 'ADD':
            reply = handle_add(from_number, parts_original)

        elif command == 'REPORT':
            reply = handle_report(from_number, parts_upper)

        elif command == 'TIPS':
            reply = handle_tips()

        else:
            first_word = parts_original[0] if parts_original else ''
            reply = handle_unknown(first_word)

        send_sms(from_number, reply)
        return HttpResponse('OK', content_type='text/plain', status=200)


# ══════════════════════════════════════════════════════════════════════════
# STEALTH DIAL VIEW — *384*911#
# ══════════════════════════════════════════════════════════════════════════

@method_decorator(csrf_exempt, name='dispatch')
class StealthPulseView(APIView):
    """
    POST /api/ussd/stealth/
    Silent PULSE. No menu. No confirmation.
    Fires immediately with best available location.
    Screen shows nothing to anyone watching.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        phone_number = request.data.get('phoneNumber', '')
        network_code = request.data.get('networkCode', '')

        phone_hash = hashlib.sha256(
            phone_number.strip().encode()
        ).hexdigest()
        carrier = carrier_from_code(network_code)
        now = timezone.now()

        try:
            user = RegisteredUser.objects.prefetch_related(
                'trusted_contacts'
            ).get(phone_hash=phone_hash)

            zone     = user.registered_zone
            landmark = user.get_best_location()
            contacts = list(user.trusted_contacts.all())

            user.last_pulse_at = now
            user.save(update_fields=['last_pulse_at'])

            contact_alert = (
                f'SAFEPULSE ALERT — {now.strftime("%d %b %Y %H:%M")}\n\n'
                f'Someone you care about may need help.\n\n'
                f'Zone: {zone}\n'
                f'Landmark: {landmark}\n'
                f'Network: {carrier}\n\n'
                f'Please check on them or contact\n'
                f'emergency services immediately.'
            )
            for contact in contacts:
                send_sms(contact.contact_phone, contact_alert)

            ngos = NGOContact.objects.filter(
                zone__iexact=zone, is_active=True
            )
            for ngo in ngos:
                send_sms(ngo.phone, (
                    f'SAFEPULSE NGO ALERT — {now.strftime("%d %b %Y %H:%M")}\n\n'
                    f'STEALTH DIAL activated.\n\n'
                    f'Zone: {zone}\n'
                    f'Landmark: {landmark}\n'
                    f'Network: {carrier}\n\n'
                    f'IMMEDIATE response required.'
                ))

            notes = (
                f'STEALTH PULSE *384*911#. Zone: {zone}. '
                f'Landmark: {landmark}. Carrier: {carrier}. '
                f'{len(contacts)} contact(s) notified.'
            )

        except RegisteredUser.DoesNotExist:
            zone  = 'Unknown'
            notes = (
                f'STEALTH PULSE from unregistered. '
                f'Carrier: {carrier}.'
            )
            send_sms(phone_number, (
                'SafePulse: Alert received.\n\n'
                'To register your location and\n'
                'trusted contacts, text 30333:\n\n'
                'REG Lagos Near blue gate Surulere'
            ))

        Incident.objects.create(
            incident_date=now.date(),
            incident_time=now.time(),
            location=zone,
            incident_type='Unknown',
            severity_level='Critical',
            reporting_channel='USSD',
            follow_up_status='Ongoing',
            is_anonymous=True,
            notes=notes,
            location_confidence='LOW',
            location_source='REGISTERED',
        )

        # Blank END — nothing appears on screen
        return HttpResponse('END', content_type='text/plain', status=200)


from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.utils import timezone
from incidents.models import RegisteredUser, NGOContact, Incident
from sms.handlers import dispatch_pulse
import hashlib


@method_decorator(csrf_exempt, name='dispatch')
class USSDView(View):
    """
    POST /api/incidents/ussd/
    Handles Africa's Talking USSD callback.
    Menu-driven pulse flow for feature phones.
    """

    def post(self, request):
        session_id   = request.POST.get('sessionId', '')
        service_code = request.POST.get('serviceCode', '')
        phone_number = request.POST.get('phoneNumber', '')
        text         = request.POST.get('text', '').strip()

        phone_hash = hashlib.sha256(
            phone_number.strip().encode()
        ).hexdigest()

        # text is empty on first dial, then accumulates replies
        # e.g. "" → "1" → "1*1" → "1*1*Yes"
        parts = text.split('*') if text else []
        level = len(parts)

        # ── Level 0 — First dial, show main menu ──────────────────
        if text == '':
            response = (
                'CON Welcome to SafePulse\n'
                '1. Send emergency alert\n'
                '2. Report an incident\n'
                '3. My account'
            )

        # ── Level 1 — User picked from main menu ──────────────────
        elif level == 1:
            choice = parts[0]

            if choice == '1':
                # Check if registered
                try:
                    user = RegisteredUser.objects.get(phone_hash=phone_hash)
                    response = (
                        f'CON Sending alert from:\n'
                        f'Zone: {user.registered_zone}\n'
                        f'Landmark: {user.landmark or "Not set"}\n\n'
                        f'1. Confirm and send\n'
                        f'2. Use different location'
                    )
                except RegisteredUser.DoesNotExist:
                    # Unregistered — fire immediately
                    self._fire_unregistered_pulse(phone_number, phone_hash)
                    response = (
                        'END Alert sent. Help is on the way.\n\n'
                        'To register your location, text 30333:\n'
                        'REG Lagos Near blue gate'
                    )

            elif choice == '2':
                response = (
                    'CON What type of incident?\n'
                    '1. Domestic Violence\n'
                    '2. Sexual Assault\n'
                    '3. Harassment\n'
                    '4. Child Abuse\n'
                    '5. Other'
                )

            elif choice == '3':
                try:
                    user = RegisteredUser.objects.get(phone_hash=phone_hash)
                    contact_count = user.trusted_contacts.count()
                    response = (
                        f'END Your SafePulse account:\n'
                        f'Zone: {user.registered_zone}\n'
                        f'Landmark: {user.landmark or "Not set"}\n'
                        f'Trusted contacts: {contact_count}\n\n'
                        f'To update, text 30333:\n'
                        f'REG Lagos Near blue gate'
                    )
                except RegisteredUser.DoesNotExist:
                    response = (
                        'END You are not registered.\n\n'
                        'Text 30333:\n'
                        'REG Lagos Near blue gate'
                    )
            else:
                response = 'END Invalid option. Please try again.'

        # ── Level 2 — Responses to level 1 choices ────────────────
        elif level == 2:
            main_choice = parts[0]
            sub_choice  = parts[1]

            if main_choice == '1':
                # Pulse confirmation
                if sub_choice == '1':
                    # Confirmed — fire pulse from registered location
                    result = self._fire_registered_pulse(phone_number, phone_hash)
                    response = f'END {result}'

                elif sub_choice == '2':
                    response = (
                        'CON Enter your current landmark:\n'
                        '(e.g. Near GTBank Ikeja)'
                    )
                else:
                    response = 'END Invalid option.'

            elif main_choice == '2':
                # Incident type chosen — ask severity
                incident_map = {
                    '1': 'Domestic Violence',
                    '2': 'Sexual Assault',
                    '3': 'Harassment',
                    '4': 'Child Abuse',
                    '5': 'Unknown',
                }
                incident_type = incident_map.get(sub_choice, 'Unknown')
                response = (
                    f'CON Incident: {incident_type}\n'
                    'Select severity:\n'
                    '1. Low\n'
                    '2. Medium\n'
                    '3. High\n'
                    '4. Critical'
                )
            else:
                response = 'END Invalid option.'

        # ── Level 3 ────────────────────────────────────────────────
        elif level == 3:
            main_choice = parts[0]
            sub_choice  = parts[1]
            third       = parts[2]

            if main_choice == '1' and sub_choice == '2':
                # User entered custom landmark — fire pulse
                custom_landmark = third
                result = self._fire_pulse_with_landmark(
                    phone_number, phone_hash, custom_landmark
                )
                response = f'END {result}'

            elif main_choice == '2':
                # Incident type + severity chosen — create incident
                incident_map = {
                    '1': 'Domestic Violence',
                    '2': 'Sexual Assault',
                    '3': 'Harassment',
                    '4': 'Child Abuse',
                    '5': 'Unknown',
                }
                severity_map = {
                    '1': 'Low',
                    '2': 'Medium',
                    '3': 'High',
                    '4': 'Critical',
                }
                incident_type = incident_map.get(sub_choice, 'Unknown')
                severity = severity_map.get(third, 'High')

                # Get location
                try:
                    user = RegisteredUser.objects.get(phone_hash=phone_hash)
                    location = user.registered_zone
                except RegisteredUser.DoesNotExist:
                    location = 'Unknown'

                now = timezone.now()
                Incident.objects.create(
                    incident_date=now.date(),
                    incident_time=now.time(),
                    location=location,
                    incident_type=incident_type,
                    severity_level=severity,
                    reporting_channel='USSD',
                    follow_up_status='Ongoing',
                    is_anonymous=True,
                    notes=f'Reported via USSD menu. Type: {incident_type}. Severity: {severity}.',
                    location_confidence='LOW',
                    location_source='REGISTERED',
                )
                response = (
                    'END Report received. You are not alone.\n'
                    'Your report is on the SafePulse dashboard.'
                )
            else:
                response = 'END Invalid option.'

        else:
            response = 'END Session ended. Text 30333 for help.'

        return HttpResponse(response, content_type='text/plain')

    # ── Helper methods ─────────────────────────────────────────────

    def _fire_unregistered_pulse(self, phone_number, phone_hash):
        from sms.at_utils import carrier_from_code
        now = timezone.now()
        Incident.objects.create(
            incident_date=now.date(),
            incident_time=now.time(),
            location='Unknown',
            incident_type='Unknown',
            severity_level='Critical',
            reporting_channel='USSD',
            follow_up_status='Ongoing',
            is_anonymous=True,
            notes='PULSE via USSD from unregistered number.',
            location_confidence='LOW',
            location_source='REGISTERED',
        )
        # Alert any active NGO
        ngos = NGOContact.objects.filter(is_active=True)[:1]
        from sms.at_utils import send_sms
        for ngo in ngos:
            send_sms(ngo.phone, (
                f'SAFEPULSE USSD ALERT — {now.strftime("%d %b %Y %H:%M")}\n\n'
                f'Unregistered user sent pulse via USSD.\n'
                f'No location on file. Please review dashboard.'
            ))

    def _fire_registered_pulse(self, phone_number, phone_hash):
        try:
            user = RegisteredUser.objects.get(phone_hash=phone_hash)
            return dispatch_pulse(
                phone_hash=phone_hash,
                zone=user.registered_zone,
                landmark=user.landmark or user.registered_zone,
                carrier='USSD',
                location_confidence='MEDIUM',
                location_source='REGISTERED',
                network_code='',
            )
        except RegisteredUser.DoesNotExist:
            self._fire_unregistered_pulse(phone_number, phone_hash)
            return 'Alert sent. Help is on the way.'

    def _fire_pulse_with_landmark(self, phone_number, phone_hash, landmark):
        try:
            user = RegisteredUser.objects.get(phone_hash=phone_hash)
            return dispatch_pulse(
                phone_hash=phone_hash,
                zone=user.registered_zone,
                landmark=landmark,
                carrier='USSD',
                location_confidence='MEDIUM',
                location_source='SMS_UPDATE',
                network_code='',
            )
        except RegisteredUser.DoesNotExist:
            self._fire_unregistered_pulse(phone_number, phone_hash)
            return 'Alert sent. Help is on the way.'
