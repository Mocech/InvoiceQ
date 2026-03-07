#!/bin/bash
# ============================================================
# InvoiceIQ — Complete Setup Script
# Run once after cloning the project
# ============================================================

set -e

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       InvoiceIQ Backend Setup            ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Python virtual environment ────────────────────────────────────────────
echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# ── 2. Install dependencies ───────────────────────────────────────────────────
echo "📦 Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# ── 3. Environment file ───────────────────────────────────────────────────────
if [ ! -f .env ]; then
  echo "📝 Creating .env from .env.example..."
  cp .env.example .env
  echo ""
  echo "⚠️  IMPORTANT: Edit .env and set your:"
  echo "   - SECRET_KEY (generate with: python -c \"from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())\")"
  echo "   - DB_PASSWORD"
  echo "   - ANTHROPIC_API_KEY"
  echo "   - AWS credentials (optional — set STORAGE_BACKEND=local for dev)"
  echo ""
fi

# ── 4. Database setup ─────────────────────────────────────────────────────────
echo "🗄️  Running database migrations..."
python manage.py migrate

# ── 5. Create logs directory ──────────────────────────────────────────────────
mkdir -p logs

# ── 6. Collect static files ───────────────────────────────────────────────────
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# ── 7. Seed demo data ─────────────────────────────────────────────────────────
echo "🌱 Seeding demo data..."
python manage.py seed_demo_data

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║           Setup Complete! ✅             ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "🚀 Start InvoiceIQ:"
echo ""
echo "   Terminal 1 — Django server:"
echo "   source venv/bin/activate && python manage.py runserver"
echo ""
echo "   Terminal 2 — Celery worker (for invoice processing):"
echo "   source venv/bin/activate && celery -A invoiceiq worker --loglevel=info"
echo ""
echo "   Terminal 3 — Redis (required by Celery):"
echo "   redis-server"
echo ""
echo "📖 API docs: http://localhost:8000/api/docs/"
echo "🔧 Django admin: http://localhost:8000/admin/"
echo "   Login: admin@invoiceiq.com / password123"
echo ""
