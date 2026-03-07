from django.contrib import admin
from .models import InvoiceDocument


@admin.register(InvoiceDocument)
class InvoiceDocumentAdmin(admin.ModelAdmin):
    list_display  = ['invoice', 'file_name', 'file_size_mb', 'file_type',
                     'ocr_provider', 'ocr_data_points_found', 'uploaded_at']
    list_filter   = ['file_type', 'ocr_provider']
    search_fields = ['invoice__invoice_number', 'file_name']
    readonly_fields = ['uploaded_at', 'ocr_completed_at', 'file_size_bytes']
