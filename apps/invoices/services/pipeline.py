"""
Invoice Processing Pipeline
Orchestrates: Upload → OCR → AI Extraction → DB Writes → Ready for Review

Each step updates Invoice.processing_progress so the polling endpoint
on processing.html can show real-time progress to the user.
"""

import logging
import time
from decimal import Decimal
from django.utils import timezone

from .ocr_service import OCRService
from .ai_service import AIExtractionService

logger = logging.getLogger('apps.invoices')


class ProcessingPipeline:

    FIELD_LABEL_MAP = {
        'invoice_number':  'Invoice Number',
        'vendor_name':     'Vendor Name',
        'vendor_address':  'Vendor Address',
        'vendor_email':    'Vendor Email',
        'vendor_phone':    'Vendor Phone',
        'po_number':       'PO Number',
        'payment_terms':   'Payment Terms',
        'invoice_date':    'Invoice Date',
        'due_date':        'Due Date',
        'currency':        'Currency',
        'subtotal_amount': 'Subtotal Amount',
        'tax_amount':      'Tax Amount',
        'total_amount':    'Total Amount',
    }

    def run(self, invoice_id: int):
        """
        Main pipeline entry point. Called by the Celery task.
        Wraps everything in try/except so failures are recorded cleanly.
        """
        from apps.invoices.models import Invoice

        try:
            invoice = Invoice.objects.get(pk=invoice_id)
            self._run_pipeline(invoice)
        except Invoice.DoesNotExist:
            logger.error(f'Pipeline: Invoice {invoice_id} not found')
        except Exception as e:
            logger.error(f'Pipeline: Unexpected error for invoice {invoice_id}: {e}', exc_info=True)
            try:
                invoice = Invoice.objects.get(pk=invoice_id)
                self._mark_failed(invoice, str(e))
            except Exception:
                pass

    def _run_pipeline(self, invoice):
        from apps.invoices.models import Invoice

        logger.info(f'Pipeline started for invoice {invoice.id}')

        # ── Step 1: Already uploaded — just confirm ───────────────────────────
        self._update_progress(invoice, step=1, progress=10, status=Invoice.STATUS_PROCESSING)
        time.sleep(0.5)

        # ── Step 2: OCR ───────────────────────────────────────────────────────
        self._update_progress(invoice, step=2, progress=25)
        logger.info(f'Pipeline step 2: OCR for invoice {invoice.id}')

        doc = invoice.document
        file_path = doc.original_file.path

        ocr_service = OCRService()
        ocr_result  = ocr_service.extract(file_path, doc.file_type)

        # Save OCR output to document record
        doc.ocr_raw_text         = ocr_result.raw_text
        doc.ocr_data_points_found = ocr_result.data_points_found
        doc.ocr_completed_at      = timezone.now()
        doc.ocr_provider          = ocr_result.provider
        doc.save(update_fields=['ocr_raw_text', 'ocr_data_points_found',
                                'ocr_completed_at', 'ocr_provider'])

        self._update_progress(invoice, step=2, progress=45)

        # ── Step 3: AI Extraction ─────────────────────────────────────────────
        self._update_progress(invoice, step=3, progress=55)
        logger.info(f'Pipeline step 3: AI extraction for invoice {invoice.id}')

        ai_service = AIExtractionService()
        ai_result  = ai_service.extract(ocr_result.raw_text, ocr_result.blocks)

        self._update_progress(invoice, step=3, progress=75)

        # ── Step 4: Save to database ──────────────────────────────────────────
        self._update_progress(invoice, step=4, progress=85)
        logger.info(f'Pipeline step 4: saving extracted data for invoice {invoice.id}')

        self._save_extracted_data(invoice, ai_result)

        # ── Done ──────────────────────────────────────────────────────────────
        invoice.status                = Invoice.STATUS_PENDING_REVIEW
        invoice.processing_progress   = 100
        invoice.processing_current_step = 4
        invoice.processed_at          = timezone.now()
        invoice.ai_confidence_score   = ai_result.overall_confidence
        invoice.ai_processing_time_ms = (
            ocr_result.processing_time_ms + ai_result.processing_time_ms
        )
        invoice.ai_model_used         = ai_result.model_used
        invoice.ai_flag_message       = ai_result.flag_message
        invoice.save()

        # Create notification for the uploader
        self._notify_ready(invoice)

        logger.info(
            f'Pipeline complete for invoice {invoice.id}. '
            f'Confidence: {ai_result.overall_confidence:.2f}, '
            f'Status: {invoice.status}'
        )

    def _save_extracted_data(self, invoice, ai_result):
        """
        Writes AI-extracted field values + confidence scores to the DB.
        This is what populates the review page.
        """
        from apps.invoices.models import ExtractedField, LineItem

        data = ai_result.data

        # ── Save scalar fields ─────────────────────────────────────────────────
        invoice_field_updates = {}

        for field_name, label in self.FIELD_LABEL_MAP.items():
            field_data = data.get(field_name, {})
            if not isinstance(field_data, dict):
                continue

            raw_value  = field_data.get('value') or ''
            confidence = float(field_data.get('confidence', 0.0))

            if raw_value is None:
                raw_value = ''

            # Save to ExtractedField for the review UI
            ExtractedField.objects.update_or_create(
                invoice=invoice,
                field_name=field_name,
                defaults={
                    'field_label':     label,
                    'extracted_value': str(raw_value),
                    'confidence_score': confidence,
                }
            )

            # Also update the Invoice record directly for querying
            invoice_field_updates[field_name] = raw_value

        # Apply scalar updates to Invoice
        for field_name, value in invoice_field_updates.items():
            if value and hasattr(invoice, field_name):
                if field_name in ('subtotal_amount', 'tax_amount', 'total_amount'):
                    try:
                        setattr(invoice, field_name, Decimal(str(value).replace(',', '')))
                    except Exception:
                        pass
                elif field_name in ('invoice_date', 'due_date'):
                    try:
                        from datetime import date
                        setattr(invoice, field_name, date.fromisoformat(str(value)))
                    except Exception:
                        pass
                else:
                    setattr(invoice, field_name, str(value))

        invoice.save()

        # ── Save line items ────────────────────────────────────────────────────
        LineItem.objects.filter(invoice=invoice).delete()

        for i, item in enumerate(data.get('line_items', [])):
            try:
                LineItem.objects.create(
                    invoice=invoice,
                    description=item.get('description', ''),
                    quantity=Decimal(str(item.get('quantity', 1))),
                    unit_price=Decimal(str(item.get('unit_price', '0')).replace(',', '')),
                    total=Decimal(str(item.get('total', '0')).replace(',', '')),
                    ai_confidence=float(item.get('confidence', 0.8)),
                    sort_order=i,
                )
            except Exception as e:
                logger.warning(f'Could not save line item {i} for invoice {invoice.id}: {e}')

    def _update_progress(self, invoice, step: int, progress: int, status=None):
        from apps.invoices.models import Invoice
        updates = {
            'processing_current_step': step,
            'processing_progress': progress,
        }
        if status:
            updates['status'] = status
        Invoice.objects.filter(pk=invoice.id).update(**updates)
        invoice.processing_current_step = step
        invoice.processing_progress = progress

    def _mark_failed(self, invoice, error_message: str):
        from apps.invoices.models import Invoice
        invoice.status           = Invoice.STATUS_PENDING_REVIEW  # let reviewer handle it
        invoice.processing_error = error_message[:1000]
        invoice.processed_at     = timezone.now()
        invoice.save(update_fields=['status', 'processing_error', 'processed_at'])
        logger.error(f'Invoice {invoice.id} pipeline failed: {error_message}')

    def _notify_ready(self, invoice):
        from apps.accounts.models import Notification
        if invoice.uploaded_by:
            Notification.objects.create(
                user=invoice.uploaded_by,
                type='review_required',
                title=f'Invoice {invoice.invoice_number} ready for review',
                message=(
                    f'AI extraction complete. '
                    f'Confidence: {round(invoice.ai_confidence_score * 100)}%. '
                    + (f'⚠️ {invoice.ai_flag_message}' if invoice.ai_flag_message else '')
                ),
                invoice_id=invoice.id,
            )
