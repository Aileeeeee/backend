from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Organisation

User = get_user_model()


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'city', 'state', 'phone', 'email']


class SignupSerializer(serializers.ModelSerializer):
    first_name      = serializers.CharField(required=True)
    last_name       = serializers.CharField(required=True)
    username        = serializers.CharField(required=False, allow_blank=True)
    password        = serializers.CharField(write_only=True, min_length=8)
    organisation_id = serializers.IntegerField(write_only=True)

    class Meta:
        model  = User
        fields = [
            'first_name', 'last_name', 'username',
            'email', 'password', 'organisation_id', 'role'
        ]

    def validate_username(self, value):
        if value and User.objects.filter(username=value).exists():
            raise serializers.ValidationError(
                'This username is already taken.'
            )
        return value

    def create(self, validated_data):
        org_id       = validated_data.pop('organisation_id')
        organisation = Organisation.objects.get(id=org_id)
        first_name   = validated_data['first_name']
        last_name    = validated_data['last_name']

        # Use provided username or auto-generate
        username = validated_data.get('username', '').strip()
        if not username:
            import re
            base = f"{re.sub(r'[^a-z0-9]', '', first_name.lower())}.{re.sub(r'[^a-z0-9]', '', last_name.lower())}"
            username = base
            counter  = 1
            while User.objects.filter(username=username).exists():
                username = f"{base}{counter}"
                counter += 1

        user = User.objects.create_user(
            username      = username,
            email         = validated_data['email'],
            password      = validated_data['password'],
            first_name    = first_name,
            last_name     = last_name,
            organisation  = organisation,
            role          = validated_data.get('role', 'FIELD_STAFF'),
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    organisation = OrganisationSerializer(read_only=True)

    class Meta:
        model  = User
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'email', 'organisation', 'role', 'created_at'
        ]
        read_only_fields = ['id', 'username', 'created_at']

class OrganisationSerializer(serializers.ModelSerializer):
    label = serializers.CharField(source="name", read_only=True)
    value = serializers.IntegerField(source="id", read_only=True)

    class Meta:
        model = Organisation
        fields = ["id","name","city","state","label","value",]
