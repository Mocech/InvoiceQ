from django.urls import path
from . import views

urlpatterns = [
    path('',                             views.InvoiceListView.as_view(),   name='invoice-list'),
    path('upload/',                      views.upload_invoice,              name='invoice-upload'),
    path('<int:pk>/status/',             views.invoice_status,              name='invoice-status'),
    path('<int:pk>/approve/',            views.approve_invoice,             name='invoice-approve'),
    path('<int:pk>/reject/',             views.reject_invoice,              name='invoice-reject'),
    path('<int:pk>/flag/',               views.flag_invoice,                name='invoice-flag'),
    path('<int:pk>/export/',             views.export_invoice,              name='invoice-export'),
    path('<int:pk>/send-to-accounting/', views.send_to_accounting,         name='invoice-accounting'),
    path('<int:pk>/',                    views.InvoiceDetailView.as_view(), name='invoice-detail'),
]
# + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
