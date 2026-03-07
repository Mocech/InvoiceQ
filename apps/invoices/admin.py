from django.contrib import admin
from .models import Invoice, LineItem, ExtractedField, AuditLog


class LineItemInline(admin.TabularInline):
    model = LineItem
    extra = 0
    readonly_fields = ['ai_confidence']


class ExtractedFieldInline(admin.TabularInline):
    model = ExtractedField
    extra = 0
    readonly_fields = ['field_name', 'field_label', 'extracted_value',
                       'confidence_score', 'manually_corrected']


class AuditLogInline(admin.TabularInline):
    model = AuditLog
    extra = 0
    readonly_fields = ['user', 'action', 'detail', 'timestamp', 'ip_address']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display  = ['invoice_number', 'vendor_name', 'total_amount', 'currency',
                     'status', 'ai_confidence_score', 'uploaded_at', 'uploaded_by']
    list_filter   = ['status', 'currency', 'organization']
    search_fields = ['invoice_number', 'vendor_name', 'po_number']
    ordering      = ['-uploaded_at']
    readonly_fields = ['uploaded_at', 'processed_at', 'reviewed_at',
                       'processing_progress', 'processing_current_step']
    inlines = [LineItemInline, ExtractedFieldInline, AuditLogInline]

    fieldsets = (
        ('Identity',    {'fields': ('invoice_number', 'vendor_name', 'vendor_address',
                                    'vendor_email', 'vendor_phone', 'po_number', 'payment_terms')}),
        ('Financials',  {'fields': ('subtotal_amount', 'tax_amount', 'total_amount', 'currency')}),
        ('Dates',       {'fields': ('invoice_date', 'due_date', 'uploaded_at',
                                    'processed_at', 'reviewed_at')}),
        ('Status',      {'fields': ('status', 'processing_progress', 'processing_current_step',
                                    'processing_error')}),
        ('AI',          {'fields': ('ai_confidence_score', 'ai_processing_time_ms',
                                    'ai_flag_message', 'ai_model_used')}),
        ('Relations',   {'fields': ('uploaded_by', 'reviewed_by', 'organization')}),
    )


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display  = ['invoice', 'user', 'action', 'timestamp', 'ip_address']
    list_filter   = ['action']
    search_fields = ['invoice__invoice_number', 'user__email']
    readonly_fields = ['invoice', 'user', 'action', 'detail', 'timestamp', 'ip_address']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
