"""
Documents models — InvoiceDocument (the physical file + OCR metadata)
"""

import os
from django.db import models
from django.conf import settings


def invoice_upload_path(instance, filename):
    """Store files as: invoices/originals/2024/01/15/filename.pdf"""
    from django.utils import timezone
    now = timezone.now()
    return f'invoices/originals/{now.year}/{now.month:02d}/{now.day:02d}/{filename}'


class InvoiceDocument(models.Model):
    invoice         = models.OneToOneField(
        'invoices.Invoice',
        on_delete=models.CASCADE,
        related_name='document'
    )

    # ── File storage ─────────────────────────────────────────────────────────
    original_file   = models.FileField(upload_to=invoice_upload_path)
    file_name       = models.CharField(max_length=255)
    file_size_bytes = models.IntegerField(default=0)
    file_type       = models.CharField(max_length=50)   # application/pdf, image/jpeg, etc.
    uploaded_at     = models.DateTimeField(auto_now_add=True)

    # ── OCR output ────────────────────────────────────────────────────────────
    ocr_raw_text          = models.TextField(blank=True)
    ocr_data_points_found = models.IntegerField(null=True, blank=True)
    ocr_completed_at      = models.DateTimeField(null=True, blank=True)
    ocr_provider          = models.CharField(max_length=50, blank=True)

    class Meta:
        db_table = 'invoice_documents'

    def __str__(self):
        return f'Document for {self.invoice} — {self.file_name}'

    @property
    def file_size_mb(self):
        return round(self.file_size_bytes / (1024 * 1024), 2)

    @property
    def preview_url(self):
        """
        Returns a URL for displaying the document in the review page preview panel.
        - Local dev: direct media URL
        - Production S3: signed URL with 1-hour expiry
        """
        if not self.original_file:
            return None

        if settings.STORAGE_BACKEND == 's3':
            return self._get_s3_signed_url()
        else:
            return self.original_file.url

    def _get_s3_signed_url(self):
        try:
            import boto3
            s3_client = boto3.client(
                's3',
                region_name=settings.AWS_S3_REGION_NAME,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                    'Key': self.original_file.name,
                },
                ExpiresIn=3600,  # 1 hour
            )
            return url
        except Exception:
            return self.original_file.url
