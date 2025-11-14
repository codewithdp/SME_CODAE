# Excel-PDF Reconciliation System - Complete Design Document

## Executive Summary
A web-based reconciliation system to compare Excel files with their corresponding PDF prints, processing ~500 reconciliations monthly. The system will identify mismatches across three key sections: student enrollment numbers, attendance frequency, and detailed attendance grids spanning 2 PDF pages.

---

## 1. SYSTEM ARCHITECTURE

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│                    (React + TypeScript)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ File Upload  │  │ Progress     │  │ Results      │         │
│  │ Component    │  │ Monitor      │  │ Dashboard    │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST API
┌────────────────────────▼────────────────────────────────────────┐
│                      API GATEWAY LAYER                          │
│                   (FastAPI + Pydantic)                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ Upload API   │  │ Status API   │  │ Report API   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                    PROCESSING LAYER                             │
│  ┌──────────────────────────────────────────────────────┐      │
│  │           Celery Task Queue                          │      │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────┐ │      │
│  │  │ Excel Parser │  │ PDF Processor│  │Reconciler │ │      │
│  │  └──────────────┘  └──────────────┘  └───────────┘ │      │
│  └──────────────────────────────────────────────────────┘      │
│                                                                  │
│  ┌──────────────────────────────────────────────────────┐      │
│  │         Azure Document Intelligence                  │      │
│  │  - Form Recognition  - Table Extraction              │      │
│  │  - OCR with Confidence Scoring                       │      │
│  └──────────────────────────────────────────────────────┘      │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                      DATA LAYER                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │ PostgreSQL   │  │ Azure Blob   │  │ Redis Cache  │         │
│  │ (Metadata)   │  │ Storage      │  │ (Sessions)   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 Technology Stack Details

#### **Frontend**
- **Framework**: React 18 + TypeScript
- **UI Library**: shadcn/ui + Tailwind CSS
- **State Management**: React Query (TanStack Query) for server state
- **File Upload**: react-dropzone
- **Data Visualization**: recharts for metrics charts
- **PDF Viewer**: react-pdf for side-by-side comparison

#### **Backend**
- **API Framework**: FastAPI (Python 3.11+)
- **Task Queue**: Celery with Redis broker
- **Excel Processing**: openpyxl, pandas
- **PDF Processing**: 
  - Azure Document Intelligence SDK (primary)
  - pdfplumber (fallback/supplementary)
- **Validation**: Pydantic v2
- **Authentication**: Azure AD B2C (future-ready)

#### **Azure Services**
- **Azure App Service**: Host FastAPI backend (Linux, Python 3.11)
- **Azure Document Intelligence**: OCR and form recognition
- **Azure Blob Storage**: File storage (hot tier for recent, cool for archive)
- **Azure Database for PostgreSQL**: Flexible Server
- **Azure Redis Cache**: Session & task queue
- **Azure Application Insights**: Monitoring & logging
- **Azure Key Vault**: Secrets management

#### **Database Schema**
- **PostgreSQL**: Reconciliation metadata, results, audit logs
- **Blob Storage**: Original files (Excel, PDF) and generated reports

---

## 2. DETAILED COMPONENT DESIGN

### 2.1 Excel Parser Module

```python
# Core structure
class ExcelParser:
    """
    Parses Excel files and extracts structured data from three sections
    """
    
    def parse_emei_sheet(self, file_path: str) -> ReconciliationData:
        """
        Extract data from EMEI sheet
        Returns structured data object with:
        - Header info (EMEI ID, address, company name)
        - Section 1: Student enrollment numbers
        - Section 2: Attendance frequency  
        - Section 3: Daily attendance grid
        """
        pass
    
    def extract_header(self, worksheet) -> HeaderData:
        """Extract EMEI ID, CEP, address from top rows"""
        pass
    
    def extract_section1_enrollment(self, worksheet) -> EnrollmentData:
        """Extract student counts by period and education level"""
        pass
    
    def extract_section2_frequency(self, worksheet) -> FrequencyData:
        """Extract attendance frequency data (page 2 equivalent)"""
        pass
    
    def extract_section3_daily_grid(self, worksheet) -> DailyAttendanceGrid:
        """Extract the large daily attendance table"""
        pass
```

**Key Features**:
- Cell-level extraction with coordinates tracking
- Data validation against expected schema
- Handles merged cells and complex formatting
- Returns structured Python objects (Pydantic models)

### 2.2 PDF Processor Module

```python
class PDFProcessor:
    """
    Processes PDF using Azure Document Intelligence
    Handles 2-page structure and stitches data together
    """
    
    def __init__(self, azure_client):
        self.client = azure_client
        self.min_confidence = 0.75  # Configurable threshold
    
    async def process_pdf(self, pdf_path: str) -> PDFExtractionResult:
        """
        Main processing pipeline:
        1. Send to Azure Document Intelligence
        2. Extract tables and key-value pairs
        3. Stitch page 1 and page 2 data
        4. Return structured data with confidence scores
        """
        pass
    
    async def extract_with_form_recognizer(self, pdf_bytes) -> FormResult:
        """Use prebuilt-document model for table extraction"""
        pass
    
    def stitch_pages(self, page1_data, page2_data) -> PDFReconciliationData:
        """
        Combine data from both pages:
        - Page 1: Header + Section 1 + Section 3 (partial grid)
        - Page 2: Section 2 + Section 3 (continuation)
        """
        pass
    
    def check_confidence_threshold(self, results) -> ConfidenceReport:
        """
        Check if OCR confidence meets minimum threshold
        Return: {meets_threshold: bool, low_confidence_areas: list}
        """
        pass
```

**Azure Document Intelligence Configuration**:
- **Model**: `prebuilt-document` for general forms and tables
- **Features**: Tables, key-value pairs, text extraction
- **Confidence Tracking**: Per-field confidence scores
- **Fallback Strategy**: If confidence < 75%, flag for manual review

### 2.3 Reconciliation Engine

```python
class ReconciliationEngine:
    """
    Core reconciliation logic - compares Excel vs PDF data
    """
    
    def reconcile(self, 
                  excel_data: ReconciliationData, 
                  pdf_data: PDFReconciliationData) -> ReconciliationResult:
        """
        Main reconciliation process:
        1. Validate ID match (filename vs PDF header)
        2. Compare Section 1 (enrollment numbers)
        3. Compare Section 2 (frequency data)
        4. Compare Section 3 (daily attendance grid)
        5. Generate mismatch report
        """
        pass
    
    def compare_section1(self, excel_s1, pdf_s1) -> SectionResult:
        """Compare enrollment numbers - exact match required"""
        pass
    
    def compare_section2(self, excel_s2, pdf_s2) -> SectionResult:
        """Compare frequency data"""
        pass
    
    def compare_section3(self, excel_s3, pdf_s3) -> SectionResult:
        """
        Compare daily attendance grid:
        - Day by day comparison
        - Meal type by meal type (breakfast, lunch, dinner)
        - Track row/column position of mismatches
        """
        pass
    
    def generate_mismatch_report(self, results) -> MismatchReport:
        """
        Create detailed report:
        - Total mismatches count
        - Mismatches by section
        - Cell-level details (Excel cell vs PDF cell)
        - Coordinates for highlighting
        """
        pass
```

**Reconciliation Data Models**:

```python
from pydantic import BaseModel
from typing import List, Optional

class CellMismatch(BaseModel):
    section: str  # "Section 1", "Section 2", "Section 3"
    excel_cell: str  # e.g., "B15"
    excel_value: any
    pdf_value: any
    row_label: str  # e.g., "Day 4", "Breakfast"
    column_label: str
    
class SectionResult(BaseModel):
    section_name: str
    total_cells_compared: int
    mismatches: List[CellMismatch]
    match_percentage: float

class ReconciliationResult(BaseModel):
    reconciliation_id: str
    emei_id: str
    excel_filename: str
    pdf_filename: str
    timestamp: datetime
    
    id_match: bool  # Does Excel filename match PDF header?
    pdf_confidence_ok: bool
    low_confidence_areas: List[str]
    
    section1_result: SectionResult
    section2_result: SectionResult
    section3_result: SectionResult
    
    total_mismatches: int
    overall_match_percentage: float
    
    row_count_excel: int
    row_count_pdf: int
    row_count_match: bool
```

### 2.4 Report Generator

```python
class ReportGenerator:
    """
    Generates downloadable reconciliation reports
    """
    
    def generate_excel_report(self, result: ReconciliationResult) -> bytes:
        """
        Excel report with:
        - Summary sheet (metrics, overall results)
        - Mismatches sheet (detailed list with coordinates)
        - Conditional formatting to highlight issues
        """
        pass
    
    def generate_pdf_report(self, result: ReconciliationResult) -> bytes:
        """
        PDF report with:
        - Executive summary
        - Section-by-section breakdown
        - Mismatch tables
        """
        pass
```

---

## 3. API DESIGN

### 3.1 REST Endpoints

#### **Upload & Process**
```
POST /api/v1/reconciliation/upload
Request:
  - multipart/form-data
  - excel_file: File
  - pdf_file: File
  
Response: 
{
  "reconciliation_id": "uuid",
  "status": "processing",
  "message": "Files uploaded successfully"
}
```

#### **Check Status**
```
GET /api/v1/reconciliation/{reconciliation_id}/status

Response:
{
  "reconciliation_id": "uuid",
  "status": "completed|processing|failed",
  "progress_percentage": 75,
  "current_step": "Comparing Section 3",
  "result": ReconciliationResult | null
}
```

#### **Download Report**
```
GET /api/v1/reconciliation/{reconciliation_id}/report?format=excel|pdf

Response: File download
```

#### **List Reconciliations**
```
GET /api/v1/reconciliations?page=1&limit=20

Response:
{
  "items": [ReconciliationResult],
  "total": 150,
  "page": 1,
  "pages": 8
}
```

### 3.2 WebSocket for Real-Time Updates (Optional Enhancement)

```
WS /ws/reconciliation/{reconciliation_id}

Messages:
{
  "type": "progress_update",
  "step": "Parsing Excel",
  "percentage": 25
}
```

---

## 4. USER INTERFACE DESIGN

### 4.1 Main Pages

#### **Page 1: Upload Page**
- Drag & drop zone for Excel file
- Drag & drop zone for PDF file
- File validation (shows filename match validation)
- "Start Reconciliation" button
- Shows uploaded file previews

#### **Page 2: Processing Page**
- Progress bar with steps:
  1. Uploading files (10%)
  2. Parsing Excel (20%)
  3. Processing PDF (40%)
  4. Extracting tables (60%)
  5. Comparing data (80%)
  6. Generating report (90%)
  7. Complete (100%)
- Real-time status messages
- Cancel option

#### **Page 3: Results Dashboard**
- **Summary Card**:
  - EMEI ID
  - Excel filename / PDF filename
  - ID Match: ✓ / ✗
  - Overall Match: 98.5%
  - Total Mismatches: 12
  
- **Section Breakdown Cards**:
  - Section 1: X mismatches
  - Section 2: Y mismatches  
  - Section 3: Z mismatches
  
- **Mismatch Table**:
  | Section | Excel Cell | Excel Value | PDF Value | Row | Column |
  |---------|-----------|-------------|-----------|-----|--------|
  | Section 3 | F15 | 225 | 224 | Day 4 | Breakfast |
  
- **Actions**:
  - Download Excel Report
  - Download PDF Report
  - View Side-by-Side Comparison

- **Warnings Section** (if applicable):
  - Low PDF confidence warning
  - Row count mismatch warning

#### **Page 4: History/List Page**
- Table of all past reconciliations
- Filters: Date range, Status, EMEI ID
- Search functionality
- Click to view details

### 4.2 UI Components Structure

```typescript
// Key React components

// Upload page
<ReconciliationUpload />
  ├─ <FileDropZone type="excel" />
  ├─ <FileDropZone type="pdf" />
  ├─ <FileValidation />
  └─ <SubmitButton />

// Processing page  
<ProcessingMonitor reconciliationId={id} />
  ├─ <ProgressBar />
  ├─ <StatusMessages />
  └─ <CancelButton />

// Results page
<ReconciliationResults data={result} />
  ├─ <SummaryCards />
  ├─ <SectionBreakdown />
  ├─ <MismatchTable />
  ├─ <WarningsAlert />
  └─ <ReportDownloads />

// History page
<ReconciliationHistory />
  ├─ <FilterBar />
  ├─ <ResultsTable />
  └─ <Pagination />
```

---

## 5. DATABASE SCHEMA

### 5.1 PostgreSQL Tables

```sql
-- Main reconciliations table
CREATE TABLE reconciliations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    emei_id VARCHAR(50) NOT NULL,
    excel_filename VARCHAR(255) NOT NULL,
    pdf_filename VARCHAR(255) NOT NULL,
    
    -- File references
    excel_blob_url TEXT NOT NULL,
    pdf_blob_url TEXT NOT NULL,
    
    -- Status
    status VARCHAR(20) NOT NULL, -- processing, completed, failed
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    -- Results
    id_match BOOLEAN,
    pdf_confidence_ok BOOLEAN,
    total_mismatches INT,
    overall_match_percentage DECIMAL(5,2),
    
    -- Row counts
    excel_row_count INT,
    pdf_row_count INT,
    row_count_match BOOLEAN,
    
    -- Report URLs
    excel_report_url TEXT,
    pdf_report_url TEXT,
    
    -- Full result JSON
    result_data JSONB,
    
    -- Audit
    created_by VARCHAR(255),
    
    INDEX idx_emei (emei_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at DESC)
);

-- Section results (for faster querying)
CREATE TABLE section_results (
    id SERIAL PRIMARY KEY,
    reconciliation_id UUID REFERENCES reconciliations(id) ON DELETE CASCADE,
    section_name VARCHAR(20) NOT NULL, -- Section1, Section2, Section3
    total_cells_compared INT,
    mismatch_count INT,
    match_percentage DECIMAL(5,2),
    
    INDEX idx_reconciliation (reconciliation_id)
);

-- Individual mismatches (for detailed analysis)
CREATE TABLE mismatches (
    id SERIAL PRIMARY KEY,
    reconciliation_id UUID REFERENCES reconciliations(id) ON DELETE CASCADE,
    section_name VARCHAR(20),
    excel_cell VARCHAR(10),
    excel_value TEXT,
    pdf_value TEXT,
    row_label VARCHAR(100),
    column_label VARCHAR(100),
    
    INDEX idx_reconciliation (reconciliation_id),
    INDEX idx_section (section_name)
);

-- Processing logs
CREATE TABLE processing_logs (
    id SERIAL PRIMARY KEY,
    reconciliation_id UUID REFERENCES reconciliations(id) ON DELETE CASCADE,
    step VARCHAR(100),
    status VARCHAR(20),
    message TEXT,
    timestamp TIMESTAMP DEFAULT NOW(),
    
    INDEX idx_reconciliation (reconciliation_id)
);

-- Low confidence areas (for PDF quality issues)
CREATE TABLE low_confidence_areas (
    id SERIAL PRIMARY KEY,
    reconciliation_id UUID REFERENCES reconciliations(id) ON DELETE CASCADE,
    area_description TEXT,
    confidence_score DECIMAL(3,2),
    page_number INT,
    
    INDEX idx_reconciliation (reconciliation_id)
);
```

### 5.2 Azure Blob Storage Structure

```
Container: reconciliation-files
├── excel/
│   └── {reconciliation_id}/original.xlsm
├── pdf/
│   └── {reconciliation_id}/original.pdf
└── reports/
    ├── {reconciliation_id}/report.xlsx
    └── {reconciliation_id}/report.pdf

Container: archives (Cool tier, after 90 days)
├── excel/
├── pdf/
└── reports/
```

---

## 6. PROCESSING WORKFLOW

### 6.1 Celery Task Chain

```python
from celery import chain

# Main task chain
reconciliation_pipeline = chain(
    upload_files.s(),
    validate_files.s(),
    parse_excel.s(),
    process_pdf.s(),
    check_pdf_confidence.s(),
    run_reconciliation.s(),
    generate_reports.s(),
    update_database.s()
)

# Individual tasks
@celery_app.task(bind=True)
def upload_files(self, reconciliation_id, excel_file, pdf_file):
    """Upload files to Blob Storage"""
    # Update progress: 10%
    pass

@celery_app.task(bind=True)
def validate_files(self, reconciliation_id):
    """Validate file formats and basic structure"""
    # Update progress: 15%
    pass

@celery_app.task(bind=True)
def parse_excel(self, reconciliation_id):
    """Parse Excel using ExcelParser"""
    # Update progress: 35%
    pass

@celery_app.task(bind=True)
def process_pdf(self, reconciliation_id):
    """Process PDF using Azure Document Intelligence"""
    # Update progress: 60%
    pass

@celery_app.task(bind=True)
def check_pdf_confidence(self, reconciliation_id, pdf_result):
    """Check confidence scores"""
    # If confidence < threshold, flag and optionally skip reconciliation
    # Update progress: 65%
    pass

@celery_app.task(bind=True)
def run_reconciliation(self, reconciliation_id, excel_data, pdf_data):
    """Execute reconciliation engine"""
    # Update progress: 85%
    pass

@celery_app.task(bind=True)
def generate_reports(self, reconciliation_id, result):
    """Generate downloadable reports"""
    # Update progress: 95%
    pass

@celery_app.task(bind=True)
def update_database(self, reconciliation_id, result):
    """Save final results to database"""
    # Update progress: 100%
    pass
```

### 6.2 Error Handling Strategy

```python
# Retry configuration
@celery_app.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={'max_retries': 3}
)
def process_pdf(self, reconciliation_id):
    try:
        # Processing logic
        pass
    except AzureDocumentIntelligenceError as e:
        # Log specific Azure errors
        log_error(reconciliation_id, f"Azure DI Error: {str(e)}")
        # Update status to failed
        update_status(reconciliation_id, 'failed', error=str(e))
        raise
    except Exception as e:
        # Generic error handling
        log_error(reconciliation_id, f"Unexpected error: {str(e)}")
        raise
```

---

## 7. DEPLOYMENT ARCHITECTURE

### 7.1 Azure Resources Setup

```yaml
# Resource Group
resource_group: rg-reconciliation-prod
location: Brazil South (or East US for lower latency to US-based users)

# App Service Plan
app_service_plan:
  name: asp-reconciliation-prod
  tier: Premium V2 (P1V2 or P2V2)
  os: Linux
  
# Web App (Backend)
web_app:
  name: app-reconciliation-api-prod
  runtime: Python 3.11
  always_on: true
  
# Static Web App (Frontend) OR App Service
frontend:
  name: app-reconciliation-web-prod
  # Option 1: Azure Static Web Apps (recommended for React)
  # Option 2: App Service with Node.js for SSR if needed
  
# Database
postgresql:
  name: psql-reconciliation-prod
  tier: General Purpose
  compute: 2 vCores
  storage: 128 GB
  backup_retention: 35 days
  
# Redis Cache
redis:
  name: redis-reconciliation-prod
  tier: Standard
  capacity: C1 (1 GB)
  
# Storage Account
storage:
  name: streonciliation[random]
  replication: LRS (or GRS for higher availability)
  containers:
    - reconciliation-files (Hot tier)
    - archives (Cool tier)
    
# Document Intelligence
document_intelligence:
  name: di-reconciliation-prod
  tier: S0 (Standard)
  
# Application Insights
app_insights:
  name: appi-reconciliation-prod
  
# Key Vault
key_vault:
  name: kv-reconciliation-prod
  secrets:
    - postgresql-connection-string
    - redis-connection-string
    - storage-account-key
    - document-intelligence-key
```

### 7.2 CI/CD Pipeline (Azure DevOps or GitHub Actions)

```yaml
# .github/workflows/deploy-prod.yml

name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Backend Tests
        run: |
          cd backend
          pip install -r requirements.txt
          pytest
      - name: Run Frontend Tests
        run: |
          cd frontend
          npm install
          npm test

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to Azure App Service
        uses: azure/webapps-deploy@v2
        with:
          app-name: app-reconciliation-api-prod
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build React App
        run: |
          cd frontend
          npm install
          npm run build
      - name: Deploy to Azure Static Web Apps
        uses: Azure/static-web-apps-deploy@v1
        with:
          azure_static_web_apps_api_token: ${{ secrets.AZURE_STATIC_WEB_APPS_API_TOKEN }}
          repo_token: ${{ secrets.GITHUB_TOKEN }}
          action: "upload"
          app_location: "/frontend"
          output_location: "build"
```

---

## 8. COST ESTIMATION (Monthly)

### 8.1 Azure Service Costs (for 500 reconciliations/month)

| Service | Configuration | Est. Cost (USD) |
|---------|--------------|----------------|
| App Service (Backend) | P1V2 | $146 |
| Static Web App (Frontend) | Free tier | $0 |
| PostgreSQL | General Purpose, 2 vCore | $146 |
| Redis Cache | Standard C1 | $35 |
| Blob Storage | 50 GB Hot, 200 GB Cool | $5 |
| Document Intelligence | 500 pages @ $1.50/1000 | $0.75 |
| Application Insights | Basic (5GB included) | $0 |
| **TOTAL** | | **~$333/month** |

### 8.2 Cost Optimization Strategies

1. **Scale Down Off-Hours**: Use Azure Automation to scale down App Service during nights/weekends
2. **Reserved Instances**: Save 30-40% by purchasing 1-year reserved capacity
3. **Archive Old Files**: Move files >90 days to Cool/Archive tier (saves 50-80% on storage)
4. **Optimize Document Intelligence**: Cache common results, batch process when possible

---

## 9. SECURITY CONSIDERATIONS

### 9.1 Data Security
- **Encryption at Rest**: All data encrypted in Blob Storage and PostgreSQL
- **Encryption in Transit**: HTTPS only, TLS 1.2+
- **Access Control**: Managed Identity for inter-service communication
- **Secrets**: All keys stored in Azure Key Vault

### 9.2 Application Security
- **Input Validation**: File type, size limits (max 50MB per file)
- **CORS**: Restrict to specific frontend domain
- **Rate Limiting**: 10 uploads per hour per user (configurable)
- **File Scanning**: Optional Azure Defender for Storage malware scanning

### 9.3 Authentication (Future Phase)
- Azure AD B2C for user authentication
- Role-based access control (RBAC)
- Audit logging for all operations

---

## 10. MONITORING & OBSERVABILITY

### 10.1 Application Insights Metrics

**Custom Metrics**:
- Reconciliations processed per hour
- Average processing time
- Error rate by step
- PDF confidence score distribution
- Mismatch rate trends

**Alerts**:
- Error rate > 5%
- Average processing time > 5 minutes
- Failed Azure DI calls > 10/hour
- Database connection failures

### 10.2 Logging Strategy

```python
# Structured logging with correlation IDs
import logging
import structlog

logger = structlog.get_logger()

logger.info(
    "reconciliation_started",
    reconciliation_id=rec_id,
    emei_id=emei_id,
    excel_filename=excel_file,
    pdf_filename=pdf_file
)

logger.warning(
    "low_pdf_confidence",
    reconciliation_id=rec_id,
    confidence_score=0.68,
    page=1
)

logger.error(
    "reconciliation_failed",
    reconciliation_id=rec_id,
    step="parse_excel",
    error=str(e)
)
```

### 10.3 Health Checks

```python
# Health check endpoints
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now()
    }

@app.get("/health/detailed")
def detailed_health():
    return {
        "database": check_database(),
        "redis": check_redis(),
        "blob_storage": check_blob(),
        "document_intelligence": check_azure_di()
    }
```

---

## 11. FUTURE ENHANCEMENTS (Phase 2+)

### 11.1 Batch Processing
- Upload multiple Excel-PDF pairs at once
- Process in parallel using multiple Celery workers
- Bulk download reports as ZIP

### 11.2 Advanced Analytics
- Dashboard showing trends over time
- Most common mismatch patterns
- School performance comparisons
- Automated anomaly detection using ML

### 11.3 Intelligent Field Mapping
- Use Azure OpenAI to automatically detect field mappings even if PDF format changes slightly
- Self-learning system that improves with user feedback

### 11.4 Mobile App
- React Native app for on-the-go uploads and review

### 11.5 Integration APIs
- Webhook notifications when reconciliation completes
- REST API for third-party system integration

---

## 12. DEVELOPMENT ROADMAP

### Phase 1: MVP (8-10 weeks)
**Week 1-2**: Setup & Infrastructure
- Azure resource provisioning
- Database schema implementation
- Basic FastAPI skeleton

**Week 3-4**: Core Processing
- Excel parser implementation
- Azure DI integration
- PDF processing pipeline

**Week 5-6**: Reconciliation Engine
- Comparison logic for all 3 sections
- Mismatch detection and reporting
- Database storage

**Week 7-8**: Frontend Development
- React app setup
- Upload UI
- Results dashboard

**Week 9**: Testing & Integration
- End-to-end testing
- Performance testing with real files
- Bug fixes

**Week 10**: Deployment & Documentation
- Production deployment
- User documentation
- Training materials

### Phase 2: Enhancements (4-6 weeks)
- Batch processing
- Advanced reporting
- Performance optimizations

### Phase 3: Analytics & ML (6-8 weeks)
- Analytics dashboard
- OpenAI integration for smart mapping
- Predictive insights

---

## 13. TESTING STRATEGY

### 13.1 Unit Tests
- Excel parser: Test each section extraction
- PDF processor: Mock Azure DI responses
- Reconciliation engine: Test comparison logic with known datasets

### 13.2 Integration Tests
- Full pipeline with sample files
- Database operations
- Blob storage upload/download

### 13.3 Performance Tests
- Process 100 reconciliations concurrently
- Measure average processing time
- Database query performance

### 13.4 User Acceptance Testing
- Test with real Excel and PDF files
- Verify accuracy of mismatch detection
- UI/UX feedback

---

## 14. SUCCESS METRICS

### 14.1 Performance KPIs
- **Processing Time**: < 2 minutes per reconciliation
- **Accuracy**: 99%+ match detection accuracy
- **Uptime**: 99.9% availability
- **Error Rate**: < 1% failed reconciliations

### 14.2 Business KPIs
- **User Satisfaction**: > 4.5/5 rating
- **Time Savings**: Reduce manual reconciliation from 30 min to 2 min
- **Monthly Volume**: Handle 500+ reconciliations reliably

---

## APPENDIX A: Environment Variables

```bash
# Backend .env
DATABASE_URL=postgresql://user:pass@host:5432/reconciliation
REDIS_URL=redis://host:6379/0
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_STORAGE_CONTAINER=reconciliation-files
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
MIN_PDF_CONFIDENCE=0.75
MAX_FILE_SIZE_MB=50
CELERY_BROKER_URL=${REDIS_URL}
CELERY_RESULT_BACKEND=${REDIS_URL}

# Frontend .env
REACT_APP_API_URL=https://app-reconciliation-api-prod.azurewebsites.net
REACT_APP_WS_URL=wss://app-reconciliation-api-prod.azurewebsites.net/ws
```

---

## APPENDIX B: Key Dependencies

```txt
# Backend requirements.txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
celery==5.3.4
redis==5.0.1
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
alembic==1.12.1
openpyxl==3.1.2
pandas==2.1.3
pydantic==2.5.0
azure-ai-formrecognizer==3.3.2
azure-storage-blob==12.19.0
azure-identity==1.15.0
pdfplumber==0.10.3
python-multipart==0.0.6
structlog==23.2.0
pytest==7.4.3
```

```json
// Frontend package.json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "@tanstack/react-query": "^5.8.0",
    "react-router-dom": "^6.20.0",
    "react-dropzone": "^14.2.3",
    "react-pdf": "^7.5.1",
    "recharts": "^2.10.3",
    "axios": "^1.6.2",
    "tailwindcss": "^3.3.5",
    "@radix-ui/react-*": "latest",
    "lucide-react": "^0.294.0"
  }
}
```

---

## SUMMARY

This comprehensive design provides a production-ready reconciliation system that:

✅ Handles 500 monthly reconciliations efficiently
✅ Uses Azure Document Intelligence for reliable PDF processing
✅ Provides exact cell-level mismatch detection
✅ Flags low-confidence OCR results
✅ Generates downloadable Excel and PDF reports
✅ Scales for future batch processing needs
✅ Monitors performance and errors proactively
✅ Costs ~$333/month with optimization opportunities

The system is built with modern, maintainable technologies and follows Azure best practices for security, scalability, and observability.
