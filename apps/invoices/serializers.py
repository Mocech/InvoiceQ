"""
Invoice serializers — list, detail, review, audit log
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Invoice, LineItem, ExtractedField, AuditLog


class LineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = LineItem
        fields = ['id', 'description', 'quantity', 'unit_price', 'total', 'ai_confidence', 'sort_order']


class ExtractedFieldSerializer(serializers.ModelSerializer):
    confidence_label   = serializers.ReadOnlyField()
    confidence_percent = serializers.ReadOnlyField()
    effective_value    = serializers.ReadOnlyField()

    class Meta:
        model = ExtractedField
        fields = [
            'id', 'field_name', 'field_label',
            'extracted_value', 'confidence_score',
            'confidence_label', 'confidence_percent', 'effective_value',
            'manually_corrected', 'corrected_value', 'corrected_at',
        ]
        read_only_fields = ['id', 'field_name', 'field_label', 'extracted_value',
                            'confidence_score', 'manually_corrected', 'corrected_at']


class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = ['id', 'action', 'detail', 'timestamp', 'user_name', 'ip_address']

    def get_user_name(self, obj):
        return obj.user.full_name if obj.user else 'System'


# ── Invoice list (compact — used in history table and dashboard) ─────────────

class InvoiceListSerializer(serializers.ModelSerializer):
    confidence_level    = serializers.ReadOnlyField()
    display_status      = serializers.ReadOnlyField()
    uploaded_by_name    = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'vendor_name',
            'total_amount', 'currency',
            'invoice_date', 'due_date', 'uploaded_at',
            'status', 'display_status',
            'ai_confidence_score', 'confidence_level',
            'ai_flag_message', 'uploaded_by_name',
        ]

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.full_name if obj.uploaded_by else None


# ── Invoice detail (full — used on review page) ──────────────────────────────

class InvoiceDetailSerializer(serializers.ModelSerializer):
    line_items          = LineItemSerializer(many=True, read_only=True)
    extracted_fields    = ExtractedFieldSerializer(many=True, read_only=True)
    audit_logs          = AuditLogSerializer(many=True, read_only=True)
    confidence_level    = serializers.ReadOnlyField()
    display_status      = serializers.ReadOnlyField()
    uploaded_by_name    = serializers.SerializerMethodField()
    reviewed_by_name    = serializers.SerializerMethodField()
    document_preview_url = serializers.SerializerMethodField()
    overall_confidence_summary = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'invoice_number', 'vendor_name', 'vendor_address',
            'vendor_email', 'vendor_phone', 'po_number', 'payment_terms',
            'subtotal_amount', 'tax_amount', 'total_amount', 'currency',
            'invoice_date', 'due_date', 'uploaded_at', 'processed_at', 'reviewed_at',
            'status', 'display_status',
            'ai_confidence_score', 'confidence_level',
            'ai_flag_message', 'ai_model_used', 'ai_processing_time_ms',
            'uploaded_by_name', 'reviewed_by_name',
            'line_items', 'extracted_fields', 'audit_logs',
            'document_preview_url', 'overall_confidence_summary',
        ]

    def get_uploaded_by_name(self, obj):
        return obj.uploaded_by.full_name if obj.uploaded_by else None

    def get_reviewed_by_name(self, obj):
        return obj.reviewed_by.full_name if obj.reviewed_by else None

    def get_document_preview_url(self, obj):
        try:
            request = self.context.get('request')
            url = obj.document.original_file.url
            if request:
                return request.build_absolute_uri(url)
            return url
        except Exception:
            return None

    def get_overall_confidence_summary(self, obj):
        """Drives the 'Overall Confidence: 72% ████' summary bar on review page"""
        fields = obj.extracted_fields.all()
        if not fields:
            return None
        scores = [f.confidence_score for f in fields]
        avg = sum(scores) / len(scores)
        high_count   = sum(1 for s in scores if s >= 0.85)
        medium_count = sum(1 for s in scores if 0.60 <= s < 0.85)
        low_count    = sum(1 for s in scores if s < 0.60)
        return {
            'overall_percent': round(avg * 100),
            'total_fields': len(scores),
            'high_count': high_count,
            'medium_count': medium_count,
            'low_count': low_count,
            'needs_review_count': medium_count + low_count,
        }


# ── Invoice update (PATCH on review page — field corrections) ─────────────────

class InvoiceUpdateSerializer(serializers.ModelSerializer):
    """Used when reviewer edits fields on the review page"""

    class Meta:
        model = Invoice
        fields = [
            'invoice_number', 'vendor_name', 'vendor_address',
            'vendor_email', 'vendor_phone', 'po_number', 'payment_terms',
            'subtotal_amount', 'tax_amount', 'total_amount', 'currency',
            'invoice_date', 'due_date',
        ]


# ── Processing status (for polling endpoint on processing.html) ───────────────

class ProcessingStatusSerializer(serializers.ModelSerializer):
    step_labels = serializers.SerializerMethodField()

    class Meta:
        model = Invoice
        fields = [
            'id', 'status', 'processing_progress',
            'processing_current_step', 'processing_error', 'step_labels',
        ]

    def get_step_labels(self, obj):
        return {
            1: {'label': 'Securely Uploading',          'done': obj.processing_current_step > 1},
            2: {'label': 'Running OCR Scan',             'done': obj.processing_current_step > 2},
            3: {'label': 'AI Agent Extracting Data',     'done': obj.processing_current_step > 3},
            4: {'label': 'Preparing Review Interface',   'done': obj.processing_current_step > 4},
        }
