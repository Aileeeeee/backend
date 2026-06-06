from django.utils import timezone
from datetime import timedelta
from incidents.models import (
    Incident, RegisteredUser, TrustedContact,
    NGOContact, PulseSession
)
from .at_utils import send_sms, carrier_from_code, normalise_city
import hashlib


INCIDENT_TYPE_MAP = {
    'DV': 'Domestic Violence',
    'SA': 'Sexual Assault',
    'H':  'Harassment',
    'CA': 'Child Abuse',
    'OT': 'Unknown',
}

SEVERITY_MAP = {
    'LOW':  'Low',
    'MED':  'Medium',
    'HIGH': 'High',
    'CRIT': 'Critical',
}


# ── CORE PULSE DISPATCH ────────────────────────────────────────────────────
# Called once location is confirmed or timed out.
# This is the single function that actually fires all alerts.

def dispatch_pulse(
    phone_hash,
    zone,
    landmark,
    carrier,
    location_confidence,
    location_source,
    network_code='',
    skip_incident_creation=False,
):
    """
    Fires the full PULSE alert sequence.
    Called after location is confirmed or timeout occurs.
    Creates the Critical incident and sends all SMS alerts.
    Returns the confirmation message for the sender.
    """
    now = timezone.now()

    # Find trusted contacts
    try:
        user = RegisteredUser.objects.prefetch_related(
            'trusted_contacts'
        ).get(phone_hash=phone_hash)
        contacts = list(user.trusted_contacts.all())
        user.last_pulse_at = now
        user.save(update_fields=['last_pulse_at'])
    except RegisteredUser.DoesNotExist:
        contacts = []

    # Build location label for alerts
    location_label = landmark if landmark else zone
    confidence_note = {
        'HIGH':   'Live location — GPS confirmed',
        'MEDIUM': 'Location confirmed by user',
        'LOW':    'Using registered fallback location',
    }.get(location_confidence, '')

    # Alert trusted contacts
    contact_alert = (
        f'SAFEPULSE ALERT — {now.strftime("%d %b %Y %H:%M")}\n\n'
        f'Someone you care about may need help.\n\n'
        f'Zone: {zone}\n'
        f'Landmark: {location_label}\n'
        f'Network: {carrier}\n'
        f'Location: {confidence_note}\n\n'
        f'Please check on them or contact\n'
        f'emergency services immediately.'
    )
    for contact in contacts:
        send_sms(contact.contact_phone, contact_alert)

    # Alert NGO in the zone
    ngos = NGOContact.objects.filter(zone__iexact=zone, is_active=True)
    ngo_alert = (
        f'SAFEPULSE NGO ALERT — {now.strftime("%d %b %Y %H:%M")}\n\n'
        f'Distress signal received in your zone.\n\n'
        f'Zone: {zone}\n'
        f'Landmark: {location_label}\n'
        f'Network: {carrier}\n'
        f'Location confidence: {location_confidence}\n\n'
        f'Please dispatch support immediately.\n'
        f'Case is live on your SafePulse dashboard.'
    )
    for ngo in ngos:
        send_sms(ngo.phone, ngo_alert)

    # Create Critical incident on dashboard
    notes = (
        f'PULSE triggered. Zone: {zone}. '
        f'Landmark: {location_label}. Carrier: {carrier}. '
        f'Confidence: {location_confidence}. '
        f'{len(contacts)} contact(s) notified.'
    )
    if not skip_incident_creation:
        Incident.objects.create(
            incident_date=now.date(),
            incident_time=now.time(),
            location=zone,
            incident_type='Unknown',
            severity_level='Critical',
            reporting_channel='SMS',
            follow_up_status='Ongoing',
            is_anonymous=True,
            notes=notes,
            location_confidence=location_confidence,
            location_source=location_source,
            last_verified_location=location_label,
        )

    return 'SafePulse: Help is on the way. Stay safe.'


# ── HANDLE_PULSE — Step 1 ─────────────────────────────────────────────────

def handle_pulse(from_number, network_code=''):
    """
    Command: PULSE
    Step 1 of the two-step flow.
    Creates a PulseSession and asks for location confirmation.
    If user is unregistered — fires immediately with LOW confidence.
    """
    phone_hash = hashlib.sha256(from_number.strip().encode()).hexdigest()
    carrier = carrier_from_code(network_code)
    now = timezone.now()

    # Check if user is registered
    try:
        user = RegisteredUser.objects.get(phone_hash=phone_hash)
    except RegisteredUser.DoesNotExist:
        # Unregistered — fire immediately, no confirmation step
        Incident.objects.create(
            incident_date=now.date(),
            incident_time=now.time(),
            location='Unknown',
            incident_type='Unknown',
            severity_level='Critical',
            reporting_channel='SMS',
            follow_up_status='Ongoing',
            is_anonymous=True,
            notes=f'PULSE from unregistered number. Carrier: {carrier}.',
            location_confidence='LOW',
            location_source='REGISTERED',
        )
        # Alert any available NGO
        ngos = NGOContact.objects.filter(is_active=True)[:1]
        for ngo in ngos:
            send_sms(ngo.phone, (
                f'SAFEPULSE ALERT — {now.strftime("%d %b %Y %H:%M")}\n\n'
                f'PULSE from unregistered number.\n'
                f'Carrier: {carrier}. No location on file.\n'
                f'Please review dashboard.'
            ))
        return (
            'SafePulse: Alert received.\n\n'
            'To register your location and\n'
            'trusted contacts so we can reach you,\n'
            'text 30333:\n\n'
            'REG Lagos Near blue gate Surulere'
        )

    # Close any existing open session for this user
    PulseSession.objects.filter(
        phone_hash=phone_hash,
        state__in=['WAITING_CONFIRM', 'WAITING_LANDMARK']
    ).update(state='TIMED_OUT')

    # Create new session — expires in 15 seconds
    PulseSession.objects.create(
        phone_hash=phone_hash,
        network_code=network_code,
        state='WAITING_CONFIRM',
        expires_at=now + timedelta(seconds=PulseSession.TIMEOUT_SECONDS),
    )

    return (
        f'SafePulse:\n'
        f'Are you at your registered location?\n\n'
        f'Zone: {user.registered_zone}\n'
        f'Landmark: {user.landmark or "None set"}\n\n'
        f'Reply YES or NO\n\n'
        f'No reply in 15 seconds =\n'
        f'alert sent automatically.'
    )


# ── HANDLE_PULSE_REPLY — Step 2 ───────────────────────────────────────────

def handle_pulse_reply(from_number, text, network_code=''):
    """
    Handles YES/NO replies and landmark updates during a PulseSession.
    Called from SMSReceiveView when an open session exists for this number.
    """
    phone_hash = hashlib.sha256(from_number.strip().encode()).hexdigest()
    carrier = carrier_from_code(network_code)
    text_upper = text.strip().upper()

    # Get open session
    try:
        session = PulseSession.objects.filter(
            phone_hash=phone_hash,
            state__in=['WAITING_CONFIRM', 'WAITING_LANDMARK']
        ).latest('created_at')
    except PulseSession.DoesNotExist:
        return None  # No open session — treat as normal message

    # Check if session has expired
    if session.is_expired():
        session.state = 'TIMED_OUT'
        session.save()
        # Fire timeout fallback
        return _fire_timeout_pulse(phone_hash, carrier, network_code)

    try:
        user = RegisteredUser.objects.get(phone_hash=phone_hash)
    except RegisteredUser.DoesNotExist:
        return None

    # ── State: WAITING_CONFIRM — user replied YES or NO ───────────────
    if session.state == 'WAITING_CONFIRM':

        if text_upper == 'YES':
            # User confirmed registered location
            session.state = 'COMPLETED'
            session.save()

            return dispatch_pulse(
                phone_hash=phone_hash,
                zone=user.registered_zone,
                landmark=user.landmark or user.registered_zone,
                carrier=carrier,
                location_confidence='MEDIUM',
                location_source='REGISTERED',
                network_code=network_code,
            )

        elif text_upper == 'NO':
            # Ask for current landmark
            session.state = 'WAITING_LANDMARK'
            session.expires_at = (
                timezone.now() +
                timedelta(seconds=PulseSession.TIMEOUT_SECONDS)
            )
            session.save()

            return (
                'SafePulse: Reply with your\n'
                'current landmark.\n\n'
                'Example:\n'
                'Near GTBank Ikeja\n\n'
                'No reply in 15 seconds =\n'
                'alert sent using registered location.'
            )

        else:
            # Unrecognised reply — treat as YES to avoid blocking
            session.state = 'COMPLETED'
            session.save()
            return dispatch_pulse(
                phone_hash=phone_hash,
                zone=user.registered_zone,
                landmark=user.landmark or user.registered_zone,
                carrier=carrier,
                location_confidence='LOW',
                location_source='REGISTERED',
                network_code=network_code,
            )

    # ── State: WAITING_LANDMARK — user sent their current location ────
    if session.state == 'WAITING_LANDMARK':
        updated_landmark = text.strip()

        # Update user's last known location
        user.last_known_location = updated_landmark
        user.last_location_update_at = timezone.now()
        user.last_location_source = 'SMS_UPDATE'
        user.save()

        session.state = 'COMPLETED'
        session.save()

        return dispatch_pulse(
            phone_hash=phone_hash,
            zone=user.registered_zone,
            landmark=updated_landmark,
            carrier=carrier,
            location_confidence='MEDIUM',
            location_source='SMS_UPDATE',
            network_code=network_code,
        )

    return None


# ── TIMEOUT FALLBACK ───────────────────────────────────────────────────────

def _fire_timeout_pulse(phone_hash, carrier, network_code=''):
    """
    Called when PulseSession expires without a reply.
    Uses registered location with LOW confidence.
    """
    try:
        user = RegisteredUser.objects.get(phone_hash=phone_hash)
        zone = user.registered_zone
        landmark = user.get_best_location()
    except RegisteredUser.DoesNotExist:
        zone = 'Unknown'
        landmark = 'None on file'

    dispatch_pulse(
        phone_hash=phone_hash,
        zone=zone,
        landmark=landmark,
        carrier=carrier,
        location_confidence='LOW',
        location_source='REGISTERED',
        network_code=network_code,
    )
    return 'SafePulse: Help is on the way. Stay safe.'


# ── REG ────────────────────────────────────────────────────────────────────

def handle_reg(from_number, parts, network_code=''):
    if len(parts) < 2:
        return (
            'SafePulse: To register, text:\n\n'
            'REG <your city> <your landmark>\n\n'
            'Example:\n'
            'REG Lagos Near blue gate Surulere'
        )

    zone = normalise_city(parts[1])
    landmark = ' '.join(parts[2:]) if len(parts) > 2 else ''
    carrier = carrier_from_code(network_code)
    phone_hash = hashlib.sha256(from_number.strip().encode()).hexdigest()

    user, created = RegisteredUser.objects.update_or_create(
        phone_hash=phone_hash,
        defaults={
            'registered_zone': zone,
            'landmark': landmark,
            'carrier_name': carrier,
            'network_code': str(network_code),
        }
    )

    action = 'now registered' if created else 'updated'

    return (
        f'SafePulse: You are {action}.\n\n'
        f'Zone: {zone}.\n'
        f'Landmark saved: {landmark or "None set"}.\n\n'
        f'Next step — add a trusted contact:\n'
        f'ADD Grace 08031234567 Sister'
    )


# ── ADD ────────────────────────────────────────────────────────────────────

def handle_add(from_number, parts):
    phone_hash = hashlib.sha256(from_number.strip().encode()).hexdigest()

    try:
        user = RegisteredUser.objects.get(phone_hash=phone_hash)
    except RegisteredUser.DoesNotExist:
        return (
            'SafePulse: Please register first.\n\n'
            'Text: REG <your city> <your landmark>\n\n'
            'Example:\n'
            'REG Lagos Near blue gate Surulere'
        )

    if len(parts) < 4:
        return (
            'SafePulse: Format:\n\n'
            'ADD <name> <number> <relation>\n\n'
            'Example:\n'
            'ADD Grace 08031234567 Sister'
        )

    if user.trusted_contacts.count() >= 5:
        return (
            'SafePulse: You already have 5 trusted contacts.\n'
            'That is the maximum allowed.'
        )

    name = parts[1]
    phone = parts[2]
    relationship = ' '.join(parts[3:])  

    TrustedContact.objects.create(
        registered_user=user,
        contact_name=name,
        contact_phone=phone,
        relationship=relationship,
    )

    count = user.trusted_contacts.count()

    if count == 1:
        return (
            f'SafePulse: {name} ({relationship}) added as trusted contact #1.\n\n'
            f'They will receive your location and landmark if you send PULSE.\n\n'
            f'To add another:\n'
            f'ADD Pastor James 08059876543 Community Leader\n\n'
            f'Or text PULSE anytime you need urgent help.'
        )

    return (
        f'SafePulse: {name} ({relationship}) added as trusted contact #{count}.\n\n'
        f'You now have {count} trusted contacts.\n'
        f'Text PULSE anytime you need urgent help.'
    )


# ── REPORT ─────────────────────────────────────────────────────────────────

def handle_report(from_number, parts):
    if len(parts) < 2:
        return (
            'SafePulse: To report, send:\n\n'
            'REPORT <type> <city> <severity>\n\n'
            'Types: DV SA H CA\n'
            'Severity: LOW MED HIGH CRIT\n\n'
            'Example:\n'
            'REPORT DV Lagos HIGH'
        )

    incident_type = INCIDENT_TYPE_MAP.get(parts[1].upper(), 'Domestic Violence')
    location = normalise_city(parts[2]) if len(parts) > 2 else 'Unknown'
    severity = SEVERITY_MAP.get(parts[3].upper(), 'High') if len(parts) > 3 else 'High'

    now = timezone.now()

    Incident.objects.create(
        incident_date=now.date(),
        incident_time=now.time(),
        location=location,
        incident_type=incident_type,
        severity_level=severity,
        reporting_channel='SMS',
        follow_up_status='Ongoing',
        is_anonymous=True,
        notes=f'Submitted via SMS. Raw: {" ".join(parts)}',
        location_confidence='LOW',
        location_source='REGISTERED',
    )

    return (
        'SafePulse: Report received. You are not alone.\n\n'
        'Your report has been logged anonymously.\n'
        'Reply TIPS for safety information.'
    )


# ── TIPS ───────────────────────────────────────────────────────────────────

def handle_tips():
    return (
        'SafePulse Safety Tips:\n\n'
        '1. Trust your instincts.\n'
        '2. Tell someone you trust.\n'
        '3. Know your nearest shelter.\n'
        '4. Keep important numbers saved.\n'
        '5. Have a safety plan ready.\n\n'
        'Text PULSE if you are in\n'
        'immediate danger.'
    )


# ── UNKNOWN ────────────────────────────────────────────────────────────────

def handle_unknown(original_text=''):
    greeting = (
        f'SafePulse: {original_text.capitalize()}. '
        if original_text else 'SafePulse: '
    )
    return (
        f'{greeting}Here are the available commands:\n\n'
        'PULSE — urgent help alert\n'
        'REG <city> <landmark> — register\n'
        'ADD <name> <number> <relation> — add trusted contact\n'
        'REPORT DV <city> HIGH — report an incident\n'
        'TIPS — safety information\n\n'
        'All messages are free. Shortcode: 30333'
    )