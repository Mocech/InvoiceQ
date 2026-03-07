from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('login/',            views.LoginView.as_view(),               name='auth-login'),
    path('register/',       views.register,             name='auth-register'), 
    path('logout/',           views.LogoutView.as_view(),              name='auth-logout'),
    path('refresh/',          TokenRefreshView.as_view(),              name='auth-refresh'),
    path('me/',               views.MeView.as_view(),                  name='auth-me'),
    path('notifications/',              views.NotificationListView.as_view(),    name='notifications-list'),
    path('notifications/read-all/',     views.mark_all_notifications_read,       name='notifications-read-all'),
    path('notifications/<int:pk>/',     views.mark_notification_read,            name='notification-detail'),
]
