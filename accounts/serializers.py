from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Organisation

User = get_user_model()


class OrganisationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organisation
        fields = ['id', 'name', 'city', 'state', 'phone', 'email']


class SignupSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    organisation_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'organisation_id', 'role']

    def validate_organisation_id(self, value):
        try:
            Organisation.objects.get(id=value)
        except Organisation.DoesNotExist:
            raise serializers.ValidationError('Organisation not found.')
        return value

    def create(self, validated_data):
        org_id = validated_data.pop('organisation_id')
        organisation = Organisation.objects.get(id=org_id)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password'],
            organisation=organisation,
            role=validated_data.get('role', 'FIELD_STAFF'),
        )
        return user


class UserProfileSerializer(serializers.ModelSerializer):
    organisation = OrganisationSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'organisation', 'role', 'created_at']
        read_only_fields = ['id', 'created_at']