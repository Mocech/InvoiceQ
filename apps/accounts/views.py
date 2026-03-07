"""
Accounts views — login, logout, profile, notifications
"""

from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model

from .serializers import (
    CustomTokenObtainPairSerializer,
    UserProfileSerializer,
    NotificationSerializer,
)
from .models import Notification

User = get_user_model()


@api_view(['POST'])
def register(request):
    """
    POST /api/auth/register/
    Creates a new user + organization in one step.
    Returns JWT tokens so the user is immediately logged in.

    Body:
    {
        "first_name":        "Moses",
        "last_name":         "Mulwa",
        "email":             "moses@company.com",
        "password":          "securepassword123",
        "organization_name": "Acme Corporation",
        "role":              "admin",       # optional, defaults to admin
        "industry":          "retail"       # optional
    }
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    from apps.accounts.models import Organization

    data = request.data

    # ── Required fields ───────────────────────────────────────────────────
    first_name = (data.get('first_name') or '').strip()
    last_name  = (data.get('last_name')  or '').strip()
    email      = (data.get('email')      or '').strip().lower()
    password   = data.get('password', '')
    org_name   = (data.get('organization_name') or '').strip()

    # ── Validation ────────────────────────────────────────────────────────
    errors = {}
    if not first_name:
        errors['first_name'] = 'First name is required.'
    if not last_name:
        errors['last_name'] = 'Last name is required.'
    if not email:
        errors['email'] = 'Email is required.'
    elif User.objects.filter(email=email).exists():
        errors['email'] = 'An account with this email already exists.'
    if not password:
        errors['password'] = 'Password is required.'
    elif len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'
    if not org_name:
        errors['organization_name'] = 'Organisation name is required.'

    if errors:
        return Response(errors, status=status.HTTP_400_BAD_REQUEST)

    # ── Create organization ───────────────────────────────────────────────
    # Check if org with this name already exists — if so, don't duplicate
    org, org_created = Organization.objects.get_or_create(
        name=org_name,
        defaults={
            'industry': data.get('industry', ''),
        }
    )

    # ── Create user ───────────────────────────────────────────────────────
    role = data.get('role', 'admin')
    # Validate role against allowed choices
    allowed_roles = ['admin', 'manager', 'reviewer', 'viewer']
    if role not in allowed_roles:
        role = 'admin'

    user = User.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        organization=org,
        role=role,
    )

    # ── Issue JWT tokens ──────────────────────────────────────────────────
    refresh = RefreshToken.for_user(user)

    return Response({
        'access':  str(refresh.access_token),
        'refresh': str(refresh),
        'user': {
            'id':               user.id,
            'email':            user.email,
            'full_name':        user.get_full_name(),
            'role':             user.role,
            'organization':     org.name,
            'avatar_initials':  (first_name[0] + last_name[0]).upper() if first_name and last_name else 'U',
        }
    }, status=status.HTTP_201_CREATED)


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    Body: { "email": "...", "password": "..." }
    Returns: { "access": "...", "refresh": "...", "user": {...} }
    """
    serializer_class = CustomTokenObtainPairSerializer
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)

        # Record the login IP for audit purposes
        if response.status_code == 200:
            try:
                from rest_framework_simplejwt.tokens import UntypedToken
                UntypedToken(response.data['access'])
                ip = self._get_client_ip(request)
                email = request.data.get('email')
                User.objects.filter(email=email).update(last_login_ip=ip)
            except Exception:
                pass

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


class LogoutView(generics.GenericAPIView):
    """
    POST /api/auth/logout/
    Body: { "refresh": "..." }
    Blacklists the refresh token so it can't be reused.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response(
                    {'error': 'Refresh token is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logged out successfully'})
        except TokenError:
            return Response(
                {'error': 'Invalid or expired token'},
                status=status.HTTP_400_BAD_REQUEST
            )


class MeView(generics.RetrieveUpdateAPIView):
    """
    GET  /api/auth/me/   — Returns current user profile
    PATCH /api/auth/me/  — Update profile fields
    """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class NotificationListView(generics.ListAPIView):
    """
    GET /api/notifications/
    Returns last 10 unread notifications for the bell dropdown.
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(
            user=self.request.user,
            is_read=False
        )[:10]

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'notifications': serializer.data,
            'unread_count': queryset.count(),
        })


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    """
    PATCH /api/notifications/{id}/
    Marks a single notification as read.
    """
    try:
        notification = Notification.objects.get(pk=pk, user=request.user)
        notification.is_read = True
        notification.save()
        return Response({'message': 'Marked as read'})
    except Notification.DoesNotExist:
        return Response(
            {'error': 'Notification not found'},
            status=status.HTTP_404_NOT_FOUND
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    """
    POST /api/notifications/read-all/
    Marks all notifications as read.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({'message': 'All notifications marked as read'})
