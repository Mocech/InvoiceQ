# InvoiceIQ — Enterprise Invoice Processing Platform

An intelligent, AI-powered invoice processing platform built with Django, Django REST Framework, and Groq/Claude AI. Process, extract, review, and manage invoices at enterprise scale with human-in-the-loop verification.

**Key Features:**
- 🤖 AI-powered invoice field extraction with confidence scoring
- ✅ Multi-step approval workflow (upload → process → review → approve)
- 📊 Real-time dashboard with analytics and reporting
- 🔐 Enterprise authentication with JWT and multi-user support
- 📝 Complete audit logging for compliance
- 💾 Export invoices as CSV, JSON, Excel, or PDF
- 🌍 Multi-currency support (USD, KES, EUR, GBP, ZAR)
- 📱 Responsive web interface

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      Browser Frontend                            │
│                   (HTML/CSS/Vanilla JS)                          │
│            Dashboard • Upload • Review • Reports                 │
└──────────────────────────┬──────────────────────────────────────┘
                          │
                  fetch() API calls
                    (JWT Bearer Token)
                          │
         ┌────────────────▼────────────────┐
         │ Django REST Framework API       │
         │ (/api/auth, /invoices, etc)    │
         └────────────────┬────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
    Accounts          Invoices            Reports
    (Auth, Users)     (CRUD, Status)      (Analytics)
        │                 │
        │            ┌────┴────────┐
        │            │             │
        │            ▼             ▼
        │          OCR Service   AI Service
        │          (Textract)    (Groq API)
        │            │             │
        ▼            ▼             ▼
    ┌────────────────────────────────────┐
    │     MySQL Database                 │
    │  • Invoice records                 │
    │  • Extracted fields (w/ scores)    │
    │  • Line items                      │
    │  • Audit logs                      │
    └────────────────────────────────────┘
        │
        ▼
    Redis (Task Broker)
    ├─ Celery Tasks
    └─ Cache
```

---

## 🚀 Quick Start

### Prerequisites

- **Python** 3.11+
- **MySQL** 8.0+
- **Redis** 7.0+ (optional, but recommended for Celery)
- **Groq API Key** (free, get at [console.groq.com](https://console.groq.com))
  - *Alternative:* Anthropic API key for Claude

### 1. Clone the Repository

```bash
git clone <repository-url>
cd invoiceiq
```

### 2. Run Setup Script

```bash
chmod +x setup.sh
./setup.sh
```

This script will:
- Create a Python virtual environment
- Install all dependencies
- Set up the database
- Collect static files
- Seed demo data (optional)

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-django-secret-key-here
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_ENGINE=django.db.backends.mysql
DB_NAME=invoiceiq_db
DB_USER=root
DB_PASSWORD=your-mysql-password
DB_HOST=localhost
DB_PORT=3306

# AI & OCR Services
GROQ_API_KEY=your-groq-api-key
# OR
ANTHROPIC_API_KEY=your-anthropic-api-key

# Optional: AWS Textract
AWS_ACCESS_KEY_ID=your-aws-key
AWS_SECRET_ACCESS_KEY=your-aws-secret
AWS_REGION=us-east-1
```

### 4. Initialize Database

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Run Development Server

```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000/`

Access the admin panel at `http://localhost:8000/admin/`

---

## 📋 Project Structure

```
invoiceiq/
├── apps/                           # Django apps
│   ├── accounts/                   # Authentication & user management
│   │   ├── models.py              # User, Organization models
│   │   ├── views.py               # Auth endpoints (login, register)
│   │   ├── serializers.py         # User serializers
│   │   └── urls.py                # /api/auth/ routes
│   │
│   ├── invoices/                   # Core invoice processing
│   │   ├── models.py              # Invoice, LineItem, ExtractedField, AuditLog
│   │   ├── views.py               # Invoice CRUD, approve, reject, export
│   │   ├── serializers.py         # Invoice serializers
│   │   ├── urls.py                # /api/invoices/ routes
│   │   ├── services/
│   │   │   ├── ai_service.py     # Groq/Claude extraction
│   │   │   ├── ocr_service.py    # AWS Textract OCR
│   │   │   ├── export_service.py # CSV/JSON/PDF/Excel export
│   │   │   └── pipeline.py       # Celery task orchestration
│   │   └── management/
│   │       └── commands/
│   │           └── seed_demo_data.py  # Demo data generator
│   │
│   ├── documents/                  # Document storage & preview
│   │   ├── models.py              # Document metadata
│   │   ├── views.py               # Document upload, retrieve
│   │   └── services/              # Document processing
│   │
│   └── reports/                    # Analytics & dashboards
│       ├── models.py              # Report definitions
│       ├── views.py               # Dashboard stats, charts
│       └── urls.py                # /api/reports/ routes
│
├── invoiceiq/                      # Django project settings
│   ├── settings.py                # Configuration
│   ├── urls.py                    # URL routing
│   └── wsgi.py                    # WSGI application
│
├── frontend/                       # Frontend SPA
│   ├── pages/                     # HTML templates
│   │   ├── login.html             # Login page
│   │   ├── register.html          # Registration
│   │   ├── dashboard.html         # Main dashboard
│   │   ├── upload.html            # Invoice upload
│   │   ├── processing.html        # Processing status
│   │   ├── review.html            # Manual review page
│   │   ├── history.html           # Invoice history
│   │   ├── reports.html           # Reports & analytics
│   │   └── success.html           # Success confirmation
│   │
│   └── static/
│       ├── css/
│       │   └── styles.css         # Styling
│       └── js/
│           └── main.js            # API wrapper & SPA logic
│
├── media/                         # Uploaded invoices (organized by date)
│   └── invoices/
│       └── originals/
│           └── YYYY/MM/DD/
│
├── logs/                          # Application logs
├── manage.py                      # Django management CLI
├── requirements.txt               # Python dependencies
├── setup.sh                       # Setup script
└── README.md                      # This file
```

---

## 🔌 API Endpoints

### Authentication (`/api/auth/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register/` | Register new user |
| POST | `/login/` | Login (returns JWT tokens) |
| POST | `/logout/` | Logout & blacklist token |
| GET | `/profile/` | Get current user profile |
| POST | `/refresh/` | Refresh access token |

### Invoices (`/api/invoices/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | List all invoices (paginated) |
| POST | `/` | Upload invoice |
| GET | `/{id}/` | Retrieve invoice details |
| PATCH | `/{id}/` | Update invoice |
| POST | `/{id}/approve/` | Approve invoice |
| POST | `/{id}/reject/` | Reject invoice |
| POST | `/{id}/flag/` | Flag for review |
| POST | `/{id}/export/` | Export invoice (CSV/JSON/PDF/Excel) |
| GET | `/{id}/status/` | Check processing status |

### Documents (`/api/documents/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/upload/` | Upload document |
| GET | `/{id}/preview/` | Get preview URL |
| DELETE | `/{id}/` | Delete document |

### Reports (`/api/reports/`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/dashboard/` | Dashboard statistics |
| GET | `/stats/` | Aggregated stats |
| GET | `/trends/` | Processing trends |

---

## 🤖 AI Extraction Pipeline

### How It Works

1. **Upload**: User uploads invoice PDF/image
2. **OCR**: Document is processed by AWS Textract (extracts raw text)
3. **AI Extraction**: Groq API (`llama-3.3-70b-versatile`) or Claude API extracts structured fields
4. **Confidence Scoring**: Each extracted field gets a confidence score (0.0–1.0)
5. **Review**: Human reviewer approves, corrects, or rejects
6. **Storage**: Approved data is saved to database
7. **Export**: Data can be exported in multiple formats

### Confidence Scoring

- **0.90–1.00**: Clearly present and unambiguous ✅
- **0.70–0.89**: Found but formatting unusual 🟡
- **0.50–0.69**: Inferred or partially reconstructed ⚠️
- **0.00–0.49**: Very uncertain — flagged for review ❌

### Extracted Fields

The AI extracts the following fields from invoices:

**Vendor Information:**
- `vendor_name` — Company name
- `vendor_address` — Street address
- `vendor_email` — Email address
- `vendor_phone` — Phone number

**Document Info:**
- `invoice_number` — Unique invoice ID
- `invoice_date` — Date issued
- `due_date` — Payment due date
- `po_number` — Purchase order number
- `payment_terms` — Net 30, Net 60, etc.

**Financial:**
- `subtotal_amount` — Amount before tax
- `tax_amount` — Tax/VAT
- `total_amount` — Grand total
- `currency` — Currency code (USD, KES, etc.)

**Line Items:**
- `description` — Item description
- `quantity` — Quantity ordered
- `unit_price` — Price per unit
- `total` — Line total

---

## 📊 Models & Database Schema

### Invoice Model
- Status workflow: Uploading → Processing → Pending Review → Approved/Rejected/Flagged
- Tracks AI confidence scores and processing metadata
- Audit trail for compliance
- Multi-currency support

### ExtractedField Model
- Individual confidence score per field
- Supports manual corrections with audit trail
- Tracks who corrected what and when

### LineItem Model
- Linked to Invoice
- Includes quantity, unit price, totals
- AI confidence per line item

### AuditLog Model
- Immutable audit trail
- Records all actions: uploads, approvals, exports, corrections
- Required for enterprise compliance

---

## 🔐 Authentication & Authorization

### JWT Tokens

The system uses **SimpleJWT** for stateless authentication:

```javascript
// Frontend stores tokens in sessionStorage
{
  access_token: "eyJhbGc...",    // 15 min expiry
  refresh_token: "eyJhbGc...",   // 7 days expiry
  user: {id, email, name, ...}
}
```

### Token Refresh Flow

1. Frontend sends API request with `Authorization: Bearer <access_token>`
2. If token expired (401), frontend uses `refresh_token` to get new `access_token`
3. If refresh fails, user is logged out

---

## 🛠️ Development

### Installing Dependencies

```bash
pip install -r requirements.txt
```

### Running Migrations

```bash
python manage.py migrate
```

### Creating a Superuser

```bash
python manage.py createsuperuser
```

### Running in Debug Mode

```bash
python manage.py runserver
```

### Seeding Demo Data

```bash
python manage.py seed_demo_data
```

---

## 📦 Dependencies

### Backend
- **Django** 5.0.4 — Web framework
- **Django REST Framework** 3.15.1 — REST API
- **SimpleJWT** 5.3.1 — JWT authentication
- **django-cors-headers** 4.3.1 — CORS support
- **Groq** — Free AI inference
- **Anthropic** 0.25.8 — Claude API (optional)
- **Pillow** 10.2.0 — Image processing
- **mysqlclient** 2.2.4 — MySQL driver
- **drf-spectacular** 0.27.1 — API documentation

### Optional
- **Celery** — Task queue for async processing
- **Redis** — Cache & task broker
- **boto3** — AWS SDK (for Textract)

See [requirements.txt](requirements.txt) for full list.

---

## 🚀 Production Deployment

### Checklist

- [ ] Set `DEBUG=False` in settings
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up Redis for Celery
- [ ] Configure Groq or Anthropic API keys
- [ ] Enable HTTPS/SSL
- [ ] Configure ALLOWED_HOSTS
- [ ] Set up email backend
- [ ] Run `python manage.py collectstatic --no-input`
- [ ] Use Gunicorn or similar WSGI server
- [ ] Configure Celery worker processes
- [ ] Set up monitoring and logging

### Example Gunicorn Command

```bash
gunicorn invoiceiq.wsgi:application \
  --workers 4 \
  --worker-class sync \
  --bind 0.0.0.0:8000 \
  --access-logfile - \
  --error-logfile -
```

---

## 📚 API Documentation

Once the server is running, view the interactive API docs:

**Swagger UI:** `http://localhost:8000/api/docs/`

**OpenAPI Schema:** `http://localhost:8000/api/schema/`

---

## 🐛 Troubleshooting

### Database Connection Error

```
Error: 2003, "Can't connect to MySQL server"
```

**Solutions:**
1. Verify MySQL is running: `mysql -u root -p`
2. Check `DB_*` settings in `.env`
3. Ensure database exists: `CREATE DATABASE invoiceiq_db;`

### Groq API Errors

```
Error: GROQ_API_KEY not set
```

**Solutions:**
1. Get free API key at [console.groq.com](https://console.groq.com)
2. Add to `.env`: `GROQ_API_KEY=your-key`

### Static Files Not Loading

```
python manage.py collectstatic --noinput
```

### Token Expired / JWT Errors

- Check token in `sessionStorage` (DevTools → Application)
- Token should be automatically refreshed
- Force logout: `sessionStorage.clear()` → refresh page

---

## 📝 License

[Add your license here]

---

## 🤝 Contributing

[Add contribution guidelines]

---

## 📧 Support

For issues, questions, or feature requests, please [create an issue](https://github.com/yourrepo/issues) or contact the team.

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
#   I n v o i c e Q 
 
 