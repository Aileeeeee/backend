from django.db import models

# Create your models here.

class Incident(models.Model):

    # Define Incident report options
    INCIDENT_TYPES = [
        ('Domestic Violence', 'Domestic Violence'),
        ('Sexual Assault',    'Sexual Assault'),
        ('Harassment',        'Harassment'),
        ('Child Abuse',       'Child Abuse'),
        ('Unknown',           'Unknown'),   # Used when PULSE arrives with no type info
    ]
    SEVERITY_LEVELS = [
        ('Low',      'Low'),
        ('Medium',   'Medium'),
        ('High',     'High'),
        ('Critical', 'Critical'),
    ]
    REPORTING_CHANNELS = [
        ('Mobile App',       'Mobile App'),
        ('Hotline',          'Hotline'),
        ('Community Center', 'Community Center'),
        ('Dashboard',        'Dashboard'),
        ('SMS',              'SMS'),
        ('USSD',             'USSD'),
    ]
    FOLLOW_UP_STATUS = [
        ('Ongoing', 'Ongoing'),
        ('Closed',  'Closed'),
    ]
    
    # Location confidence 
    LOCATION_CONFIDENCE = [
        ('HIGH',   'High — live GPS or confirmed'),
        ('MEDIUM', 'Medium — user confirmed recently'),
        ('LOW',    'Low — registered fallback only'),
    ]
    LOCATION_SOURCE = [
        ('GPS',         'GPS — mobile app'),
        ('REGISTERED',  'Registered fallback'),
        ('SMS_UPDATE',  'Updated via SMS'),
        ('USSD_UPDATE', 'Updated via USSD'),
    ]

     # Fields filled by the server
    incident_date     = models.DateField()
    incident_time     = models.TimeField()
    reporting_channel = models.CharField(max_length=50, choices=REPORTING_CHANNELS)
    follow_up_status  = models.CharField(max_length=30, choices=FOLLOW_UP_STATUS, default='Ongoing')
    is_anonymous      = models.BooleanField(default=True)
    created_at        = models.DateTimeField(auto_now_add=True)
    updated_at        = models.DateTimeField(auto_now=True)

     # Fields from SMS REPORT command (or app) ---
    location          = models.CharField(max_length=100, db_index=True)
    incident_type     = models.CharField(max_length=50, choices=INCIDENT_TYPES, db_index=True)
    severity_level    = models.CharField(max_length=20, choices=SEVERITY_LEVELS, db_index=True)

    # Fields only the app can provide — optional for SMS 
    victim_age               = models.PositiveIntegerField(null=True, blank=True)
    victim_gender            = models.CharField(max_length=20, blank=True, default='Unknown')
    perpetrator_relationship = models.CharField(max_length=50, blank=True, default='Unknown')
    support_provided         = models.CharField(max_length=50, blank=True, default='')
    notes                    = models.TextField(blank=True, default='')

    # Acknowledge fields 
    is_acknowledged = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    # location confidence fields 
    location_confidence = models.CharField(max_length=10, choices=LOCATION_CONFIDENCE,default='LOW', blank=True)
    location_source = models.CharField(max_length=15, choices=LOCATION_SOURCE,default='REGISTERED', blank=True)
    last_verified_location  = models.TextField(blank=True, default='')

    latitude          = models.FloatField(null=True, blank=True)
    longitude         = models.FloatField(null=True, blank=True)
    location_accuracy = models.FloatField(null=True, blank=True)
    reporter_type     = models.CharField(
        max_length=20,
        choices=[('victim', 'Victim'), ('bystander', 'Bystander')],
        default='victim',
        blank=True,
    )

    class Meta:
        ordering = ['-incident_date', '-incident_time']

        indexes = [
        models.Index(fields=['location', 'incident_date']),
        models.Index(fields=['severity_level', 'follow_up_status']),
    ]

    def __str__(self):
        return f" [{self.id}] {self.incident_type} - {self.location} ({self.incident_date})]"
    
class RegisteredUser(models.Model):
    phone_hash      = models.CharField(max_length=64, unique=True)  
    registered_zone = models.CharField(max_length=100)             
    landmark        = models.TextField(blank=True, default='')     
    carrier_name    = models.CharField(max_length=100, blank=True) 
    network_code    = models.CharField(max_length=20,  blank=True) 
    registered_at   = models.DateTimeField(auto_now_add=True)
    last_pulse_at   = models.DateTimeField(null=True, blank=True)

    # location tracking fields 
    last_known_location     = models.TextField(blank=True, default='')
    last_location_update_at = models.DateTimeField(null=True, blank=True)
    last_location_source    = models.CharField(max_length=15,choices=[
            ('GPS', 'GPS'), ('SMS_UPDATE', 'SMS Update'),
            ('USSD_UPDATE', 'USSD Update'), ('REGISTERED', 'Registered'),
        ],
        default='REGISTERED', blank=True)
 
    NETWORK_CODE_MAP = {
        '62120': 'Airtel Nigeria',
        '62130': 'MTN Nigeria',
        '62150': 'Globacom (Glo)',
        '62160': '9mobile',
    }
 
    @classmethod
    def hash_phone(cls, phone_number):
        import hashlib
        return hashlib.sha256(phone_number.strip().encode()).hexdigest()
 
    @classmethod
    def carrier_from_code(cls, code):
        return cls.NETWORK_CODE_MAP.get(str(code), 'Unknown')
 
    def get_best_location(self):
        if self.last_known_location:
            return self.last_known_location
        return self.landmark or self.registered_zone

    def __str__(self):
        return f'User [{self.phone_hash[:8]}...] — {self.registered_zone}'

    
class TrustedContact(models.Model):

    registered_user = models.ForeignKey(RegisteredUser, on_delete=models.CASCADE,
                                         related_name='trusted_contacts')
    contact_phone   = models.CharField(max_length=20)   # Plain number — we need to SMS them
    contact_name    = models.CharField(max_length=100)  # e.g. Grace
    contact_gender =  models.CharField(max_length=100,null=True, blank=True)  # e.g. Female
    relationship    = models.CharField(max_length=50,null=True, blank=True)   # e.g. Sister
    added_at        = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f'{self.contact_name} ({self.relationship})'
 

class NGOContact(models.Model):
    
    zone     = models.CharField(max_length=100)   
    org_name = models.CharField(max_length=200)   
    phone    = models.CharField(max_length=20)    
    is_active = models.BooleanField(default=True)
 
    def __str__(self):
        return f'{self.org_name} — {self.zone}'

class PulseSession(models.Model):
    TIMEOUT_SECONDS = 15

    STATE_CHOICES = [
        ('WAITING_CONFIRM',  'Waiting for YES/NO'),
        ('WAITING_LANDMARK', 'Waiting for landmark update'),
        ('COMPLETED',        'Completed'),
        ('TIMED_OUT',        'Timed out'),
    ]

    phone_hash      = models.CharField(max_length=64, db_index=True)
    network_code    = models.CharField(max_length=20, blank=True)
    state           = models.CharField(max_length=20, choices=STATE_CHOICES,default='WAITING_CONFIRM')
    created_at      = models.DateTimeField(auto_now_add=True)
    expires_at      = models.DateTimeField()

    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def __str__(self):
        return f'PulseSession [{self.phone_hash[:8]}...] — {self.state}'