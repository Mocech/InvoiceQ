"""
Tests for invoice export functionality.
Place this file at: apps/invoices/tests.py
Run with: python manage.py test apps.invoices.tests.ExportTest -v 2
"""

from django.test import TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from decimal import Decimal
import json


class ExportTest(APITestCase):
    """
    Tests every part of the export pipeline:
    1. URL resolves correctly
    2. Unauthenticated requests are rejected
    3. Authenticated requests succeed
    4. Each format (excel, pdf, csv, json) returns correct content type
    5. Export service generates files without errors
    """

    @classmethod
    def setUpTestData(cls):
        """Create test data once for all tests in this class."""
        from apps.accounts.models import User, Organization

        # Create organization
        cls.org = Organization.objects.create(name='Test Org Export')

        # Create user belonging to that org
        cls.user = User.objects.create_user(
            email='exporttest@test.com',
            password='testpass123',
            first_name='Export',
            last_name='Tester',
            organization=cls.org,
        )

        # Create a minimal invoice owned by that user/org
        from apps.invoices.models import Invoice
        cls.invoice = Invoice.objects.create(
            vendor_name='Test Vendor',
            invoice_number='INV-TEST-001',
            status=Invoice.STATUS_APPROVED,
            organization=cls.org,
            uploaded_by=cls.user,
            total_amount=Decimal('1500.00'),
            subtotal_amount=Decimal('1300.00'),
            tax_amount=Decimal('200.00'),
            currency='KES',
        )

    def setUp(self):
        """Authenticate before each test."""
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    # ── 1. URL Resolution ─────────────────────────────────────────────────────

    def test_export_url_resolves(self):
        """Export URL should resolve to export_invoice view."""
        from django.urls import resolve
        from apps.invoices.views import export_invoice

        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        self.assertEqual(url, f'/api/invoices/{self.invoice.pk}/export/')

        match = resolve(url)
        # DRF wraps functions — check the underlying function name
        self.assertEqual(match.url_name, 'invoice-export')
        print(f'\n✓ URL resolves: {url} -> {match.url_name}')

    # ── 2. Authentication ─────────────────────────────────────────────────────

    def test_export_requires_authentication(self):
        """Unauthenticated request should return 401."""
        client = APIClient()  # no auth
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = client.get(url, {'export_format': 'excel'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        print(f'\n✓ Unauthenticated returns 401: {response.status_code}')

    # ── 3. Invoice Not Found ──────────────────────────────────────────────────

    def test_export_nonexistent_invoice_returns_404(self):
        """Request for non-existent invoice should return 404."""
        url = reverse('invoice-export', kwargs={'pk': 99999})
        response = self.client.get(url, {'export_format': 'excel'})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        print(f'\n✓ Non-existent invoice returns 404: {response.status_code}')

    # ── 4. Excel Export ───────────────────────────────────────────────────────

    def test_export_excel_status_200(self):
        """Excel export should return 200."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'excel'})
        print(f'\n  Excel status: {response.status_code}')
        if response.status_code != 200:
            print(f'  Response content: {response.content[:300]}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_excel_content_type(self):
        """Excel export should return xlsx content type."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'excel'})
        self.assertIn('spreadsheetml', response.get('Content-Type', ''))
        print(f'\n✓ Excel Content-Type: {response.get("Content-Type")}')

    def test_export_excel_has_content(self):
        """Excel file should have content."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'excel'})
        self.assertGreater(len(response.content), 1000)
        print(f'\n✓ Excel file size: {len(response.content)} bytes')

    def test_export_excel_filename(self):
        """Excel export should have correct filename in header."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'excel'})
        disposition = response.get('Content-Disposition', '')
        self.assertIn('.xlsx', disposition)
        print(f'\n✓ Excel Content-Disposition: {disposition}')

    # ── 5. PDF Export ─────────────────────────────────────────────────────────

    def test_export_pdf_status_200(self):
        """PDF export should return 200."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'pdf'})
        print(f'\n  PDF status: {response.status_code}')
        if response.status_code != 200:
            print(f'  Response content: {response.content[:300]}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_export_pdf_content_type(self):
        """PDF export should return application/pdf content type."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'pdf'})
        self.assertEqual(response.get('Content-Type', ''), 'application/pdf')
        print(f'\n✓ PDF Content-Type: {response.get("Content-Type")}')

    def test_export_pdf_has_content(self):
        """PDF file should have content."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'pdf'})
        self.assertGreater(len(response.content), 500)
        print(f'\n✓ PDF file size: {len(response.content)} bytes')

    # ── 6. CSV Export ─────────────────────────────────────────────────────────

    def test_export_csv_status_200(self):
        """CSV export should return 200."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'csv'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(f'\n✓ CSV status: {response.status_code}')

    def test_export_csv_content_type(self):
        """CSV export should return text/csv content type."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'csv'})
        self.assertIn('text/csv', response.get('Content-Type', ''))
        print(f'\n✓ CSV Content-Type: {response.get("Content-Type")}')

    # ── 7. JSON Export ────────────────────────────────────────────────────────

    def test_export_json_status_200(self):
        """JSON export should return 200."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'json'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        print(f'\n✓ JSON status: {response.status_code}')

    def test_export_json_has_invoice_number(self):
        """JSON export should contain invoice number."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'json'})
        content = response.content.decode('utf-8', errors='replace')
        self.assertIn('INV-TEST-001', content)
        print(f'\n✓ JSON contains invoice number')

    # ── 8. Invalid Format ─────────────────────────────────────────────────────

    def test_export_invalid_format_returns_400(self):
        """Invalid format should return 400."""
        url = reverse('invoice-export', kwargs={'pk': self.invoice.pk})
        response = self.client.get(url, {'export_format': 'docx'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        print(f'\n✓ Invalid format returns 400: {response.status_code}')

    # ── 9. Export Service Directly ────────────────────────────────────────────

    def test_export_service_excel_directly(self):
        """Test ExportService.to_excel() directly without HTTP."""
        from apps.invoices.services.export_service import ExportService
        service = ExportService()
        response = service.to_excel(self.invoice)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 1000)
        print(f'\n✓ ExportService.to_excel() works: {len(response.content)} bytes')

    def test_export_service_pdf_directly(self):
        """Test ExportService.to_pdf() directly without HTTP."""
        from apps.invoices.services.export_service import ExportService
        service = ExportService()
        response = service.to_pdf(self.invoice)
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.content), 500)
        print(f'\n✓ ExportService.to_pdf() works: {len(response.content)} bytes')