"""
python manage.py seed_demo_data

Creates:
  - Demo organization
  - Admin user (admin@invoiceiq.com / password123)
  - Reviewer user (sarah@invoiceiq.com / password123)
  - 15 sample invoices in various states
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import date, timedelta
import random


class Command(BaseCommand):
    help = 'Seeds the database with demo data for InvoiceIQ'

    def handle(self, *args, **kwargs):
        from apps.accounts.models import User, Organization, Notification
        from apps.invoices.models import Invoice, LineItem, ExtractedField, AuditLog

        self.stdout.write('🌱 Seeding demo data...')

        # ── Organization ──────────────────────────────────────────────────────
        org, _ = Organization.objects.get_or_create(
            name='Acme Corporation',
            defaults={
                'plan': 'enterprise',
                'storage_limit_gb': 50.0,
                'invoice_limit_per_month': 5000,
            }
        )
        self.stdout.write(f'  ✓ Organization: {org.name}')

        # ── Users ─────────────────────────────────────────────────────────────
        admin, created = User.objects.get_or_create(
            email='admin@invoiceiq.com',
            defaults={
                'first_name': 'John',
                'last_name': 'Admin',
                'role': 'admin',
                'organization': org,
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created:
            admin.set_password('password123')
            admin.save()
        self.stdout.write(f'  ✓ Admin user: {admin.email} / password123')

        reviewer, created = User.objects.get_or_create(
            email='sarah@invoiceiq.com',
            defaults={
                'first_name': 'Sarah',
                'last_name': 'Jenkins',
                'role': 'reviewer',
                'organization': org,
            }
        )
        if created:
            reviewer.set_password('password123')
            reviewer.save()
        self.stdout.write(f'  ✓ Reviewer user: {reviewer.email} / password123')

        # ── Sample invoices ────────────────────────────────────────────────────
        vendors = [
            {'name': 'Amazon Web Services', 'number': 'INV-2025-00432', 'amount': Decimal('145000.00'), 'status': Invoice.STATUS_PENDING_REVIEW},
            {'name': 'Microsoft Azure',     'number': 'INV-2025-00431', 'amount': Decimal('89500.00'),  'status': Invoice.STATUS_APPROVED},
            {'name': 'Google Cloud',        'number': 'INV-2025-00430', 'amount': Decimal('62000.00'),  'status': Invoice.STATUS_APPROVED},
            {'name': 'Safaricom PLC',       'number': 'INV-2025-00429', 'amount': Decimal('15000.00'),  'status': Invoice.STATUS_FLAGGED},
            {'name': 'Kenya Power',         'number': 'INV-2025-00428', 'amount': Decimal('28500.00'),  'status': Invoice.STATUS_APPROVED},
            {'name': 'DHL Express',         'number': 'INV-2025-00427', 'amount': Decimal('7200.00'),   'status': Invoice.STATUS_APPROVED},
            {'name': 'Jumia Kenya',         'number': 'INV-2025-00426', 'amount': Decimal('34000.00'),  'status': Invoice.STATUS_REJECTED},
            {'name': 'Twilio Inc.',         'number': 'INV-2025-00425', 'amount': Decimal('9800.00'),   'status': Invoice.STATUS_APPROVED},
            {'name': 'Oracle Corporation',  'number': 'INV-2025-00424', 'amount': Decimal('220000.00'), 'status': Invoice.STATUS_PENDING_REVIEW},
            {'name': 'Stripe Inc.',         'number': 'INV-2025-00423', 'amount': Decimal('4200.00'),   'status': Invoice.STATUS_APPROVED},
        ]

        for i, v in enumerate(vendors):
            inv, created = Invoice.objects.get_or_create(
                invoice_number=v['number'],
                defaults={
                    'vendor_name':          v['name'],
                    'vendor_address':       f'123 Business Park, Nairobi, Kenya',
                    'vendor_email':         f'billing@{v["name"].lower().replace(" ", "")}.com',
                    'total_amount':         v['amount'],
                    'subtotal_amount':      v['amount'] * Decimal('0.84'),
                    'tax_amount':           v['amount'] * Decimal('0.16'),
                    'currency':             'KES',
                    'invoice_date':         date.today() - timedelta(days=i * 3),
                    'due_date':             date.today() + timedelta(days=30 - i * 2),
                    'status':               v['status'],
                    'uploaded_by':          reviewer,
                    'organization':         org,
                    'ai_confidence_score':  round(random.uniform(0.72, 0.98), 2),
                    'ai_processing_time_ms': random.randint(800, 3500),
                    'ai_model_used':        'mock',
                    'processed_at':         timezone.now() - timedelta(days=i),
                    'processing_progress':  100,
                    'processing_current_step': 4,
                    'payment_terms':        random.choice(['Net 30', 'Net 60', 'Due on Receipt']),
                }
            )

            if created:
                # Add sample extracted fields
                fields = [
                    ('vendor_name',    'Vendor Name',    v['name'],          random.uniform(0.88, 0.99)),
                    ('invoice_number', 'Invoice Number', v['number'],        random.uniform(0.92, 0.99)),
                    ('invoice_date',   'Invoice Date',   str(date.today() - timedelta(days=i*3)), random.uniform(0.90, 0.99)),
                    ('total_amount',   'Total Amount',   str(v['amount']),   random.uniform(0.85, 0.99)),
                    ('po_number',      'PO Number',      f'PO-{1000+i}',     random.uniform(0.30, 0.70)),
                    ('payment_terms',  'Payment Terms',  'Net 30',           random.uniform(0.85, 0.99)),
                ]
                for field_name, label, val, conf in fields:
                    ExtractedField.objects.create(
                        invoice=inv,
                        field_name=field_name,
                        field_label=label,
                        extracted_value=val,
                        confidence_score=round(conf, 2),
                    )

                # Add sample line items
                LineItem.objects.create(
                    invoice=inv,
                    description='Professional Services',
                    quantity=Decimal('1'),
                    unit_price=inv.subtotal_amount,
                    total=inv.subtotal_amount,
                    ai_confidence=0.92,
                    sort_order=0,
                )

                # Audit log
                AuditLog.objects.create(
                    invoice=inv,
                    user=reviewer,
                    action='uploaded',
                    detail={'file_name': f'{v["number"]}.pdf'},
                )

                # Flagged invoice gets a flag message
                if v['status'] == Invoice.STATUS_FLAGGED:
                    inv.ai_flag_message = 'PO number confidence is very low (34%). Unusual amount for this vendor.'
                    inv.save(update_fields=['ai_flag_message'])

        invoices_created = Invoice.objects.filter(organization=org).count()
        self.stdout.write(f'  ✓ {invoices_created} invoices created')

        # ── Notifications ─────────────────────────────────────────────────────
        Notification.objects.get_or_create(
            user=reviewer,
            title='INV-2025-00432 ready for review',
            defaults={
                'type': 'review_required',
                'message': 'AI extraction complete. Confidence: 87%. ⚠️ PO number needs verification.',
                'invoice_id': Invoice.objects.filter(invoice_number='INV-2025-00432').first().id if Invoice.objects.filter(invoice_number='INV-2025-00432').exists() else None,
            }
        )

        self.stdout.write(self.style.SUCCESS('\n✅ Demo data seeded successfully!'))
        self.stdout.write('\n📋 Login credentials:')
        self.stdout.write('   Admin:    admin@invoiceiq.com  / password123')
        self.stdout.write('   Reviewer: sarah@invoiceiq.com  / password123')
        self.stdout.write('\n🚀 Start the server: python manage.py runserver')
