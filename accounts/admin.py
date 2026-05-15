from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import NGOUser, Organisation


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'state', 'phone', 'is_active']
    list_filter = ['state', 'is_active']
    search_fields = ['name', 'city']


@admin.register(NGOUser)
class NGOUserAdmin(UserAdmin):
    list_display = ['username', 'organisation', 'role']
    list_filter = ['role', 'organisation__state']
    fieldsets = UserAdmin.fieldsets + (
        ('SafePulse Details', {
            'fields': ('organisation', 'role')
        }),
    )
