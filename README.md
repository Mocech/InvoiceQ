# InvoiceIQ Backend

AI-powered invoice processing backend built with Django, Django REST Framework, Celery, and Claude AI.

---

## Architecture Overview

```
Browser (HTML/JS)
      │
      │  fetch() API calls  ← main.js apiFetch() wrapper
      ▼
Django REST Framework  ←  JWT Authentication (SimpleJWT)
      │
      ├── /api/auth/         ← Login, logout, user profile, notifications
      ├── /api/invoices/     ← CRUD, upload, approve, reject, flag, export
      ├── /api/documents/    ← Document preview URLs
      └── /api/reports/      ← Dashboard stats, analytics charts
      │
      ├── Celery Task ──► OCR Service (AWS Textract)
      │                        │
      │                        ▼
      │                   AI Service (Claude claude-sonnet-4-6)
      │                        │
      │                        ▼
      │                   PostgreSQL (Invoice + ExtractedField rows)
      │
      └── Redis  ←──  Celery Broker
```

---

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+
- Redis 7+
- An Anthropic API key (get one at console.anthropic.com)

### 1. Clone & Setup

```bash
git clone <repo>
cd invoiceiq
chmod +x setup.sh
./setup.sh
```

### 2. Configure Environment

Edit `.env`:

```env
SECRET_KEY=<generate with python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
DB_PASSWORD=yourpassword
ANTHROPIC_API_KEY=sk-ant-...

# For local dev, keep these defaults:
STORAGE_BACKEND=local
OCR_PROVIDER=aws_textract   # or mock if no AWS
DEBUG=True
```

### 3. Start All Services

```bash
# Terminal 1 — Redis
redis-server

# Terminal 2 — Celery worker
source venv/bin/activate
celery -A invoiceiq worker --loglevel=info

# Terminal 3 — Django
source venv/bin/activate
python manage.py runserver
```

Open: http://localhost:8000

**Demo login:** `sarah@invoiceiq.com` / `password123`

---

## Project Structure

```
invoiceiq/
├── invoiceiq/              ← Django project (settings, urls, celery)
├── apps/
│   ├── accounts/           ← User, Organization, Notification models + JWT auth
│   ├── invoices/           ← Invoice, LineItem, ExtractedField, AuditLog
│   │   ├── services/
│   │   │   ├── ocr_service.py      ← AWS Textract / Google Vision
│   │   │   ├── ai_service.py       ← Claude AI extraction
│   │   │   ├── pipeline.py         ← Orchestrates OCR → AI → DB
│   │   │   └── export_service.py   ← CSV + JSON export
│   │   ├── tasks.py        ← Celery async tasks
│   │   └── management/commands/seed_demo_data.py
│   ├── documents/          ← InvoiceDocument (file storage + OCR metadata)
│   └── reports/            ← Dashboard KPIs + analytics
├── frontend/
│   ├── static/
│   │   ├── css/styles.css
│   │   └── js/main.js      ← All fetch() API calls
│   └── pages/              ← HTML files served by Django
├── media/                  ← Uploaded invoice files (local dev)
├── logs/
├── requirements.txt
├── setup.sh
└── .env.example
```

---

## API Reference

### Auth
| Method | URL | Description |
|--------|-----|-------------|
| POST | `/api/auth/login/` | Returns JWT access + refresh tokens + user profile |
| POST | `/api/auth/logout/` | Blacklists refresh token |
| POST | `/api/auth/refresh/` | Refreshes access token |
| GET | `/api/auth/me/` | Current user profile |
| GET | `/api/auth/notifications/` | Unread notifications for bell dropdown |
| PATCH | `/api/auth/notifications/{id}/` | Mark notification as read |

### Invoices
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/invoices/` | Paginated list. Params: `?status=&search=&date_from=&date_to=` |
| POST | `/api/invoices/upload/` | Multipart file upload. Returns `invoice_id` immediately |
| GET | `/api/invoices/{id}/` | Full detail for review page |
| PATCH | `/api/invoices/{id}/` | Save field corrections |
| GET | `/api/invoices/{id}/status/` | Processing progress (polled every 2s) |
| POST | `/api/invoices/{id}/approve/` | Approve + optionally save corrections |
| POST | `/api/invoices/{id}/reject/` | Reject with optional reason |
| POST | `/api/invoices/{id}/flag/` | Flag for manager review |
| GET | `/api/invoices/{id}/export/?format=csv` | Download as CSV |
| GET | `/api/invoices/{id}/export/?format=json` | Download as JSON |
| POST | `/api/invoices/{id}/send-to-accounting/` | Push to accounting system |

### Reports
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/reports/dashboard/` | KPI cards + recent invoices for dashboard |
| GET | `/api/reports/analytics/` | Charts + full analytics for reports page |

### Documents
| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/documents/{invoice_id}/preview/` | Signed URL for document preview |

---

## Processing Flow

```
1. User uploads PDF on upload.html
        │
        ▼
2. POST /api/invoices/upload/
   → Django saves file
   → Creates Invoice (status=processing)
   → Dispatches Celery task
   → Returns {invoice_id} IMMEDIATELY
        │
        ▼
3. Frontend redirects to /processing/?id={invoice_id}
   → Polls GET /api/invoices/{id}/status/ every 2 seconds
   → Updates progress ring + step indicators from real data
        │
        ▼
4. Celery task runs ProcessingPipeline:
   Step 1: Confirm upload        → progress=10%
   Step 2: AWS Textract OCR      → progress=25%-45%
   Step 3: Claude AI extraction  → progress=55%-75%
   Step 4: Save to DB            → progress=85%-100%
   → Invoice.status = 'pending_review'
        │
        ▼
5. Polling detects status=pending_review
   → Frontend auto-redirects to /review/?id={invoice_id}
        │
        ▼
6. Review page calls GET /api/invoices/{id}/
   → Populates extracted fields with confidence badges
   → Renders confidence summary bar
   → Loads document preview
        │
        ▼
7. Reviewer approves/rejects/flags via buttons or A/R/F keyboard shortcuts
   → POST /api/invoices/{id}/approve/
   → Audit log created
   → Notification sent
   → Redirect to /success/
```

---

## AI Extraction (Claude)

The `AIExtractionService` sends OCR text to `claude-sonnet-4-6` with a structured system prompt.

Claude returns JSON with a confidence score per field:
```json
{
  "vendor_name":   {"value": "ABC Ltd",   "confidence": 0.95},
  "total_amount":  {"value": "145000.00", "confidence": 0.98},
  "po_number":     {"value": "PO-0891",   "confidence": 0.34},
  ...
  "overall_confidence": 0.87,
  "needs_human_review": true,
  "flag_message": "PO number confidence is low (34%)"
}
```

Confidence drives the UI:
- `>= 0.85` → Green badge (High confidence)
- `0.60–0.84` → Yellow badge (Needs review)  
- `< 0.60` → Red badge (Low confidence, always flagged)

**No API key?** The service falls back to `_mock_extraction()` which returns realistic demo data — great for development without spending API credits.

---

## Frontend Integration

`main.js` replaces all hardcoded HTML data with real `fetch()` calls:

| Page | Fetch call |
|------|-----------|
| `dashboard.html` | `GET /api/reports/dashboard/` → populates all 4 KPI cards + recent table |
| `upload.html` | `POST /api/invoices/upload/` → returns invoice_id for redirect |
| `processing.html` | `GET /api/invoices/{id}/status/` polled every 2s |
| `review.html` | `GET /api/invoices/{id}/` → all fields, confidence scores, preview URL |
| `history.html` | `GET /api/invoices/` → full table with search + filter |
| `reports.html` | `GET /api/reports/analytics/` → chart data + KPIs |
| Bell dropdown | `GET /api/auth/notifications/` → real notification items |

All calls use a shared `apiFetch()` wrapper that injects the JWT Bearer token and handles 401 auto-refresh.

---

## Production Deployment Checklist

- [ ] Set `DEBUG=False` in `.env`
- [ ] Set `STORAGE_BACKEND=s3` and configure AWS credentials
- [ ] Set `ALLOWED_HOSTS` to your domain
- [ ] Run `python manage.py collectstatic`
- [ ] Use gunicorn: `gunicorn invoiceiq.wsgi:application`
- [ ] Use nginx as reverse proxy
- [ ] Set up Celery with systemd or supervisor
- [ ] Enable HTTPS / SSL certificate
- [ ] Set strong `SECRET_KEY`
- [ ] Configure `CORS_ALLOWED_ORIGINS` for your domain only
#   I n v o i c e Q  
 