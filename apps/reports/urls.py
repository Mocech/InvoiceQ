from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/',  views.dashboard_stats,  name='reports-dashboard'),
    path('analytics/',  views.analytics,         name='reports-analytics'),
    path('business/',   views.business_report,   name='business_report'),
]