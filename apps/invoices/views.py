"""
Invoice views — CRUD, upload, approve, reject, flag, status polling, export
"""

import logging
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import status, generics, filters
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import Invoice, ExtractedField, AuditLog
from .serializers import (
    InvoiceListSerializer,
    InvoiceDetailSerializer,
    InvoiceUpdateSerializer,
    ProcessingStatusSerializer,
)
from apps.invoices.services.export_service import ExportService

logger = logging.getLogger('apps.invoices')


# ── Filters ──────────────────────────────────────────────────────────────────

class InvoiceFilter(django_filters.FilterSet):
    status      = django_filters.CharFilter(field_name='status', lookup_expr='exact')
    vendor      = django_filters.CharFilter(field_name='vendor_name', lookup_expr='icontains')
    date_from   = django_filters.DateFilter(field_name='invoice_date', lookup_expr='gte')
    date_to     = django_filters.DateFilter(field_name='invoice_date', lookup_expr='lte')
    min_amount  = django_filters.NumberFilter(field_name='total_amount', lookup_expr='gte')
    max_amount  = django_filters.NumberFilter(field_name='total_amount', lookup_expr='lte')

    class Meta:
        model = Invoice
        fields = ['status', 'vendor', 'date_from', 'date_to', 'min_amount', 'max_amount']


# ── List & Upload ─────────────────────────────────────────────────────────────

class InvoiceListView(generics.ListAPIView):
    """
    GET /api/invoices/
    Returns paginated invoice list for history.html table.
    Supports: ?status=pending_review&search=Amazon&date_from=2024-01-01&page=2
    """
    serializer_class    = InvoiceListSerializer
    permission_classes  = [IsAuthenticated]
    filter_backends     = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class     = InvoiceFilter
    search_fields       = ['invoice_number', 'vendor_name', 'po_number']
    ordering_fields     = ['uploaded_at', 'invoice_date', 'total_amount', 'status']
    ordering            = ['-uploaded_at']

    def get_queryset(self):
        return Invoice.objects.filter(
            organization=self.request.user.organization
        ).select_related('uploaded_by')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def upload_invoice(request):
    """
    POST /api/invoices/upload/
    Accepts multipart file upload. Creates Invoice + InvoiceDocument,
    then dispatches Celery task for async processing.

    Returns immediately with invoice_id so frontend can redirect to
    processing.html?id={invoice_id} and start polling.
    """
    file = request.FILES.get('file')
    if not file:
        return Response({'error': 'No file provided'}, status=status.HTTP_400_BAD_REQUEST)

    # Validate file type
    allowed_types = ['application/pdf', 'image/jpeg', 'image/png', 'image/tiff']
    if file.content_type not in allowed_types:
        return Response(
            {'error': f'Unsupported file type: {file.content_type}. Upload PDF, JPG, PNG, or TIFF.'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Validate file size (50MB max)
    if file.size > 50 * 1024 * 1024:
        return Response({'error': 'File too large. Maximum size is 50MB.'}, status=status.HTTP_400_BAD_REQUEST)

    # Create Invoice record
    invoice = Invoice.objects.create(
        status=Invoice.STATUS_PROCESSING,
        uploaded_by=request.user,
        organization=request.user.organization,
        processing_progress=5,
        processing_current_step=1,
    )

    # Create document record & save file
    from apps.documents.models import InvoiceDocument
    doc = InvoiceDocument.objects.create(
        invoice=invoice,
        original_file=file,
        file_name=file.name,
        file_size_bytes=file.size,
        file_type=file.content_type,
    )

    # Record upload action in audit log
    _log_action(invoice, request.user, 'uploaded', {'file_name': file.name}, request)

    from apps.invoices.services.pipeline import ProcessingPipeline
    pipeline = ProcessingPipeline()
    pipeline.run(invoice.id)
    logger.info(f'Invoice {invoice.id} uploaded by {request.user.email}, task dispatched')

    return Response({
        'invoice_id': invoice.id,
        'status': invoice.status,
        'message': 'Invoice uploaded. Processing started.',
    }, status=status.HTTP_201_CREATED)


# ── Single Invoice ────────────────────────────────────────────────────────────

class InvoiceDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/invoices/{id}/   — Full invoice detail for review.html
    PATCH /api/invoices/{id}/   — Save field corrections made by reviewer
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Invoice.objects.filter(
            organization=self.request.user.organization
        ).prefetch_related('line_items', 'extracted_fields', 'audit_logs__user')

    def get_serializer_class(self):
        if self.request.method == 'PATCH':
            return InvoiceUpdateSerializer
        return InvoiceDetailSerializer

    def partial_update(self, request, *args, **kwargs):
        invoice = self.get_object()
        old_data = InvoiceUpdateSerializer(invoice).data

        response = super().partial_update(request, *args, **kwargs)

        # Build a diff of what changed for the audit log
        new_data = InvoiceUpdateSerializer(invoice).data
        changes = {
            field: {'from': old_data[field], 'to': new_data[field]}
            for field in old_data
            if old_data[field] != new_data[field]
        }
        if changes:
            _log_action(invoice, request.user, 'field_corrected', {'changes': changes}, request)

        return response


# ── Processing Status (polling) ───────────────────────────────────────────────

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def invoice_status(request, pk):
    """
    GET /api/invoices/{id}/status/
    Called by processing.html every 2 seconds to update the progress ring.
    Returns immediately with current processing state.
    """
    try:
        invoice = Invoice.objects.get(pk=pk, organization=request.user.organization)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    serializer = ProcessingStatusSerializer(invoice)
    return Response(serializer.data)


# ── Actions ───────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def approve_invoice(request, pk):
    """
    POST /api/invoices/{id}/approve/
    Moves invoice to 'approved'. Creates audit log. Sends notification.
    Also saves any last-minute field corrections passed in request body.
    """
    try:
        invoice = Invoice.objects.get(pk=pk, organization=request.user.organization)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    if invoice.status not in [Invoice.STATUS_PENDING_REVIEW, Invoice.STATUS_FLAGGED]:
        return Response(
            {'error': f'Cannot approve invoice with status: {invoice.status}'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Save any field corrections included in the approve request
    corrections = request.data.get('corrections', {})
    for field_name, new_value in corrections.items():
        ExtractedField.objects.filter(
            invoice=invoice, field_name=field_name
        ).update(
            manually_corrected=True,
            corrected_value=new_value,
            corrected_by=request.user,
            corrected_at=timezone.now(),
        )

    invoice.status       = Invoice.STATUS_APPROVED
    invoice.reviewed_by  = request.user
    invoice.reviewed_at  = timezone.now()
    invoice.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    _log_action(invoice, request.user, 'approved',
                {'corrections_count': len(corrections)}, request)

    # Create notification for the uploader
    _create_notification(
        invoice, 'invoice_approved',
        f'Invoice {invoice.invoice_number} approved',
        f'Approved by {request.user.full_name}'
    )

    logger.info(f'Invoice {invoice.id} approved by {request.user.email}')

    return Response({
        'message': f'Invoice {invoice.invoice_number} approved successfully.',
        'invoice_id': invoice.id,
        'status': invoice.status,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reject_invoice(request, pk):
    """
    POST /api/invoices/{id}/reject/
    Body: { "reason": "..." }  — optional rejection reason
    """
    try:
        invoice = Invoice.objects.get(pk=pk, organization=request.user.organization)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    reason = request.data.get('reason', '')

    invoice.status      = Invoice.STATUS_REJECTED
    invoice.reviewed_by = request.user
    invoice.reviewed_at = timezone.now()
    invoice.save(update_fields=['status', 'reviewed_by', 'reviewed_at'])

    _log_action(invoice, request.user, 'rejected', {'reason': reason}, request)

    logger.info(f'Invoice {invoice.id} rejected by {request.user.email}. Reason: {reason}')

    return Response({
        'message': f'Invoice {invoice.invoice_number} rejected.',
        'invoice_id': invoice.id,
        'status': invoice.status,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def flag_invoice(request, pk):
    """
    POST /api/invoices/{id}/flag/
    Body: { "message": "..." }
    Flags invoice for manager review and sends notification.
    """
    try:
        invoice = Invoice.objects.get(pk=pk, organization=request.user.organization)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    message = request.data.get('message', 'Flagged for manager review')

    invoice.status          = Invoice.STATUS_FLAGGED
    invoice.ai_flag_message = message
    invoice.save(update_fields=['status', 'ai_flag_message'])

    _log_action(invoice, request.user, 'flagged', {'message': message}, request)

    _create_notification(
        invoice, 'invoice_flagged',
        f'Invoice {invoice.invoice_number} flagged',
        message
    )

    return Response({
        'message': f'Invoice flagged. Manager has been notified.',
        'invoice_id': invoice.id,
        'status': invoice.status,
    })


# ── Export ────────────────────────────────────────────────────────────────────
# Replace the existing export_invoice function in apps/invoices/views.py with this:

# Replace export_invoice in apps/invoices/views.py with this:
# Replace export_invoice in apps/invoices/views.py with this:

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def export_invoice(request, pk):
    """
    GET /api/invoices/{id}/export/?export_format=excel
    GET /api/invoices/{id}/export/?export_format=pdf
    GET /api/invoices/{id}/export/?export_format=csv
    GET /api/invoices/{id}/export/?export_format=json

    NOTE: uses 'export_format' not 'format' — DRF reserves ?format= for
    content negotiation which causes 404s for non-JSON formats.
    """
    try:
        invoice = Invoice.objects.prefetch_related(
            'line_items', 'extracted_fields', 'audit_logs__user'
        ).get(pk=pk)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    # Allow access if: same org, OR superuser, OR uploaded by this user
    user = request.user
    has_access = (
        user.is_superuser or
        invoice.uploaded_by == user or
        (user.organization and invoice.organization == user.organization) or
        invoice.organization is None
    )
    if not has_access:
        return Response({'error': 'Access denied'}, status=status.HTTP_403_FORBIDDEN)

    export_format = request.query_params.get('export_format', 'excel').lower()
    service = ExportService()

    if export_format == 'excel':
        response = service.to_excel(invoice)
        _log_action(invoice, request.user, 'exported_excel', {}, request)
        return response
    elif export_format == 'pdf':
        response = service.to_pdf(invoice)
        _log_action(invoice, request.user, 'exported_pdf', {}, request)
        return response
    elif export_format == 'csv':
        response = service.to_csv(invoice)
        _log_action(invoice, request.user, 'exported_csv', {}, request)
        return response
    elif export_format == 'json':
        response = service.to_json(invoice)
        _log_action(invoice, request.user, 'exported_json', {}, request)
        return response
    else:
        return Response(
            {'error': 'Invalid format. Use excel, pdf, csv, or json.'},
            status=status.HTTP_400_BAD_REQUEST
        )
            
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_to_accounting(request, pk):
    """
    POST /api/invoices/{id}/send-to-accounting/
    Simulates push to an accounting system (QuickBooks, Sage, SAP, etc.)
    In production this would call the accounting system's API.
    """
    try:
        invoice = Invoice.objects.get(pk=pk, organization=request.user.organization)
    except Invoice.DoesNotExist:
        return Response({'error': 'Invoice not found'}, status=status.HTTP_404_NOT_FOUND)

    # TODO: In production, call accounting system API here
    _log_action(invoice, request.user, 'sent_to_accounting', {}, request)

    return Response({'message': 'Invoice sent to accounting system successfully.'})


# ── Helpers ───────────────────────────────────────────────────────────────────

def _log_action(invoice, user, action, detail, request=None):
    ip = None
    ua = ''
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')
        ua = request.META.get('HTTP_USER_AGENT', '')[:500]

    AuditLog.objects.create(
        invoice=invoice,
        user=user,
        action=action,
        detail=detail,
        ip_address=ip,
        user_agent=ua,
    )


def _create_notification(invoice, notif_type, title, message):
    from apps.accounts.models import Notification
    if invoice.uploaded_by:
        Notification.objects.create(
            user=invoice.uploaded_by,
            type=notif_type,
            title=title,
            message=message,
            invoice_id=invoice.id,
        )

