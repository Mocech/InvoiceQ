from django.urls import path
from . import views

urlpatterns = [
    path('<int:invoice_pk>/preview/', views.document_preview, name='document-preview'),
]
