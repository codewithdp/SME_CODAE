# Excel-PDF Reconciliation System - Implementation Guide

## 📋 Overview

A production-ready web-based reconciliation system that compares Excel files with their corresponding PDF documents. Built for processing ~500 reconciliations monthly with exact cell-level mismatch detection across three key sections.

**Key Features:**
- ✅ Azure Document Intelligence for reliable PDF extraction
- ✅ Cell-level mismatch detection with coordinates
- ✅ Multi-page PDF stitching (automatically combines page 1 & 2)
- ✅ Confidence scoring with configurable thresholds
- ✅ Downloadable Excel/PDF reports
- ✅ Web-based drag-and-drop interface
- ✅ Real-time processing status updates

---

## 🏗️ Architecture

```
Frontend (React + TypeScript)
    ↓ HTTPS/REST
Backend (FastAPI + Python)
    ↓
Processing Layer (Celery Tasks)
    ├─ Excel Parser (openpyxl)
    ├─ PDF Processor (Azure Document Intelligence)
    └─ Reconciliation Engine
    ↓
Data Layer
    ├─ PostgreSQL (metadata)
    ├─ Azure Blob Storage (files)
    └─ Redis (task queue)
```

---

## 📦 Project Structure

```
reconciliation-system/
├── backend/
│   ├── app/
│   │   ├── main_api.py              # FastAPI application
│   │   ├── excel_parser.py          # Excel parsing module
│   │   ├── pdf_processor.py         # PDF processing with Azure DI
│   │   ├── reconciliation_engine.py # Comparison logic
│   │   ├── models.py                # Database models
│   │   ├── tasks.py                 # Celery tasks
│   │   └── config.py                # Configuration
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── UploadPage.tsx
│   │   │   ├── ProcessingPage.tsx
│   │   │   ├── ResultsPage.tsx
│   │   │   └── HistoryPage.tsx
│   │   ├── api/
│   │   │   └── reconciliationApi.ts
│   │   ├── App.tsx
│   │   └── index.tsx
│   ├── package.json
│   └── Dockerfile
├── infrastructure/
│   ├── azure-resources.bicep        # Infrastructure as Code
│   └── deploy.sh
├── docs/
│   └── reconciliation_system_design.md
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

1. **Azure Account** with:
   - Azure Document Intelligence resource
   - Azure Storage Account
   - Azure Database for PostgreSQL
   - Azure Redis Cache

2. **Development Tools**:
   - Python 3.11+
   - Node.js 18+
   - Docker & Docker Compose
   - Git

### Local Development Setup

#### 1. Clone & Setup Backend

```bash
# Clone repository
git clone <your-repo-url>
cd reconciliation-system/backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
# Edit .env with your Azure credentials
```

#### 2. Configure Environment Variables

Edit `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/reconciliation

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
AZURE_STORAGE_CONTAINER=reconciliation-files

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key-here

# Processing Configuration
MIN_PDF_CONFIDENCE=0.75
MAX_FILE_SIZE_MB=50

# Redis (for Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

#### 3. Setup Database

```bash
# Start PostgreSQL (using Docker)
docker run --name postgres-reconciliation \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=reconciliation \
  -p 5432:5432 \
  -d postgres:15

# Run migrations
python -c "from app.main_api import Base, engine; Base.metadata.create_all(bind=engine)"
```

#### 4. Start Redis

```bash
# Using Docker
docker run --name redis-reconciliation \
  -p 6379:6379 \
  -d redis:7-alpine
```

#### 5. Start Backend Services

```bash
# Terminal 1: Start FastAPI server
uvicorn app.main_api:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Celery worker
celery -A app.main_api.celery_app worker --loglevel=info

# Terminal 3 (optional): Start Celery Flower for monitoring
celery -A app.main_api.celery_app flower --port=5555
```

#### 6. Setup Frontend

```bash
cd ../frontend

# Install dependencies
npm install

# Copy environment template
cp .env.example .env
# Edit with backend API URL

# Start development server
npm start
```

Frontend will be available at `http://localhost:3000`

---

## 🔧 Configuration Details

### Excel Parser Configuration

The Excel parser expects a specific structure. Adjust cell references in `excel_parser.py` based on your actual Excel layout:

```python
# In _extract_header()
emei_code=self._get_cell_value("B3", "header.emei_code")

# In _extract_section1_enrollment()
enrollment_rows = [
    ("INTEGRAL (4 a 6 horas)", 10),
    ("PERÍODO MATUTINO", 11),
    # ... adjust row numbers
]
```

### PDF Processor Configuration

Azure Document Intelligence settings in `pdf_processor.py`:

```python
# Model selection
model = "prebuilt-document"  # General form/table extraction

# Confidence threshold
min_confidence = 0.75  # Adjust based on PDF quality

# Table extraction
# Automatically detects and extracts tables from both pages
```

### Reconciliation Rules

Configure comparison behavior in `reconciliation_engine.py`:

```python
# Exact match required (no tolerance)
def _compare_cell(excel_val, pdf_val):
    return excel_val == pdf_val  # Strict equality

# Section identification heuristics
if table.row_count <= 6:  # Section 1
    section1_table = table
elif table.row_count >= 20 and table.column_count <= 7:  # Section 2
    section2_table = table
```

---

## 🧪 Testing

### Unit Tests

```bash
cd backend
pytest tests/ -v

# Run specific test file
pytest tests/test_excel_parser.py -v

# With coverage
pytest --cov=app tests/
```

### Integration Tests

```bash
# Test full reconciliation pipeline
pytest tests/test_integration.py -v

# Test with sample files
python -m app.test_reconciliation \
  --excel samples/019382.xlsm \
  --pdf samples/EMEI_test1.pdf
```

### API Tests

```bash
# Using httpie
http POST localhost:8000/api/v1/reconciliation/upload \
  excel_file@samples/019382.xlsm \
  pdf_file@samples/EMEI_test1.pdf

# Get status
http GET localhost:8000/api/v1/reconciliation/{id}/status
```

---

## 📊 Sample Data Requirements

### Excel File Structure

Your Excel files should have:

1. **Header Section** (rows 1-6):
   - EMEI code
   - School information
   - Address, CEP
   - Company name
   - Month, Year

2. **Section 1** (rows ~8-14): Student enrollment
   - Columns: Period | Enrolled | Special Diet A | Special Diet B
   - Total row at bottom

3. **Section 2** (rows ~20-50): Frequency data
   - Columns: Day | Frequency A | Lunch A | Frequency B | Lunch B | Emergency

4. **Section 3** (rows ~60-90): Daily attendance grid
   - Columns: Day | 1º Período (Breakfast, Lunch) | 2º Período | ... | 3º Período
   - 30-31 rows for each day of month

### PDF File Structure

- **Page 1**: Header + Section 1 + Section 3 (partial)
- **Page 2**: Section 2 + Section 3 (continuation)

The system automatically stitches both pages together.

---

## 🚢 Production Deployment

### Option 1: Azure App Service (Recommended)

#### Deploy Backend

```bash
# Login to Azure
az login

# Create resource group
az group create --name rg-reconciliation-prod --location brazilsouth

# Create App Service Plan
az appservice plan create \
  --name asp-reconciliation-prod \
  --resource-group rg-reconciliation-prod \
  --sku P1V2 \
  --is-linux

# Create Web App
az webapp create \
  --name app-reconciliation-api-prod \
  --resource-group rg-reconciliation-prod \
  --plan asp-reconciliation-prod \
  --runtime "PYTHON|3.11"

# Configure environment variables
az webapp config appsettings set \
  --name app-reconciliation-api-prod \
  --resource-group rg-reconciliation-prod \
  --settings @appsettings.json

# Deploy code
az webapp up \
  --name app-reconciliation-api-prod \
  --resource-group rg-reconciliation-prod \
  --runtime "PYTHON:3.11"
```

#### Deploy Frontend

```bash
# Build React app
cd frontend
npm run build

# Deploy to Azure Static Web Apps
az staticwebapp create \
  --name app-reconciliation-web \
  --resource-group rg-reconciliation-prod \
  --source ./build \
  --location brazilsouth
```

### Option 2: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: reconciliation
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    
  redis:
    image: redis:7-alpine
    
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/reconciliation
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
  
  celery:
    build: ./backend
    command: celery -A app.main_api.celery_app worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@postgres:5432/reconciliation
      - CELERY_BROKER_URL=redis://redis:6379/0
    depends_on:
      - postgres
      - redis
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"

volumes:
  postgres_data:
```

Deploy:

```bash
docker-compose up -d
```

### Option 3: Kubernetes (Azure AKS)

See `infrastructure/k8s/` for Kubernetes manifests.

---

## 📈 Monitoring & Logging

### Application Insights

```python
# Backend automatically logs to Application Insights
from opencensus.ext.azure.log_exporter import AzureLogHandler

logger.addHandler(AzureLogHandler(
    connection_string=f'InstrumentationKey={APPINSIGHTS_KEY}'
))
```

### Key Metrics to Monitor

1. **Processing Metrics**:
   - Reconciliations processed per hour
   - Average processing time
   - Success/failure rate

2. **PDF Quality Metrics**:
   - Average confidence score
   - Low confidence incidents
   - Pages processed

3. **Performance Metrics**:
   - API response time
   - Celery queue length
   - Database query time

### Alerts Setup

```bash
# Alert on high error rate
az monitor metrics alert create \
  --name high-error-rate \
  --resource-group rg-reconciliation-prod \
  --scopes /subscriptions/.../resourceGroups/rg-reconciliation-prod/providers/Microsoft.Web/sites/app-reconciliation-api-prod \
  --condition "count totalRequests where resultCode >= 500 > 10" \
  --window-size 5m \
  --evaluation-frequency 1m
```

---

## 🔐 Security Best Practices

### 1. Secure Secrets Management

```bash
# Store secrets in Azure Key Vault
az keyvault create \
  --name kv-reconciliation-prod \
  --resource-group rg-reconciliation-prod

# Add secrets
az keyvault secret set \
  --vault-name kv-reconciliation-prod \
  --name "AZURE-DI-KEY" \
  --value "your-key"

# Use in app
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

credential = DefaultAzureCredential()
client = SecretClient(vault_url="https://kv-reconciliation-prod.vault.azure.net/", credential=credential)
secret = client.get_secret("AZURE-DI-KEY")
```

### 2. Network Security

- Enable HTTPS only
- Configure CORS properly
- Use Azure Private Link for database
- Enable Azure Firewall

### 3. Data Protection

- Enable Azure Storage encryption at rest
- Use TLS 1.2+ for all connections
- Implement data retention policies
- Regular backups (35-day retention)

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Excel File Won't Parse

**Error**: `File is not a zip file`

**Solution**:
```bash
# Check file format
file your-file.xlsm

# If it's actually XLS (older format), convert it:
libreoffice --headless --convert-to xlsx your-file.xls
```

#### 2. PDF Confidence Too Low

**Error**: `PDF confidence below threshold`

**Solutions**:
- Improve PDF quality (re-scan at higher DPI)
- Adjust threshold: `MIN_PDF_CONFIDENCE=0.65`
- Use manual review for low-confidence areas

#### 3. Azure DI Rate Limits

**Error**: `Rate limit exceeded`

**Solutions**:
- Upgrade to higher tier (S0)
- Implement exponential backoff
- Cache results when possible

#### 4. Celery Tasks Stuck

**Check task status**:
```bash
celery -A app.main_api.celery_app inspect active
celery -A app.main_api.celery_app purge  # Clear queue
```

#### 5. Database Connection Issues

```bash
# Test connection
psql postgresql://user:pass@host:5432/reconciliation

# Check connection pool
from sqlalchemy import inspect
print(engine.pool.status())
```

---

## 📚 API Documentation

### Interactive API Docs

Once the backend is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Key Endpoints

#### Upload Files
```http
POST /api/v1/reconciliation/upload
Content-Type: multipart/form-data

excel_file: <file>
pdf_file: <file>

Response:
{
  "reconciliation_id": "uuid",
  "status": "processing",
  "message": "Files uploaded successfully"
}
```

#### Check Status
```http
GET /api/v1/reconciliation/{id}/status

Response:
{
  "reconciliation_id": "uuid",
  "status": "completed",
  "progress_percentage": 100,
  "result": { ... }
}
```

#### Download Report
```http
GET /api/v1/reconciliation/{id}/report?format=excel

Response: File download
```

---

## 💰 Cost Estimation

### Monthly Costs (500 reconciliations)

| Service | Tier | Cost (USD) |
|---------|------|-----------|
| App Service | P1V2 | $146 |
| PostgreSQL | 2 vCore | $146 |
| Redis Cache | C1 | $35 |
| Blob Storage | 250 GB | $5 |
| Document Intelligence | 1,000 pages | $1.50 |
| Application Insights | 5 GB | $0 |
| **TOTAL** | | **~$334/month** |

### Cost Optimization

1. **Use Azure Reserved Instances**: Save 30-40%
2. **Scale down off-hours**: Use Azure Automation
3. **Archive old files**: Move to Cool/Archive tier after 90 days
4. **Optimize image sizes**: Reduce blob storage costs

---

## 🔄 Backup & Recovery

### Database Backups

```bash
# Automated backups (configured in Azure)
az postgres flexible-server backup list \
  --resource-group rg-reconciliation-prod \
  --name psql-reconciliation-prod

# Manual backup
pg_dump -h host -U user reconciliation > backup_$(date +%Y%m%d).sql

# Restore
psql -h host -U user reconciliation < backup_20250101.sql
```

### Blob Storage Backups

```bash
# Enable soft delete
az storage blob service-properties delete-policy update \
  --account-name streonciliation \
  --enable true \
  --days-retained 30

# Copy to backup storage account
azcopy copy \
  "https://source.blob.core.windows.net/reconciliation-files/*" \
  "https://backup.blob.core.windows.net/reconciliation-backup/" \
  --recursive
```

---

## 🎯 Performance Tuning

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_reconciliations_created_at ON reconciliations(created_at DESC);
CREATE INDEX idx_reconciliations_emei_status ON reconciliations(emei_id, status);

-- Vacuum regularly
VACUUM ANALYZE reconciliations;
```

### Celery Optimization

```python
# celery_config.py
celery_app.conf.update(
    worker_prefetch_multiplier=4,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    task_soft_time_limit=300,
    task_time_limit=600
)
```

### Caching Strategy

```python
# Add Redis caching for frequently accessed data
from redis import Redis
redis_client = Redis(host='localhost', port=6379)

@lru_cache(maxsize=100)
def get_reconciliation(reconciliation_id):
    # Check cache first
    cached = redis_client.get(f"recon:{reconciliation_id}")
    if cached:
        return json.loads(cached)
    # ... fetch from database
```

---

## 📞 Support & Contributing

### Getting Help

- 📧 Email: support@yourcompany.com
- 💬 Slack: #reconciliation-support
- 📖 Wiki: https://wiki.yourcompany.com/reconciliation

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write tests
5. Submit a pull request

### Code Style

```bash
# Format Python code
black app/
isort app/

# Lint
flake8 app/
mypy app/

# Format TypeScript
cd frontend
npm run lint
npm run format
```

---

## 📝 License

Copyright © 2025 Your Company. All rights reserved.

---

## 🎉 Acknowledgments

Built with:
- FastAPI
- React
- Azure Document Intelligence
- PostgreSQL
- Celery

---

**Last Updated**: November 2025  
**Version**: 1.0.0  
**Author**: Your Team
