# Bulk Upload Feature - Implementation Progress

**Last Updated:** November 14, 2025
**Status:** Phase 1 - Foundation Complete
**Overall Progress:** 40% (4 of 8 phases)

---

## 🎯 Feature Overview

**Goal:** Allow users to upload a single combined PDF containing multiple 2-page documents, automatically split and reconcile them with matching Excel files.

**Workflow:**
1. User uploads combined PDF → System splits into individual 2-page documents
2. User uploads multiple Excel files → System matches by filename (ID)
3. User selects documents with valid pages (2) and matched Excel → Batch reconcile
4. User views reconciliation results per document

---

## 📋 Implementation Phases

### ✅ **Phase 1: Backend Foundation (COMPLETE)**

**Completed Items:**

1. **Database Schema** (`backend/app/database_schema_bulk.sql`)
   - `bulk_uploads` table: Tracks upload sessions
   - `bulk_documents` table: Individual extracted documents
   - Views and indexes for performance
   - 6-month retention policy support

2. **Azure Blob Storage Service** (`backend/app/blob_storage_service.py`)
   - Upload/download files to Azure Blob
   - Generate temporary SAS URLs
   - List and delete blobs
   - 6-month retention cleanup method

3. **PDF Splitting Processor** (`backend/app/bulk_pdf_processor.py`)
   - Uses Azure DI custom model `Header_extraction`
   - Extracts: ID, Tipo, Lugar, Código CODAE, Mês, Ano, CEP, Diretoria, Prestador
   - Splits combined PDF page-by-page
   - Groups pages by document ID
   - Creates individual 2-page PDFs

4. **Data Models** (`backend/app/bulk_models.py`)
   - Request/Response Pydantic models
   - Database models for SQLAlchemy
   - Comprehensive typing and validation

5. **Dependencies** (`backend/requirements.txt`)
   - Added `azure-storage-blob==12.19.0`
   - Added `PyPDF2==3.0.1`

**Status:** ✅ Ready for API endpoint implementation

---

### 🔄 **Phase 2: Bulk Upload API (IN PROGRESS)**

**Next Steps:**
1. Create API endpoint: `POST /api/v1/bulk/upload-pdf`
   - Accept PDF file
   - Process with BulkPDFProcessor
   - Save to blob storage
   - Store in database
   - Return status

2. Create endpoint: `GET /api/v1/bulk/{upload_id}/status`
   - Return processing status
   - List extracted documents

3. Create endpoint: `GET /api/v1/bulk/{upload_id}/documents`
   - Return table of all documents
   - With page counts, metadata, etc.

**Status:** 🔄 Not started

---

### ⏳ **Phase 3: Excel Upload & Matching (PENDING)**

**Planned:**
1. Endpoint: `POST /api/v1/bulk/{upload_id}/upload-excel`
2. Accept multiple `.xlsm` files
3. Match filenames with document IDs
4. Update `bulk_documents.excel_matched`
5. Return matching statistics

**Status:** ⏳ Waiting for Phase 2

---

### ⏳ **Phase 4: Batch Reconciliation (PENDING)**

**Planned:**
1. Endpoint: `POST /api/v1/bulk/{upload_id}/reconcile`
2. Accept list of document IDs
3. For each ID:
   - Load split PDF from blob
   - Load Excel from blob
   - Call existing `ComprehensiveReconciliationEngine`
   - Store results
4. Return batch status

**Status:** ⏳ Waiting for Phase 3

---

### ⏳ **Phase 5-8: Frontend & Integration (PENDING)**

- Phase 5: PDF upload UI
- Phase 6: Excel upload & matching UI
- Phase 7: Batch selection & reconciliation UI
- Phase 8: Results display & integration testing

---

## 🗂️ File Structure

```
backend/
├── app/
│   ├── database_schema_bulk.sql       ✅ NEW - Database schema
│   ├── blob_storage_service.py        ✅ NEW - Azure Blob Storage
│   ├── bulk_pdf_processor.py          ✅ NEW - PDF splitting logic
│   ├── bulk_models.py                 ✅ NEW - Pydantic models
│   ├── bulk_api.py                    🔄 TODO - API endpoints
│   ├── main.py                        🔄 TODO - Register routes
│   └── ...existing files...
├── requirements.txt                   ✅ UPDATED - New dependencies
└── ...
```

---

## 🔧 Technical Details

### Database Schema

**Table: `bulk_uploads`**
```sql
- id (UUID, PK)
- original_filename
- upload_timestamp
- status (processing/completed/failed/partial)
- total_pages, total_documents
- blob_path (Azure Blob reference)
- retention_until (6 months from upload)
```

**Table: `bulk_documents`**
```sql
- id (UUID, PK)
- bulk_upload_id (FK)
- document_id (EMEI ID, e.g., "92311")
- tipo, lugar, codigo_codae, mes, ano, cep, diretoria, prestador
- page_count (should be 2 for valid docs)
- pdf_blob_path, excel_blob_path
- excel_matched (boolean)
- reconciliation_id (FK to reconciliations table)
- status (extracted/ready/reconciling/completed/failed)
```

### Azure Custom Model

**Model ID:** `Header_extraction`

**Extracted Fields:**
- ID → document_id (EMEI ID)
- Tipo
- Lugar
- CodigoCODAE → codigo_codae
- Mes
- Ano
- CEP
- Diretoria
- Prestador

### Processing Flow

```
1. Upload PDF
   ↓
2. Split into pages (using PyPDF2)
   ↓
3. For each page:
   - Call Azure DI custom model
   - Extract metadata
   ↓
4. Group pages by document_id
   ↓
5. Create 2-page PDFs (combine pages with same ID)
   ↓
6. Upload each PDF to blob storage
   ↓
7. Save metadata to database
```

### Storage Strategy

**Container:** `bulk-uploads`

**Folder Structure:**
```
bulk-uploads/
  2025-01/
    {upload_id}/
      original.pdf          # Original combined PDF
      split/
        92311.pdf          # Individual 2-page PDFs
        95687.pdf
      excel/
        92311.xlsm         # Matched Excel files
        95687.xlsm
```

**Retention:** 6 months (auto-cleanup via `BlobStorageService.delete_old_files()`)

---

## 🔑 Environment Variables

Add to `.env`:

```bash
# Existing
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...

# NEW - Add these
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...;AccountKey=...;EndpointSuffix=core.windows.net
AZURE_STORAGE_CONTAINER_NAME=bulk-uploads
CUSTOM_MODEL_ID=Header_extraction
```

---

## 🧪 Testing Plan

### Unit Tests
- [ ] BlobStorageService.upload_file()
- [ ] BlobStorageService.download_file()
- [ ] BulkPDFProcessor.process_combined_pdf()
- [ ] BulkPDFProcessor._extract_page_metadata()
- [ ] BulkPDFProcessor._group_pages_by_id()

### Integration Tests
- [ ] Upload combined PDF → Verify split PDFs in blob
- [ ] Upload Excel → Verify matching logic
- [ ] Batch reconciliation → Verify results stored
- [ ] End-to-end workflow with sample data

### Performance Tests
- [ ] Process 100-page PDF (50 documents)
- [ ] Upload 50 Excel files
- [ ] Reconcile 50 documents in parallel

---

## 📊 Expected Performance

**PDF Processing:**
- Azure DI: ~2-3 seconds per page
- 100-page PDF: ~5-8 minutes total
- Parallelization: 3-4 pages at a time

**Storage:**
- Upload: ~100ms per PDF
- Download: ~50ms per PDF

**Reconciliation:**
- Per document: ~10-15 seconds (existing engine)
- 50 documents sequential: ~10 minutes
- 50 documents parallel (5 workers): ~2-3 minutes

---

## 🚀 Next Session Tasks

### Phase 2: Create Bulk Upload API

1. **Create `bulk_api.py`:**
   ```python
   @router.post("/api/v1/bulk/upload-pdf")
   async def upload_combined_pdf(file: UploadFile):
       # Process PDF
       # Save to blob
       # Store in DB
       # Return upload_id
   ```

2. **Create background task for processing:**
   - Process PDF asynchronously
   - Update status in real-time
   - Handle errors gracefully

3. **Register routes in `main.py`:**
   ```python
   from .bulk_api import router as bulk_router
   app.include_router(bulk_router)
   ```

4. **Test with Postman/curl:**
   ```bash
   curl -X POST http://localhost:8000/api/v1/bulk/upload-pdf \
     -F "file=@combined_document.pdf"
   ```

### Database Setup

1. **Run schema migration:**
   ```bash
   psql SME_recon < backend/app/database_schema_bulk.sql
   ```

2. **Verify tables created:**
   ```bash
   psql SME_recon -c "\d bulk_uploads"
   psql SME_recon -c "\d bulk_documents"
   ```

---

## 📝 Notes & Considerations

### Known Limitations
1. **No parallel processing yet:** Pages processed sequentially
2. **No resume capability:** If processing fails, must restart
3. **Memory usage:** Entire PDF loaded into memory

### Future Enhancements
1. **Parallel page processing:** Use ThreadPoolExecutor
2. **Chunked processing:** Process in batches for large PDFs
3. **Resume support:** Save progress, allow retry
4. **Webhook notifications:** Alert when processing complete
5. **UI progress bar:** Real-time updates via WebSocket

---

## 🎉 Achievements So Far

✅ Database schema designed and documented
✅ Azure Blob Storage service implemented
✅ PDF splitting logic with custom model integration
✅ Complete data models for API
✅ Dependencies updated
✅ 6-month retention policy supported

**Phase 1 Complete:** Foundation ready for API development!

---

**Ready to proceed with Phase 2!** 🚀
