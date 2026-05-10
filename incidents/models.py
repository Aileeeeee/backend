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

    class Meta:
        ordering = ['-incident_date', '-incident_time']

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
 
    def __str__(self):
        return f'User [{self.phone_hash[:8]}...] — {self.registered_zone}'

    
class TrustedContact(models.Model):

    registered_user = models.ForeignKey(RegisteredUser, on_delete=models.CASCADE,
                                         related_name='trusted_contacts')
    contact_phone   = models.CharField(max_length=20)   # Plain number — we need to SMS them
    contact_name    = models.CharField(max_length=100)  # e.g. Grace
    relationship    = models.CharField(max_length=50)   # e.g. Sister
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
