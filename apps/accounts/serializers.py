"""
Accounts serializers — JWT customization, user profile, notifications
"""

from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from .models import Notification, Organization

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends the default JWT login to include user info in the response.
    This means the frontend gets everything it needs in one login call.
    """

    def validate(self, attrs):
        data = super().validate(attrs)

        # Add user profile data to the token response
        data['user'] = {
            'id': self.user.id,
            'email': self.user.email,
            'full_name': self.user.full_name,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'avatar_initials': self.user.avatar_initials,
            'role': self.user.role,
            'organization': self.user.organization.name if self.user.organization else None,
            'plan': self.user.organization.plan if self.user.organization else 'starter',
            'storage_used_gb': self.user.storage_used_gb,
            'storage_limit_gb': (
                self.user.organization.storage_limit_gb
                if self.user.organization else 10.0
            ),
        }

        return data


class UserProfileSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    avatar_initials = serializers.ReadOnlyField()
    storage_used_gb = serializers.ReadOnlyField()
    organization_name = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    storage_limit_gb = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name',
            'avatar_initials', 'role', 'organization_name', 'plan',
            'storage_used_gb', 'storage_limit_gb', 'date_joined',
        ]
        read_only_fields = ['id', 'email', 'date_joined']

    def get_organization_name(self, obj):
        return obj.organization.name if obj.organization else None

    def get_plan(self, obj):
        return obj.organization.plan if obj.organization else 'starter'

    def get_storage_limit_gb(self, obj):
        return obj.organization.storage_limit_gb if obj.organization else 10.0


class NotificationSerializer(serializers.ModelSerializer):
    time_ago = serializers.ReadOnlyField()

    class Meta:
        model = Notification
        fields = [
            'id', 'type', 'title', 'message',
            'invoice_id', 'is_read', 'created_at', 'time_ago'
        ]
        read_only_fields = ['id', 'created_at']
