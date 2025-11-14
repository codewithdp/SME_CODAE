# Quick Reference Guide - Excel-PDF Reconciliation System

## 🎯 System Overview

**Purpose**: Automatically reconcile Excel files with their PDF counterparts, identifying mismatches across student enrollment, attendance frequency, and daily meal attendance data.

**Key Stats**:
- Monthly Volume: ~500 reconciliations
- Processing Time: < 2 minutes per reconciliation
- Accuracy: 99%+ match detection
- Cost: ~$334/month on Azure

---

## 🏗️ Architecture Quick View

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (React + TypeScript)                          │
│  - Upload Interface                                     │
│  - Real-time Progress Monitoring                        │
│  - Results Dashboard                                    │
└───────────────────┬─────────────────────────────────────┘
                    │ REST API / WebSocket
┌───────────────────▼─────────────────────────────────────┐
│  BACKEND (FastAPI + Python 3.11)                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  API Layer                                      │   │
│  │  - File Upload                                  │   │
│  │  - Status Tracking                              │   │
│  │  - Report Generation                            │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Processing Layer (Celery Workers)              │   │
│  │  ┌──────────────┐  ┌──────────────┐            │   │
│  │  │ Excel Parser │  │ PDF Processor│            │   │
│  │  │  (openpyxl)  │  │  (Azure DI)  │            │   │
│  │  └──────────────┘  └──────────────┘            │   │
│  │           │                │                    │   │
│  │           └────────┬───────┘                    │   │
│  │                    │                            │   │
│  │         ┌──────────▼──────────┐                │   │
│  │         │ Reconciliation      │                │   │
│  │         │ Engine              │                │   │
│  │         │ - Section 1: Enroll │                │   │
│  │         │ - Section 2: Freq   │                │   │
│  │         │ - Section 3: Daily  │                │   │
│  │         └─────────────────────┘                │   │
│  └─────────────────────────────────────────────────┘   │
└───────────────────┬─────────────────────────────────────┘
                    │
┌───────────────────▼─────────────────────────────────────┐
│  DATA LAYER                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ PostgreSQL   │  │ Azure Blob   │  │ Redis        │  │
│  │ - Metadata   │  │ - Files      │  │ - Queue      │  │
│  │ - Results    │  │ - Reports    │  │ - Cache      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Three-Section Comparison

### Section 1: Student Enrollment Numbers
- **Location**: Page 1 of PDF, rows 8-14 of Excel
- **Data**: Number of students by period (Integral, Matutino, Intermediário, Vespertino)
- **Columns**: Enrolled | Special Diet A | Special Diet B
- **Comparison**: Exact match required for each cell

### Section 2: Attendance Frequency
- **Location**: Page 2 of PDF, rows 20-50 of Excel
- **Data**: Daily frequency by special diet group
- **Columns**: Day | Frequency A | Lunch A | Frequency B | Lunch B | Emergency
- **Comparison**: Day-by-day matching

### Section 3: Daily Attendance Grid
- **Location**: Spans both pages of PDF, rows 60-90 of Excel
- **Data**: Daily meal attendance by period
- **Columns**: Day | 1º Período (Breakfast, Lunch) | 2º Período | Intermediário | Integral | 3º Período
- **Rows**: 30-31 days
- **Comparison**: ~300-400 cells per document

---

## 🚀 Quick Start Commands

### Local Development

```bash
# 1. Start Infrastructure
docker run -d --name postgres -e POSTGRES_PASSWORD=pass -p 5432:5432 postgres:15
docker run -d --name redis -p 6379:6379 redis:7-alpine

# 2. Start Backend
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main_api:app --reload &
celery -A app.main_api.celery_app worker --loglevel=info &

# 3. Start Frontend
cd frontend
npm install
npm start

# Access:
# - Frontend: http://localhost:3000
# - API Docs: http://localhost:8000/docs
# - Celery Monitor: http://localhost:5555
```

### Using Docker Compose

```bash
# Start everything
docker-compose up -d

# View logs
docker-compose logs -f

# Stop everything
docker-compose down
```

---

## 🔧 Configuration Quick Reference

### Environment Variables (Backend)

```bash
# Azure Services
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_DOCUMENT_INTELLIGENCE_KEY=your-key-here
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...

# Database
DATABASE_URL=postgresql://user:pass@host:5432/reconciliation

# Processing
MIN_PDF_CONFIDENCE=0.75          # Minimum OCR confidence (0-1)
MAX_FILE_SIZE_MB=50              # Maximum file size

# Queue
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Environment Variables (Frontend)

```bash
REACT_APP_API_URL=http://localhost:8000
REACT_APP_WS_URL=ws://localhost:8000/ws
```

---

## 📊 File Structure Expectations

### Excel File (EMEI Sheet)

```
Row 1-6:    Header (EMEI code, school info, address)
Row 8-14:   Section 1 - Student Enrollment
            ┌─────────────┬──────────┬──────────────┬──────────────┐
            │ Period      │ Enrolled │ Special A    │ Special B    │
            ├─────────────┼──────────┼──────────────┼──────────────┤
            │ INTEGRAL    │ 225      │ 12           │ 0            │
            │ MATUTINO    │ 234      │ 38           │ 0            │
            └─────────────┴──────────┴──────────────┴──────────────┘

Row 20-50:  Section 2 - Frequency Data
            ┌─────┬───────────┬─────────┬───────────┬─────────┬───────────┐
            │ Day │ Freq A    │ Lunch A │ Freq B    │ Lunch B │ Emergency │
            ├─────┼───────────┼─────────┼───────────┼─────────┼───────────┤
            │ 1   │ 156       │ 145     │ 156       │ 21      │ 0         │
            │ 4   │ 225       │ 214     │ 225       │ 25      │ 30        │
            └─────┴───────────┴─────────┴───────────┴─────────┴───────────┘

Row 60-90:  Section 3 - Daily Attendance Grid
            ┌─────┬──────────┬────────┬──────────┬────────┬─────┐
            │ Day │ 1º P BF  │ 1º P L │ 2º P BF  │ 2º P L │ ... │
            ├─────┼──────────┼────────┼──────────┼────────┼─────┤
            │ 1   │ 156      │ 145    │ 156      │ 0      │ ... │
            │ 4   │ 225      │ 214    │ 225      │ 25     │ ... │
            └─────┴──────────┴────────┴──────────┴────────┴─────┘
```

### PDF File (2 Pages)

```
Page 1:
- Header with EMEI code
- Section 1 table
- Section 3 table (first ~15 days)

Page 2:
- Section 2 table (frequency data)
- Section 3 table (remaining days)
```

---

## 🔍 Troubleshooting Quick Fixes

### Issue: Excel Won't Parse

```bash
# Check file format
file your-file.xlsm

# If corrupt, try opening and re-saving in Excel/LibreOffice
libreoffice --headless --convert-to xlsx your-file.xlsm
```

### Issue: PDF Confidence Low

```python
# Adjust threshold in backend
MIN_PDF_CONFIDENCE=0.65  # Lower threshold

# Or re-scan PDF at higher quality (300+ DPI)
```

### Issue: Celery Tasks Not Running

```bash
# Check Redis connection
redis-cli ping

# Check Celery workers
celery -A app.main_api.celery_app inspect active

# Restart worker
celery -A app.main_api.celery_app worker --loglevel=info
```

### Issue: Database Connection Failed

```bash
# Test connection
psql postgresql://user:pass@host:5432/reconciliation

# Check if database exists
psql -l
```

---

## 📈 Monitoring Checklist

### Health Checks

```bash
# Backend API
curl http://localhost:8000/health

# Database
psql -c "SELECT 1"

# Redis
redis-cli ping

# Azure DI (check quota)
# Visit Azure Portal > Document Intelligence > Metrics
```

### Key Metrics to Watch

1. **Processing Time**: Should be < 2 minutes
2. **Success Rate**: Should be > 99%
3. **Queue Length**: Should be near 0
4. **PDF Confidence**: Should be > 0.75
5. **Database Connections**: Should be < 80% of max

---

## 🎓 Common Use Cases

### Case 1: Single File Reconciliation

```bash
# Via Web UI
1. Go to http://localhost:3000
2. Drag Excel file to left zone
3. Drag PDF file to right zone
4. Click "Start Reconciliation"
5. Wait ~2 minutes
6. View results and download report
```

### Case 2: API Integration

```python
import requests

# Upload files
files = {
    'excel_file': open('019382.xlsm', 'rb'),
    'pdf_file': open('EMEI_test1.pdf', 'rb')
}
response = requests.post('http://localhost:8000/api/v1/reconciliation/upload', files=files)
reconciliation_id = response.json()['reconciliation_id']

# Check status
status = requests.get(f'http://localhost:8000/api/v1/reconciliation/{reconciliation_id}/status')
print(status.json())

# Download report when complete
report = requests.get(f'http://localhost:8000/api/v1/reconciliation/{reconciliation_id}/report?format=excel')
with open('report.xlsx', 'wb') as f:
    f.write(report.content)
```

### Case 3: Batch Processing (Future)

```bash
# Upload multiple file pairs
for excel in *.xlsm; do
    pdf="${excel%.xlsm}.pdf"
    if [ -f "$pdf" ]; then
        curl -X POST http://localhost:8000/api/v1/reconciliation/upload \
            -F "excel_file=@$excel" \
            -F "pdf_file=@$pdf"
    fi
done
```

---

## 📚 Additional Resources

### Documentation
- [Full System Design](./reconciliation_system_design.md)
- [API Documentation](http://localhost:8000/docs)
- [Azure DI Docs](https://learn.microsoft.com/azure/ai-services/document-intelligence/)

### Code Examples
- [Excel Parser](./excel_parser.py)
- [PDF Processor](./pdf_processor.py)
- [Reconciliation Engine](./reconciliation_engine.py)
- [FastAPI App](./main_api.py)
- [React Component](./ReconciliationUpload.tsx)

### Support
- Email: support@yourcompany.com
- Slack: #reconciliation-support
- GitHub Issues: https://github.com/yourorg/reconciliation/issues

---

## 🎯 Next Steps

### Phase 1: MVP (Current)
- [x] Excel parsing
- [x] PDF processing with Azure DI
- [x] Three-section comparison
- [x] Web UI for upload
- [x] Results dashboard
- [ ] Report generation (Excel/PDF)
- [ ] Deployment to Azure

### Phase 2: Enhancements
- [ ] Batch processing
- [ ] Advanced analytics dashboard
- [ ] Email notifications
- [ ] User authentication
- [ ] Role-based access control

### Phase 3: AI Features
- [ ] Azure OpenAI for smart field mapping
- [ ] Anomaly detection
- [ ] Predictive insights
- [ ] Natural language queries

---

## 💡 Pro Tips

1. **PDF Quality Matters**: Scan PDFs at 300+ DPI for best OCR results
2. **Filename Convention**: Include EMEI code in filenames for auto-validation
3. **Regular Backups**: Set up automated daily backups of PostgreSQL
4. **Monitor Costs**: Set up Azure cost alerts at $300/month threshold
5. **Test with Real Data**: Always test with actual production files before go-live
6. **Cache Common Results**: Use Redis to cache frequently accessed reconciliations
7. **Scale Horizontally**: Add more Celery workers during peak times
8. **Log Everything**: Structured logging helps debug PDF parsing issues

---

**Created**: November 2025  
**Last Updated**: November 2025  
**Version**: 1.0.0
