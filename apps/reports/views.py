"""
Reports views — dashboard KPI cards, monthly analytics, accuracy metrics.
"""

import logging
from datetime import date, timedelta

from django.db.models import Count, Avg,Sum,Q
from django.db.models.functions import TruncMonth

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from datetime import timedelta
from django.utils import timezone
from apps.invoices.models import Invoice

logger = logging.getLogger('apps.invoices')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_stats(request):
    org         = request.user.organization
    today       = date.today()
    month_start = today.replace(day=1)

    from apps.invoices.models import Invoice
    base_qs = Invoice.objects.filter(organization=org)

    invoices_this_month = base_qs.filter(uploaded_at__date__gte=month_start).count()
    pending_review = base_qs.filter(status__in=[Invoice.STATUS_PENDING_REVIEW, Invoice.STATUS_FLAGGED]).count()
    processed_today = base_qs.filter(processed_at__date=today).count()
    approved_count = base_qs.filter(status=Invoice.STATUS_APPROVED).count()
    cost_saved_usd = round(approved_count * (18.00 - 2.40), 2)

    recent = base_qs.select_related('uploaded_by').order_by('-uploaded_at')[:10]
    flagged = base_qs.filter(status=Invoice.STATUS_FLAGGED).select_related('uploaded_by').order_by('-uploaded_at')[:5]

    from apps.invoices.serializers import InvoiceListSerializer

    return Response({
        'kpis': {
            'invoices_this_month': invoices_this_month,
            'pending_review': pending_review,
            'processed_today': processed_today,
            'cost_saved_usd': cost_saved_usd,
            'approved_total': approved_count,
        },
        'recent_invoices': InvoiceListSerializer(recent, many=True).data,
        'flagged_invoices': InvoiceListSerializer(flagged, many=True).data,
        'user': {
            'full_name': request.user.full_name,
            'avatar_initials': request.user.avatar_initials,
            'role': request.user.role,
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics(request):
    org = request.user.organization
    from apps.invoices.models import Invoice, ExtractedField
    base_qs = Invoice.objects.filter(organization=org)

    six_months_ago = date.today() - timedelta(days=180)
    monthly_volumes = (
        base_qs
        .filter(uploaded_at__date__gte=six_months_ago)
        .annotate(month=TruncMonth('uploaded_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )
    chart_data = [{'month': item['month'].strftime('%b'), 'count': item['count']} for item in monthly_volumes]
    while len(chart_data) < 6:
        chart_data.insert(0, {'month': '-', 'count': 0})

    monthly_accuracy = []
    for i in range(5, -1, -1):
        month_date = (date.today().replace(day=1) - timedelta(days=i * 28))
        month_end  = (month_date.replace(day=28) + timedelta(days=4)).replace(day=1)
        fields = ExtractedField.objects.filter(
            invoice__organization=org,
            invoice__processed_at__date__gte=month_date,
            invoice__processed_at__date__lt=month_end,
        )
        total = fields.count()
        accuracy = round(((total - fields.filter(manually_corrected=True).count()) / total) * 100, 1) if total else 94.0
        monthly_accuracy.append({'month': month_date.strftime('%b'), 'accuracy': accuracy})

    total_invoices  = base_qs.count()
    total_approved  = base_qs.filter(status=Invoice.STATUS_APPROVED).count()
    avg_ms          = base_qs.filter(ai_processing_time_ms__isnull=False).aggregate(avg=Avg('ai_processing_time_ms'))['avg'] or 0
    all_fields      = ExtractedField.objects.filter(invoice__organization=org)
    total_fields    = all_fields.count()
    corrected       = all_fields.filter(manually_corrected=True).count()
    accuracy_rate   = round(((total_fields - corrected) / total_fields) * 100, 1) if total_fields else 94.2
    hitl_count      = base_qs.filter(extracted_fields__manually_corrected=True).distinct().count()

    return Response({
        'monthly_volumes': chart_data,
        'monthly_accuracy': monthly_accuracy,
        'kpis': {
            'total_invoices': total_invoices,
            'total_approved': total_approved,
            'avg_processing_seconds': round(avg_ms / 1000, 1),
            'accuracy_rate_percent': accuracy_rate,
            'hitl_rate_percent': round((hitl_count / total_invoices) * 100, 1) if total_invoices else 8.0,
            'cost_per_invoice_ai': 2.40,
            'cost_per_invoice_manual': 18.00,
            'total_cost_saved': round(total_approved * 15.60, 2),
        }
    })


"""
ADD THIS to your reports/views.py or invoices/views.py
Then add to urls.py:  path('api/reports/business/', business_report, name='business_report'),
"""




@api_view(['GET'])
@permission_classes([IsAuthenticated])
def business_report(request):
    """
    GET /api/reports/business/
    Returns all data needed for the financial reports page.
    Every metric here is directly useful for business decisions.
    """
    org   = request.user.organization
    today = timezone.now().date()
    now   = timezone.now()

    # Date ranges
    start_this_month  = today.replace(day=1)
    start_last_month  = (start_this_month - timedelta(days=1)).replace(day=1)
    end_last_month    = start_this_month - timedelta(days=1)
    in_7_days         = today + timedelta(days=7)

    all_invoices = Invoice.objects.filter(organization=org)

    # ── KPIs ──────────────────────────────────────────────────────────────────

    # Total spend this month (approved invoices)
    spend_this = all_invoices.filter(
        status=Invoice.STATUS_APPROVED,
        invoice_date__gte=start_this_month,
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    spend_last = all_invoices.filter(
        status=Invoice.STATUS_APPROVED,
        invoice_date__gte=start_last_month,
        invoice_date__lte=end_last_month,
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    spend_change_pct = None
    if spend_last > 0:
        spend_change_pct = round(((spend_this - spend_last) / spend_last) * 100, 1)

    # Pending approval
    pending_qs = all_invoices.filter(status=Invoice.STATUS_PENDING_REVIEW)
    pending_count = pending_qs.count()
    oldest_pending = pending_qs.order_by('uploaded_at').first()
    oldest_pending_days = None
    if oldest_pending:
        oldest_pending_days = (now - oldest_pending.uploaded_at).days

    # Due in 7 days (not yet approved)
    due_soon_qs = all_invoices.filter(
        due_date__gte=today,
        due_date__lte=in_7_days,
        status__in=[Invoice.STATUS_PENDING_REVIEW, Invoice.STATUS_APPROVED],
    )
    due_soon_amount = due_soon_qs.aggregate(total=Sum('total_amount'))['total'] or 0
    due_soon_count  = due_soon_qs.count()

    # Flagged
    flagged_count = all_invoices.filter(status=Invoice.STATUS_FLAGGED).count()

    # Detect currency (use most common from org invoices)
    currency_result = all_invoices.values('currency').annotate(c=Count('id')).order_by('-c').first()
    currency = currency_result['currency'] if currency_result else 'KES'

    # ── Attention alerts ──────────────────────────────────────────────────────
    alerts = []

    # Overdue payments (due date passed, not approved)
    overdue = all_invoices.filter(
        due_date__lt=today,
        status__in=[Invoice.STATUS_PENDING_REVIEW, Invoice.STATUS_FLAGGED],
    )
    if overdue.exists():
        total = overdue.aggregate(t=Sum('total_amount'))['t'] or 0
        alerts.append({
            'level':   'danger',
            'message': f"{overdue.count()} invoice(s) are overdue for payment — totalling {currency} {total:,.0f}",
            'link':    '/history/?status=pending_review',
            'action':  'Review now →',
        })

    # Invoices pending more than 3 days
    stale = pending_qs.filter(uploaded_at__lte=now - timedelta(days=3))
    if stale.exists():
        alerts.append({
            'level':   'warning',
            'message': f"{stale.count()} invoice(s) have been waiting for approval for over 3 days",
            'link':    '/history/?status=pending_review',
            'action':  'Approve now →',
        })

    # Flagged invoices
    if flagged_count > 0:
        alerts.append({
            'level':   'warning',
            'message': f"{flagged_count} invoice(s) flagged as suspicious — manager review needed",
            'link':    '/history/?status=flagged',
            'action':  'View flagged →',
        })

    # Vendor spend spike (>50% increase vs last month)
    vendor_spikes = _get_vendor_spend_spikes(org, start_this_month, start_last_month, end_last_month, currency)
    alerts.extend(vendor_spikes)

    # ── Monthly spend trend (last 6 months) ───────────────────────────────────
    monthly_spend = []
    for i in range(5, -1, -1):
        month_start = (today.replace(day=1) - timedelta(days=i * 28)).replace(day=1)
        month_end   = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        total = all_invoices.filter(
            status=Invoice.STATUS_APPROVED,
            invoice_date__gte=month_start,
            invoice_date__lte=month_end,
        ).aggregate(t=Sum('total_amount'))['t'] or 0
        monthly_spend.append({
            'month': month_start.strftime('%b').upper(),
            'total': float(total),
        })

    # ── Invoice pipeline ──────────────────────────────────────────────────────
    def oldest_days(qs):
        obj = qs.order_by('uploaded_at').first()
        return (now - obj.uploaded_at).days if obj else 0

    processing_qs = all_invoices.filter(status=Invoice.STATUS_PROCESSING)
    approved_qs   = all_invoices.filter(status=Invoice.STATUS_APPROVED)
    rejected_qs   = all_invoices.filter(status=Invoice.STATUS_REJECTED)

    pipeline = {
        'processing':              processing_qs.count(),
        'processing_oldest_days':  oldest_days(processing_qs),
        'pending_review':          pending_count,
        'pending_review_oldest_days': oldest_pending_days or 0,
        'approved':                approved_qs.count(),
        'rejected':                rejected_qs.count(),
    }

    # ── Upcoming payments (next 14 days) ─────────────────────────────────────
    upcoming_qs = all_invoices.filter(
        due_date__gte=today,
        due_date__lte=today + timedelta(days=14),
    ).exclude(status=Invoice.STATUS_REJECTED).order_by('due_date')[:10]

    upcoming_payments = [
        {
            'id':             inv.id,
            'vendor_name':    inv.vendor_name,
            'invoice_number': inv.invoice_number,
            'total_amount':   float(inv.total_amount or 0),
            'due_date':       str(inv.due_date),
            'status':         inv.status,
        }
        for inv in upcoming_qs
    ]

    # ── Vendor spend breakdown ────────────────────────────────────────────────
    vendor_this = all_invoices.filter(
        invoice_date__gte=start_this_month,
    ).values('vendor_name').annotate(
        this_month=Sum('total_amount'),
        invoice_count=Count('id'),
    ).order_by('-this_month')[:10]

    vendor_last_map = {
        v['vendor_name']: v['total']
        for v in all_invoices.filter(
            invoice_date__gte=start_last_month,
            invoice_date__lte=end_last_month,
        ).values('vendor_name').annotate(total=Sum('total_amount'))
    }

    vendor_spend = [
        {
            'vendor_name':    v['vendor_name'] or 'Unknown',
            'this_month':     float(v['this_month'] or 0),
            'last_month':     float(vendor_last_map.get(v['vendor_name'], 0)),
            'invoice_count':  v['invoice_count'],
        }
        for v in vendor_this
        if v['vendor_name']
    ]

    return Response({
        'currency': currency,
        'kpis': {
            'total_spend_this_month': float(spend_this),
            'spend_change_pct':       spend_change_pct,
            'pending_count':          pending_count,
            'oldest_pending_days':    oldest_pending_days,
            'due_soon_amount':        float(due_soon_amount),
            'due_soon_count':         due_soon_count,
            'flagged_count':          flagged_count,
        },
        'alerts':           alerts,
        'monthly_spend':    monthly_spend,
        'pipeline':         pipeline,
        'upcoming_payments': upcoming_payments,
        'vendor_spend':     vendor_spend,
    })


def _get_vendor_spend_spikes(org, start_this, start_last, end_last, currency):
    """Flag vendors whose billing jumped more than 50% vs last month."""
    alerts = []
    this_month = Invoice.objects.filter(
        organization=org, invoice_date__gte=start_this,
    ).values('vendor_name').annotate(total=Sum('total_amount'))

    last_month_map = {
        v['vendor_name']: float(v['total'] or 0)
        for v in Invoice.objects.filter(
            organization=org,
            invoice_date__gte=start_last,
            invoice_date__lte=end_last,
        ).values('vendor_name').annotate(total=Sum('total_amount'))
    }

    for v in this_month:
        name      = v['vendor_name']
        this_amt  = float(v['total'] or 0)
        last_amt  = last_month_map.get(name, 0)
        if last_amt > 0 and this_amt > last_amt * 1.5:
            pct = round(((this_amt - last_amt) / last_amt) * 100)
            alerts.append({
                'level':   'info',
                'message': f"{name} billing is up {pct}% this month ({currency} {this_amt:,.0f} vs {currency} {last_amt:,.0f} last month)",
                'link':    f'/history/?vendor={name}',
                'action':  'Investigate →',
            })
    return alerts