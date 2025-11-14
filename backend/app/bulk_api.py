"""
Bulk Upload API Endpoints
Handles combined PDF upload, processing, Excel matching, and batch reconciliation
"""

import os
import io
import json
import logging
from typing import List, Optional
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError

from .bulk_models import (
    BulkUploadResponse,
    BulkUploadStatusResponse,
    BulkDocumentResponse,
    ExcelMatchingResponse,
    ReconcileRequest,
    ReconciliationProgressResponse
)
from .bulk_pdf_processor import BulkPDFProcessor
from .blob_storage_service import BlobStorageService
from .reconciliation_engine_comprehensive import ComprehensiveReconciliationEngine
from .excel_parser_custom import CustomExcelParser
from .pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

# ============================================================================
# DATABASE SETUP
# ============================================================================

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://writetodennis@localhost:5432/SME_recon")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Database dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# DATABASE MODELS (SQLAlchemy ORM)
# ============================================================================

class BulkUpload(Base):
    __tablename__ = "bulk_uploads"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    original_filename = Column(String(255), nullable=False)
    upload_timestamp = Column(DateTime, default=datetime.now)
    status = Column(String(20), default="processing")
    total_pages = Column(Integer)
    total_documents = Column(Integer)
    documents_with_2_pages = Column(Integer)
    documents_with_excel = Column(Integer)
    documents_reconciled = Column(Integer)
    blob_container = Column(String(100), default="bulk-uploads")
    blob_path = Column(String(500))
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    error_message = Column(Text)
    retention_until = Column(DateTime)
    user_id = Column(String(100))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class BulkDocument(Base):
    __tablename__ = "bulk_documents"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    bulk_upload_id = Column(PGUUID(as_uuid=True), nullable=False)
    document_id = Column(String(50), nullable=False)
    tipo = Column(String(50))
    lugar = Column(String(255))
    codigo_codae = Column(String(50))
    mes = Column(String(20))
    ano = Column(String(10))
    cep = Column(String(20))
    diretoria = Column(String(255))
    prestador = Column(String(255))
    page_count = Column(Integer, nullable=False)
    page_numbers = Column(Text)  # JSON array as string
    pdf_blob_path = Column(String(500))
    excel_filename = Column(String(255))
    excel_blob_path = Column(String(500))
    excel_matched = Column(Boolean, default=False)
    excel_uploaded_at = Column(DateTime)
    reconciliation_id = Column(PGUUID(as_uuid=True))
    reconciliation_status = Column(String(20))
    reconciliation_match_percentage = Column(Float)
    reconciliation_total_mismatches = Column(Integer)
    status = Column(String(20), default="extracted")
    error_message = Column(Text)
    extraction_confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# ============================================================================
# ROUTER
# ============================================================================

router = APIRouter(prefix="/api/v1/bulk", tags=["Bulk Upload"])


# ============================================================================
# SERVICES INITIALIZATION
# ============================================================================

def get_blob_service():
    """Get Azure Blob Storage service"""
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    container_name = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "bulk-uploads")
    return BlobStorageService(connection_string, container_name)


def get_pdf_processor():
    """Get Bulk PDF Processor"""
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")
    model_id = os.getenv("CUSTOM_MODEL_ID", "Header_extraction")
    return BulkPDFProcessor(endpoint, key, model_id)


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def process_bulk_pdf_background(
    upload_id: UUID,
    pdf_content: bytes,
    original_filename: str
):
    """
    Background task to process combined PDF
    """
    db = SessionLocal()
    blob_service = get_blob_service()
    pdf_processor = get_pdf_processor()

    try:
        # Update status
        upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
        upload.status = "processing"
        upload.processing_started_at = datetime.now()
        db.commit()

        logger.info(f"Starting background processing for upload {upload_id}")

        # Step 1: Upload original PDF to blob storage
        blob_folder = f"{datetime.now().strftime('%Y-%m')}/{upload_id}"
        original_blob_path = blob_service.upload_file(
            file_data=io.BytesIO(pdf_content),
            blob_name=f"{blob_folder}/original.pdf",
            content_type="application/pdf",
            metadata={"upload_id": str(upload_id), "filename": original_filename}
        )
        logger.info(f"Uploaded original PDF to: {original_blob_path}")

        # Update blob path
        upload.blob_path = original_blob_path
        db.commit()

        # Step 2: Process PDF with custom model
        logger.info("Processing PDF with custom model...")
        result = pdf_processor.process_combined_pdf(io.BytesIO(pdf_content))

        logger.info(
            f"PDF processing complete: {result.total_documents} documents extracted "
            f"from {result.total_pages} pages in {result.processing_time_seconds:.2f}s"
        )

        # Step 3: Save each extracted document
        documents_with_2_pages = 0

        for doc in result.documents:
            # Upload individual PDF to blob
            doc_blob_path = blob_service.upload_file(
                file_data=io.BytesIO(doc.pdf_content),
                blob_name=f"{blob_folder}/split/{doc.document_id}.pdf",
                content_type="application/pdf",
                metadata={
                    "upload_id": str(upload_id),
                    "document_id": doc.document_id,
                    "page_count": str(doc.page_count)
                }
            )

            # Save to database
            db_doc = BulkDocument(
                bulk_upload_id=upload_id,
                document_id=doc.document_id,
                tipo=doc.tipo,
                lugar=doc.lugar,
                codigo_codae=doc.codigo_codae,
                mes=doc.mes,
                ano=doc.ano,
                cep=doc.cep,
                diretoria=doc.diretoria,
                prestador=doc.prestador,
                page_count=doc.page_count,
                page_numbers=json.dumps(doc.page_numbers),
                pdf_blob_path=doc_blob_path,
                extraction_confidence=doc.confidence,
                status="extracted"
            )
            db.add(db_doc)

            if doc.page_count == 2:
                documents_with_2_pages += 1

            logger.info(f"Saved document {doc.document_id} ({doc.page_count} pages)")

        db.commit()

        # Step 4: Update upload statistics
        upload.total_pages = result.total_pages
        upload.total_documents = result.total_documents
        upload.documents_with_2_pages = documents_with_2_pages
        upload.status = "completed"
        upload.processing_completed_at = datetime.now()
        upload.retention_until = datetime.now() + timedelta(days=180)  # 6 months

        if result.processing_errors:
            upload.error_message = "; ".join(result.processing_errors[:5])  # Store first 5 errors

        db.commit()

        logger.info(f"✅ Upload {upload_id} processing complete!")

    except Exception as e:
        logger.error(f"❌ Error processing upload {upload_id}: {e}", exc_info=True)

        # Update status to failed
        upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
        if upload:
            upload.status = "failed"
            upload.error_message = str(e)
            upload.processing_completed_at = datetime.now()
            db.commit()

    finally:
        db.close()


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/upload-pdf", response_model=BulkUploadResponse)
async def upload_combined_pdf(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a combined PDF containing multiple documents

    Process:
    1. Accept PDF file
    2. Create upload record
    3. Process in background (split, extract metadata, save to blob)
    4. Return upload ID for status checking
    """
    # Validate file
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Check file size (50MB limit)
    max_size = int(os.getenv("MAX_FILE_SIZE_MB", "50")) * 1024 * 1024
    content = await file.read()

    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {max_size / 1024 / 1024}MB"
        )

    try:
        # Create upload record
        upload = BulkUpload(
            original_filename=file.filename,
            status="processing",
            processing_started_at=datetime.now()
        )
        db.add(upload)
        db.commit()
        db.refresh(upload)

        logger.info(f"Created upload record: {upload.id}")

        # Process in background
        background_tasks.add_task(
            process_bulk_pdf_background,
            upload.id,
            content,
            file.filename
        )

        # Return response
        return BulkUploadResponse(
            id=upload.id,
            original_filename=upload.original_filename,
            upload_timestamp=upload.upload_timestamp,
            status=upload.status,
            processing_started_at=upload.processing_started_at,
            documents=[]
        )

    except SQLAlchemyError as e:
        logger.error(f"Database error: {e}")
        raise HTTPException(status_code=500, detail="Database error")


@router.get("/{upload_id}/status", response_model=BulkUploadStatusResponse)
async def get_upload_status(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get processing status of a bulk upload

    Returns current status, progress, and any errors
    """
    upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()

    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Calculate progress percentage
    progress = 0
    if upload.status == "processing":
        progress = 50  # Assume 50% while processing
    elif upload.status == "completed":
        progress = 100
    elif upload.status == "failed":
        progress = 0

    current_step = None
    if upload.status == "processing":
        current_step = "Extracting documents from PDF..."
    elif upload.status == "completed":
        current_step = "Complete"

    return BulkUploadStatusResponse(
        id=upload.id,
        status=upload.status,
        total_pages=upload.total_pages,
        total_documents=upload.total_documents,
        progress_percentage=progress,
        current_step=current_step,
        error_message=upload.error_message
    )


@router.get("/{upload_id}/documents", response_model=List[BulkDocumentResponse])
async def get_uploaded_documents(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get list of all documents extracted from the upload

    Returns table of documents with metadata, page counts, Excel matching status
    """
    # Verify upload exists
    upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Get all documents
    documents = db.query(BulkDocument).filter(
        BulkDocument.bulk_upload_id == upload_id
    ).order_by(BulkDocument.document_id).all()

    # Convert to response models
    return [
        BulkDocumentResponse(
            id=doc.id,
            bulk_upload_id=doc.bulk_upload_id,
            document_id=doc.document_id,
            tipo=doc.tipo,
            lugar=doc.lugar,
            codigo_codae=doc.codigo_codae,
            mes=doc.mes,
            ano=doc.ano,
            cep=doc.cep,
            diretoria=doc.diretoria,
            prestador=doc.prestador,
            page_count=doc.page_count,
            page_numbers=json.loads(doc.page_numbers) if doc.page_numbers else None,
            excel_filename=doc.excel_filename,
            excel_matched=doc.excel_matched,
            reconciliation_id=doc.reconciliation_id,
            reconciliation_status=doc.reconciliation_status,
            reconciliation_match_percentage=doc.reconciliation_match_percentage,
            reconciliation_total_mismatches=doc.reconciliation_total_mismatches,
            status=doc.status,
            error_message=doc.error_message,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]


@router.get("/{upload_id}", response_model=BulkUploadResponse)
async def get_upload_details(
    upload_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get complete upload details including all documents

    Combines upload metadata with document list
    """
    upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Get documents
    documents = db.query(BulkDocument).filter(
        BulkDocument.bulk_upload_id == upload_id
    ).all()

    # Convert documents to response models
    doc_responses = [
        BulkDocumentResponse(
            id=doc.id,
            bulk_upload_id=doc.bulk_upload_id,
            document_id=doc.document_id,
            tipo=doc.tipo,
            lugar=doc.lugar,
            codigo_codae=doc.codigo_codae,
            mes=doc.mes,
            ano=doc.ano,
            cep=doc.cep,
            diretoria=doc.diretoria,
            prestador=doc.prestador,
            page_count=doc.page_count,
            page_numbers=json.loads(doc.page_numbers) if doc.page_numbers else None,
            excel_filename=doc.excel_filename,
            excel_matched=doc.excel_matched,
            reconciliation_id=doc.reconciliation_id,
            reconciliation_status=doc.reconciliation_status,
            reconciliation_match_percentage=doc.reconciliation_match_percentage,
            reconciliation_total_mismatches=doc.reconciliation_total_mismatches,
            status=doc.status,
            error_message=doc.error_message,
            created_at=doc.created_at,
            updated_at=doc.updated_at
        )
        for doc in documents
    ]

    return BulkUploadResponse(
        id=upload.id,
        original_filename=upload.original_filename,
        upload_timestamp=upload.upload_timestamp,
        status=upload.status,
        total_pages=upload.total_pages,
        total_documents=upload.total_documents,
        documents_with_2_pages=upload.documents_with_2_pages,
        documents_with_excel=upload.documents_with_excel,
        documents_reconciled=upload.documents_reconciled,
        processing_started_at=upload.processing_started_at,
        processing_completed_at=upload.processing_completed_at,
        error_message=upload.error_message,
        documents=doc_responses
    )


@router.post("/{upload_id}/upload-excel", response_model=ExcelMatchingResponse)
async def upload_excel_files(
    upload_id: UUID,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload multiple Excel files and match with documents

    Process:
    1. Accept multiple .xlsm files
    2. Match filename (without extension) with document_id
    3. Upload matched files to blob storage
    4. Update bulk_documents table
    5. Return matching statistics
    """
    # Verify upload exists
    upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Get all documents for this upload
    documents = db.query(BulkDocument).filter(
        BulkDocument.bulk_upload_id == upload_id
    ).all()

    if not documents:
        raise HTTPException(status_code=400, detail="No documents found for this upload")

    # Create document ID lookup
    doc_map = {doc.document_id: doc for doc in documents}

    blob_service = get_blob_service()
    blob_folder = f"{datetime.now().strftime('%Y-%m')}/{upload_id}/excel"

    matched_count = 0
    matched_ids = []

    # Process each Excel file
    for file in files:
        # Validate file extension
        if not file.filename.endswith(('.xlsx', '.xlsm', '.xls')):
            logger.warning(f"Skipping non-Excel file: {file.filename}")
            continue

        # Extract document ID from filename (remove extension)
        file_base = file.filename.rsplit('.', 1)[0]

        # Check if this matches a document ID
        if file_base in doc_map:
            doc = doc_map[file_base]

            try:
                # Read file content
                content = await file.read()

                # Upload to blob storage
                excel_blob_path = blob_service.upload_file(
                    file_data=io.BytesIO(content),
                    blob_name=f"{blob_folder}/{file.filename}",
                    content_type="application/vnd.ms-excel",
                    metadata={
                        "upload_id": str(upload_id),
                        "document_id": file_base
                    }
                )

                # Update document record
                doc.excel_filename = file.filename
                doc.excel_blob_path = excel_blob_path
                doc.excel_matched = True
                doc.excel_uploaded_at = datetime.now()
                doc.status = "ready"  # Ready for reconciliation

                matched_count += 1
                matched_ids.append(file_base)

                logger.info(f"Matched Excel file {file.filename} with document {file_base}")

            except Exception as e:
                logger.error(f"Error uploading Excel file {file.filename}: {e}")

    # Commit all changes
    db.commit()

    # Update upload statistics
    upload.documents_with_excel = matched_count
    db.commit()

    # Get list of missing document IDs
    all_doc_ids = set(doc_map.keys())
    missing_ids = list(all_doc_ids - set(matched_ids))

    return ExcelMatchingResponse(
        bulk_upload_id=upload_id,
        total_excel_files=len(files),
        matched_count=matched_count,
        missing_count=len(missing_ids),
        matched_documents=matched_ids,
        missing_documents=missing_ids
    )
