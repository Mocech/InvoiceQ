"""
Documents views — document preview URL endpoint
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import InvoiceDocument


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def document_preview(request, invoice_pk):
    """
    GET /api/documents/{invoice_id}/preview/
    Returns a signed/direct URL for the document preview iframe on review.html.
    """
    try:
        doc = InvoiceDocument.objects.get(
            invoice__pk=invoice_pk,
            invoice__organization=request.user.organization
        )
    except InvoiceDocument.DoesNotExist:
        return Response({'error': 'Document not found'}, status=status.HTTP_404_NOT_FOUND)

    return Response({
        'preview_url':    doc.preview_url,
        'file_name':      doc.file_name,
        'file_size_mb':   doc.file_size_mb,
        'file_type':      doc.file_type,
        'ocr_provider':   doc.ocr_provider,
        'data_points':    doc.ocr_data_points_found,
    })
