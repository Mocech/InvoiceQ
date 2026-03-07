# InvoiceIQ

🤖 **AI-powered invoice processing platform** built with Django, Django REST Framework, and Groq/Claude AI. Automatically extract invoice data, review with confidence scores, and manage approvals at scale.

## ✨ Key Features

- 🤖 **AI Field Extraction** — Groq/Claude AI extracts invoice fields with confidence scoring
- ✅ **Approval Workflow** — Upload → Process → Review → Approve/Reject/Flag
- 📊 **Analytics Dashboard** — Real-time stats, trends, and insights
- 🔐 **Enterprise Auth** — JWT-based authentication with multi-user support
- 📝 **Audit Trail** — Complete logging for compliance and accountability
- 💾 **Multi-Format Export** — CSV, JSON, Excel, PDF
- 🌍 **Multi-Currency** — Support for USD, KES, EUR, GBP, ZAR
- 📱 **Responsive UI** — Modern HTML/CSS/JavaScript frontend

## 🏗️ Architecture

**Frontend Layer:**
- HTML templates, vanilla JavaScript, responsive CSS
- Single-page app (SPA) with sessionStorage-based auth
- Pages: Login, Dashboard, Upload, Processing, Review, History, Reports

**API Layer (Django REST Framework):**
- `/api/auth/` — User registration, login, token refresh
- `/api/invoices/` — CRUD operations, status tracking, approvals, exports
- `/api/documents/` — Document upload and preview
- `/api/reports/` — Dashboard analytics and statistics

**Backend Services:**
- **AI Service** — Groq API (`llama-3.3-70b-versatile`) / Claude for field extraction
- **OCR Service** — AWS Textract for document text extraction
- **Export Service** — CSV, JSON, Excel, PDF generation

**Database:**
- MySQL with Django ORM
- Models: Invoice, LineItem, ExtractedField, AuditLog
- Support for multi-currency and audit trails

## 🚀 Installation

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Groq API key ([get free key](https://console.groq.com)) or Anthropic API key
- Redis 7.0+ (optional, for Celery tasks)

### Setup Instructions

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd invoiceiq
   ```

2. **Run the setup script:**
   ```bash
   chmod +x setup.sh
   ./setup.sh
   ```
   This will create a virtual environment, install dependencies, run migrations, and seed demo data.

3. **Configure environment variables** (create `.env` file):
   ```
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   DB_ENGINE=django.db.backends.mysql
   DB_NAME=invoiceiq_db
   DB_USER=root
   DB_PASSWORD=your-mysql-password
   DB_HOST=localhost
   DB_PORT=3306
   
   GROQ_API_KEY=your-groq-api-key
   # OR ANTHROPIC_API_KEY=your-anthropic-key
   ```

4. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

5. **Run the development server:**
   ```bash
   python manage.py runserver
   ```

   Access the app at `http://localhost:8000/` and admin at `http://localhost:8000/admin/`

## 📁 Project Structure

```
invoiceiq/
├── apps/
│   ├── accounts/          # User authentication & organization
│   ├── invoices/          # Core invoice processing
│   │   └── services/      # AI extraction, OCR, export
│   ├── documents/         # Document upload & preview
│   └── reports/           # Analytics & dashboard
├── invoiceiq/             # Django project config (settings, urls, wsgi)
├── frontend/
│   ├── pages/             # HTML templates
│   └── static/css,js/     # CSS & JavaScript
├── logs/                  # Application logs
├── media/                 # Uploaded invoice storage
├── manage.py              # Django CLI
├── requirements.txt       # Python dependencies
├── setup.sh               # Initial setup script
└── README.md              # This file
```

## 🔌 API Endpoints

### Authentication (`/api/auth/`)
- **POST `/register/`** — Register a new user
- **POST `/login/`** — Login and receive JWT tokens
- **POST `/logout/`** — Logout and blacklist token
- **GET `/profile/`** — Get current user profile
- **POST `/refresh/`** — Refresh access token

### Invoices (`/api/invoices/`)
- **GET `/`** — List all invoices (paginated)
- **POST `/`** — Upload a new invoice
- **GET `/{id}/`** — Retrieve invoice details
- **PATCH `/{id}/`** — Update invoice
- **POST `/{id}/approve/`** — Approve invoice
- **POST `/{id}/reject/`** — Reject invoice
- **POST `/{id}/flag/`** — Flag for review
- **POST `/{id}/export/`** — Export invoice (CSV/JSON/PDF/Excel)
- **GET `/{id}/status/`** — Check processing status

### Documents (`/api/documents/`)
- **POST `/upload/`** — Upload document
- **GET `/{id}/preview/`** — Get preview URL
- **DELETE `/{id}/`** — Delete document

### Reports (`/api/reports/`)
- **GET `/dashboard/`** — Dashboard statistics
- **GET `/stats/`** — Aggregated processing stats
- **GET `/trends/`** — Processing trends over time

## 🤖 AI Extraction Pipeline

### Processing Steps

1. **Upload** — User uploads invoice (PDF/image)
2. **OCR** — Extract text using AWS Textract
3. **AI Extraction** — Groq API extracts structured fields
4. **Confidence Scoring** — Each field gets a score (0.0–1.0)
5. **Review** — Human reviewer approves or corrects
6. **Storage** — Approved data saved to database
7. **Export** — Export in CSV, JSON, Excel, or PDF

### Extracted Fields

**Vendor:** vendor_name, vendor_address, vendor_email, vendor_phone  
**Document:** invoice_number, invoice_date, due_date, po_number, payment_terms  
**Financial:** subtotal_amount, tax_amount, total_amount, currency  
**Line Items:** description, quantity, unit_price, total

### Confidence Levels

- 🟢 **0.90–1.00** — Clearly present and unambiguous
- 🟡 **0.70–0.89** — Found but formatting was unusual
- 🟠 **0.50–0.69** — Inferred or partially reconstructed
- 🔴 **0.00–0.49** — Very uncertain, flagged for review

## 💾 Database Models

- **Invoice** — Core invoice record with status, dates, amounts, AI metadata
- **ExtractedField** — Individual field with confidence score and correction history
- **LineItem** — Invoice line items (quantity, unit price, total)
- **AuditLog** — Immutable audit trail for compliance (who did what, when)

## 🔐 Authentication

- **JWT Tokens** — Access token (15 min) + Refresh token (7 days)
- **Token Storage** — sessionStorage on frontend
- **Auto-Refresh** — Frontend automatically refreshes expired tokens
- **Token Blacklist** — Logout invalidates tokens via SimpleJWT

## 💻 Development

### Common Commands

```bash
# Run migrations
python manage.py migrate

# Create admin user
python manage.py createsuperuser

# Start development server
python manage.py runserver

# Seed demo data
python manage.py seed_demo_data

# Collect static files
python manage.py collectstatic --noinput
```

### Dependencies

**Core:**
- Django 5.0+
- Django REST Framework
- SimpleJWT (authentication)
- django-cors-headers

**AI & Processing:**
- Groq SDK (free inference)
- Anthropic SDK (Claude API)
- Pillow (image processing)

**Database:**
- mysqlclient (MySQL driver)

**API Docs:**
- drf-spectacular (OpenAPI/Swagger)

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure production MySQL database
- [ ] Set up Redis for Celery (optional)
- [ ] Configure Groq or Anthropic API keys
- [ ] Enable HTTPS/SSL
- [ ] Set proper `ALLOWED_HOSTS`
- [ ] Run `python manage.py collectstatic --no-input`
- [ ] Use Gunicorn or similar WSGI server
- [ ] Set up monitoring and logging

### Example Gunicorn

```bash
gunicorn invoiceiq.wsgi:application \
  --workers 4 \
  --bind 0.0.0.0:8000
```

## 📖 Documentation

- **API Docs (Swagger):** After running the server, visit `http://localhost:8000/api/docs/`
- **OpenAPI Schema:** `http://localhost:8000/api/schema/`

## 🐛 Troubleshooting

**MySQL connection error?**
- Verify MySQL is running and database exists
- Check credentials in `.env`

**Groq API errors?**
- Get free key at [console.groq.com](https://console.groq.com)
- Add `GROQ_API_KEY` to `.env`

**Static files not loading?**
- Run: `python manage.py collectstatic --noinput`

**JWT token issues?**
- Tokens in `sessionStorage` are auto-refreshed
- Clear cache if issues persist: `sessionStorage.clear()`

## 📄 License

[Add your license information here]

## 🤝 Contributing

Contributions are welcome! Please open an issue or submit a pull request.

## 📧 Support

For questions or issues, please [create an issue](https://github.com/yourrepo/issues) or contact the team.

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