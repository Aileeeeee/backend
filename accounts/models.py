from django.contrib.auth.models import AbstractUser
from django.db import models


class Organisation(models.Model):

    STATE_CHOICES = [
        ('Abia', 'Abia'), ('Abuja', 'Abuja (FCT)'), ('Adamawa', 'Adamawa'),
        ('Akwa Ibom', 'Akwa Ibom'), ('Anambra', 'Anambra'), ('Bauchi', 'Bauchi'),
        ('Bayelsa', 'Bayelsa'), ('Benue', 'Benue'), ('Borno', 'Borno'),
        ('Cross River', 'Cross River'), ('Delta', 'Delta'), ('Ebonyi', 'Ebonyi'),
        ('Edo', 'Edo'), ('Ekiti', 'Ekiti'), ('Enugu', 'Enugu'),
        ('Gombe', 'Gombe'), ('Imo', 'Imo'), ('Jigawa', 'Jigawa'),
        ('Kaduna', 'Kaduna'), ('Kano', 'Kano'), ('Katsina', 'Katsina'),
        ('Kebbi', 'Kebbi'), ('Kogi', 'Kogi'), ('Kwara', 'Kwara'),
        ('Lagos', 'Lagos'), ('Nasarawa', 'Nasarawa'), ('Niger', 'Niger'),
        ('Ogun', 'Ogun'), ('Ondo', 'Ondo'), ('Osun', 'Osun'),
        ('Oyo', 'Oyo'), ('Plateau', 'Plateau'), ('Rivers', 'Rivers'),
        ('Sokoto', 'Sokoto'), ('Taraba', 'Taraba'), ('Yobe', 'Yobe'),
        ('Zamfara', 'Zamfara'),
    ]

    name = models.CharField(max_length=200)
    state = models.CharField(max_length=50, choices=STATE_CHOICES)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True, default='')
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.name} — {self.city}, {self.state}'


class NGOUser(AbstractUser):

    ROLE_CHOICES = [
        ('COORDINATOR', 'NGO Coordinator'),
        ('FIELD_STAFF', 'Field Staff'),
        ('ADMIN', 'System Admin'),
    ]

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users'
    )
    role = models.CharField(max_length=15, choices=ROLE_CHOICES, default='FIELD_STAFF')
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        org = self.organisation.name if self.organisation else 'No organisation'
        return f'{self.username} — {org}'

    @property
    def coverage_area(self):
        return self.organisation.city if self.organisation else ''

    @property
    def organisation_name(self):
        return self.organisation.name if self.organisation else ''
