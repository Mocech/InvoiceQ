"""
InvoiceIQ URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    # Django admin
    path('admin/', admin.site.urls),
    # API routes
    path('api/auth/', include('apps.accounts.urls')),
    path('api/invoices/', include('apps.invoices.urls')),
    path('api/documents/', include('apps.documents.urls')),
    path('api/reports/', include('apps.reports.urls')),

    # API Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'), 

    # Frontend pages — serve HTML files directly
    path('', TemplateView.as_view(template_name='pages/login.html'), name='login'),
    path('register/', TemplateView.as_view(template_name='pages/register.html'), name='register'),
    path('dashboard/', TemplateView.as_view(template_name='pages/dashboard.html'), name='dashboard'),
    path('upload/', TemplateView.as_view(template_name='pages/upload.html'), name='upload'),
    path('processing/', TemplateView.as_view(template_name='pages/processing.html'), name='processing'),
    path('review/', TemplateView.as_view(template_name='pages/review.html'), name='review'),
    path('success/', TemplateView.as_view(template_name='pages/success.html'), name='success'),
    path('history/', TemplateView.as_view(template_name='pages/history.html'), name='history'),
    path('reports/', TemplateView.as_view(template_name='pages/reports.html'), name='reports'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
