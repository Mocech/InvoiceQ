"""
Invoices models — Invoice, LineItem, ExtractedField, AuditLog
"""

from django.db import models
from django.conf import settings


class Invoice(models.Model):

    STATUS_UPLOADING       = 'uploading'
    STATUS_PROCESSING      = 'processing'
    STATUS_PENDING_REVIEW  = 'pending_review'
    STATUS_APPROVED        = 'approved'
    STATUS_REJECTED        = 'rejected'
    STATUS_FLAGGED         = 'flagged'
    STATUS_ARCHIVED        = 'archived'

    STATUS_CHOICES = [
        (STATUS_UPLOADING,      'Uploading'),
        (STATUS_PROCESSING,     'Processing'),
        (STATUS_PENDING_REVIEW, 'Pending Review'),
        (STATUS_APPROVED,       'Approved'),
        (STATUS_REJECTED,       'Rejected'),
        (STATUS_FLAGGED,        'Flagged'),
        (STATUS_ARCHIVED,       'Archived'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'US Dollar'),
        ('KES', 'Kenyan Shilling'),
        ('EUR', 'Euro'),
        ('GBP', 'British Pound'),
        ('ZAR', 'South African Rand'),
    ]

    # ── Identity ─────────────────────────────────────────────────────────────
    invoice_number  = models.CharField(max_length=100, blank=True)
    vendor_name     = models.CharField(max_length=200, blank=True)
    vendor_address  = models.TextField(blank=True)
    vendor_email    = models.EmailField(blank=True)
    vendor_phone    = models.CharField(max_length=50, blank=True)
    po_number       = models.CharField(max_length=100, blank=True, verbose_name='PO Number')
    payment_terms   = models.CharField(max_length=100, blank=True)

    # ── Financials ───────────────────────────────────────────────────────────
    subtotal_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    tax_amount      = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    total_amount    = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency        = models.CharField(max_length=10, choices=CURRENCY_CHOICES, default='USD')

    # ── Dates ────────────────────────────────────────────────────────────────
    invoice_date    = models.DateField(null=True, blank=True)
    due_date        = models.DateField(null=True, blank=True)
    uploaded_at     = models.DateTimeField(auto_now_add=True)
    processed_at    = models.DateTimeField(null=True, blank=True)
    reviewed_at     = models.DateTimeField(null=True, blank=True)

    # ── Status ───────────────────────────────────────────────────────────────
    status          = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPLOADING)

    # ── AI Metadata ──────────────────────────────────────────────────────────
    ai_confidence_score     = models.FloatField(null=True, blank=True)
    ai_processing_time_ms   = models.IntegerField(null=True, blank=True)
    ai_flag_message         = models.TextField(blank=True)
    ai_model_used           = models.CharField(max_length=100, blank=True)

    # ── Processing progress (for polling) ────────────────────────────────────
    processing_progress     = models.IntegerField(default=0)   # 0-100
    processing_current_step = models.IntegerField(default=1)   # 1-4
    processing_error        = models.TextField(blank=True)

    # ── Relationships ────────────────────────────────────────────────────────
    uploaded_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_invoices'
    )
    reviewed_by     = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_invoices'
    )
    organization    = models.ForeignKey(
        'accounts.Organization',
        on_delete=models.CASCADE,
        related_name='invoices',
        null=True
    )

    class Meta:
        db_table = 'invoices'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f'{self.invoice_number or "INV-???"} — {self.vendor_name or "Unknown"}'

    @property
    def confidence_level(self):
        """Returns 'high', 'medium', or 'low' based on AI score"""
        if self.ai_confidence_score is None:
            return 'unknown'
        if self.ai_confidence_score >= 0.85:
            return 'high'
        if self.ai_confidence_score >= 0.60:
            return 'medium'
        return 'low'

    @property
    def needs_review(self):
        return self.status == self.STATUS_PENDING_REVIEW

    @property
    def display_status(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status)


class LineItem(models.Model):
    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='line_items')
    description = models.CharField(max_length=500)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price  = models.DecimalField(max_digits=14, decimal_places=2)
    total       = models.DecimalField(max_digits=14, decimal_places=2)
    ai_confidence = models.FloatField(default=1.0)
    sort_order  = models.IntegerField(default=0)

    class Meta:
        db_table = 'invoice_line_items'
        ordering = ['sort_order']

    def __str__(self):
        return f'{self.invoice.invoice_number} — {self.description[:50]}'


class ExtractedField(models.Model):
    """
    Stores each AI-extracted field with its individual confidence score.
    Drives the green/yellow badge display on the review page.
    """
    invoice         = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='extracted_fields')
    field_name      = models.CharField(max_length=100)      # e.g. "vendor_name", "total_amount"
    field_label     = models.CharField(max_length=100)      # e.g. "Vendor Name", "Total Amount"
    extracted_value = models.TextField()
    confidence_score = models.FloatField()                  # 0.0 – 1.0

    # When reviewer manually corrects a field
    manually_corrected  = models.BooleanField(default=False)
    corrected_value     = models.TextField(blank=True)
    corrected_by        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    corrected_at        = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'extracted_fields'
        unique_together = ('invoice', 'field_name')

    def __str__(self):
        return f'{self.invoice.invoice_number} — {self.field_name}: {self.extracted_value}'

    @property
    def effective_value(self):
        """Returns corrected value if reviewer changed it, else AI value"""
        return self.corrected_value if self.manually_corrected else self.extracted_value

    @property
    def confidence_label(self):
        if self.confidence_score >= 0.85:
            return 'high'
        if self.confidence_score >= 0.60:
            return 'medium'
        return 'low'

    @property
    def confidence_percent(self):
        return round(self.confidence_score * 100)

class AuditLog(models.Model):
    """
    Immutable audit trail — every action on every invoice is recorded.
    Required for the enterprise compliance features (Audit Logs page).
    """
    ACTION_CHOICES = [
        ('uploaded',          'Uploaded'),
        ('processing_started','Processing Started'),
        ('processing_complete','Processing Complete'),
        ('processing_failed', 'Processing Failed'),
        ('field_viewed',      'Field Viewed'),
        ('field_corrected',   'Field Corrected'),
        ('approved',          'Approved'),
        ('rejected',          'Rejected'),
        ('flagged',           'Flagged for Review'),
        ('exported_csv',      'Exported as CSV'),
        ('exported_json',     'Exported as JSON'),
        ('exported_excel',    'Exported as Excel'),   # ← ADDED
        ('exported_pdf',      'Exported as PDF'),     # ← ADDED
        ('sent_to_accounting','Sent to Accounting'),
        ('archived',          'Archived'),
        ('deleted',           'Deleted'),
    ]

    invoice     = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='audit_logs')
    user        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    action      = models.CharField(max_length=30, choices=ACTION_CHOICES)
    detail      = models.JSONField(default=dict)    # stores old/new values for field corrections
    timestamp   = models.DateTimeField(auto_now_add=True)
    ip_address  = models.GenericIPAddressField(null=True, blank=True)
    user_agent  = models.TextField(blank=True)

    class Meta:
        db_table = 'audit_logs'
        ordering = ['-timestamp']

    def __str__(self):
        return f'{self.invoice.invoice_number} — {self.action} by {self.user}'