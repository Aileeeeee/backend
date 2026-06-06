from django.contrib import admin
from incidents.models import Incident, RegisteredUser, TrustedContact, NGOContact, PulseSession


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display  = ['id', 'incident_type', 'location', 'severity_level',
                     'follow_up_status', 'reporting_channel', 'location_confidence',
                     'is_acknowledged', 'incident_date']
    list_filter   = ['severity_level', 'follow_up_status', 'reporting_channel',
                     'incident_type', 'location_confidence', 'is_acknowledged']
    search_fields = ['location', 'notes', 'last_verified_location']
    readonly_fields = ['created_at', 'updated_at', 'acknowledged_at']


@admin.register(RegisteredUser)
class RegisteredUserAdmin(admin.ModelAdmin):
    list_display  = ['id', 'registered_zone', 'carrier_name', 'last_known_location',
                     'last_location_source', 'registered_at', 'last_pulse_at']
    list_filter   = ['carrier_name', 'last_location_source']
    search_fields = ['registered_zone', 'landmark', 'last_known_location']
    readonly_fields = ['registered_at', 'last_pulse_at', 'last_location_update_at']


@admin.register(TrustedContact)
class TrustedContactAdmin(admin.ModelAdmin):
    list_display  = ['id', 'contact_name', 'relationship', 'contact_phone', 'added_at']
    search_fields = ['contact_name', 'relationship']


@admin.register(NGOContact)
class NGOContactAdmin(admin.ModelAdmin):
    list_display  = ['id', 'org_name', 'zone', 'phone', 'is_active']
    list_filter   = ['is_active', 'zone']
    search_fields = ['org_name', 'zone']


@admin.register(PulseSession)
class PulseSessionAdmin(admin.ModelAdmin):
    list_display  = ['id', 'phone_hash', 'state', 'created_at', 'expires_at']
    list_filter   = ['state']
    readonly_fields = ['created_at']