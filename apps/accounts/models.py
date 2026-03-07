"""
Accounts models — Custom User, Organization, Notification
"""

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Organization(models.Model):
    name = models.CharField(max_length=200)
    plan = models.CharField(
        max_length=20,
        choices=[
            ('starter', 'Starter'),
            ('pro', 'Pro'),
            ('enterprise', 'Enterprise'),
        ],
        default='starter'
    )
    storage_limit_gb = models.FloatField(default=10.0)
    invoice_limit_per_month = models.IntegerField(default=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'organizations'

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('reviewer', 'Reviewer'),
        ('viewer', 'Viewer'),
    ]

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='reviewer')
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members',
        null=True,
        blank=True
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        return f'{self.first_name} {self.last_name}'

    @property
    def avatar_initials(self):
        """Returns e.g. 'SK' for Sarah Jenkins"""
        return f'{self.first_name[:1]}{self.last_name[:1]}'.upper()

    @property
    def storage_used_gb(self):
        """Calculate total storage used by this user's organization"""
        from apps.documents.models import InvoiceDocument
        total_bytes = InvoiceDocument.objects.filter(
            invoice__organization=self.organization
        ).aggregate(
            total=models.Sum('file_size_bytes')
        )['total'] or 0
        return round(total_bytes / (1024 ** 3), 2)


class Notification(models.Model):
    TYPE_CHOICES = [
        ('invoice_processed', 'Invoice Processed'),
        ('review_required', 'Review Required'),
        ('invoice_flagged', 'Invoice Flagged'),
        ('invoice_approved', 'Invoice Approved'),
        ('invoice_rejected', 'Invoice Rejected'),
        ('system', 'System'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    message = models.TextField(blank=True)
    invoice_id = models.IntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.email} — {self.title}'

    @property
    def time_ago(self):
        from django.utils.timesince import timesince
        return timesince(self.created_at) + ' ago'
