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
    password        = serializers.CharField(write_only=True, min_length=8)
    organisation_id = serializers.IntegerField(write_only=True)

    class Meta:
        model  = User
        fields = ['first_name', 'last_name', 'email', 'password', 'organisation_id', 'role']

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value

    def validate_organisation_id(self, value):
        try:
            Organisation.objects.get(id=value)
        except Organisation.DoesNotExist:
            raise serializers.ValidationError('Organisation not found.')
        return value

    def create(self, validated_data):
        org_id       = validated_data.pop('organisation_id')
        organisation = Organisation.objects.get(id=org_id)
        first_name   = validated_data['first_name']
        last_name    = validated_data['last_name']

        # Auto-generate username from first + last name
        # e.g. "Adaeze Okafor" → "adaeze.okafor"
        # If taken, add a number: "adaeze.okafor1"
        base_username = f"{first_name.lower()}.{last_name.lower()}"
        base_username = base_username.replace(" ", "")
        username      = base_username
        counter       = 1
        while User.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
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