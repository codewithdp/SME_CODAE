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
from .main import ReconciliationDB

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
    progress_percentage = Column(Integer, default=0)
    current_step = Column(String(255))
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
        upload.progress_percentage = 5
        upload.current_step = "Iniciando processamento..."
        db.commit()

        logger.info(f"Starting background processing for upload {upload_id}")

        # Step 1: Upload original PDF to blob storage
        upload.progress_percentage = 10
        upload.current_step = "Fazendo upload do PDF..."
        db.commit()

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
        upload.progress_percentage = 20
        upload.current_step = "Analisando documento com Azure AI..."
        db.commit()

        # Step 2: Process PDF with custom model
        logger.info("Processing PDF with custom model...")
        result = pdf_processor.process_combined_pdf(io.BytesIO(pdf_content))

        logger.info(
            f"PDF processing complete: {result.total_documents} documents extracted "
            f"from {result.total_pages} pages in {result.processing_time_seconds:.2f}s"
        )

        # Step 3: Save each extracted document
        upload.progress_percentage = 60
        upload.current_step = f"Salvando {result.total_documents} documentos extraídos..."
        db.commit()

        documents_with_2_pages = 0
        saved_count = 0

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

            saved_count += 1
            # Update progress for each document saved (60-90%)
            doc_progress = 60 + int((saved_count / result.total_documents) * 30)
            upload.progress_percentage = doc_progress
            upload.current_step = f"Documento {saved_count}/{result.total_documents} salvo: {doc.document_id}"
            db.commit()

            logger.info(f"Saved document {doc.document_id} ({doc.page_count} pages)")

        # Step 4: Update upload statistics
        upload.progress_percentage = 95
        upload.current_step = "Finalizando processamento..."
        db.commit()

        upload.total_pages = result.total_pages
        upload.total_documents = result.total_documents
        upload.documents_with_2_pages = documents_with_2_pages
        upload.status = "completed"
        upload.progress_percentage = 100
        upload.current_step = "Concluído!"
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

    # Get progress from database or calculate based on status
    progress = upload.progress_percentage or 0
    if upload.status == "completed":
        progress = 100
    elif upload.status == "failed":
        progress = 0
    elif upload.status == "processing" and progress == 0:
        progress = 10  # Show some progress if none recorded yet

    current_step = upload.current_step
    if not current_step:
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


@router.get("/{upload_id}/reconciliation/{reconciliation_id}")
async def get_reconciliation_details(
    upload_id: UUID,
    reconciliation_id: str,
    db: Session = Depends(get_db)
):
    """
    Get detailed reconciliation results for a specific document

    Returns the full reconciliation report including all mismatches,
    match percentages, and comparison details
    """
    # Verify upload exists
    upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail="Upload not found")

    # Get reconciliation record
    reconciliation = db.query(ReconciliationDB).filter(
        ReconciliationDB.id == reconciliation_id
    ).first()

    if not reconciliation:
        raise HTTPException(status_code=404, detail="Reconciliation not found")

    # Return the full reconciliation data
    return JSONResponse(content={
        "id": str(reconciliation.id) if reconciliation.id else None,
        "document_id": reconciliation.emei_id,
        "excel_filename": reconciliation.excel_filename,
        "pdf_filename": reconciliation.pdf_filename,
        "status": reconciliation.status,
        "overall_match_percentage": reconciliation.overall_match_percentage,
        "total_mismatches": reconciliation.total_mismatches,
        "id_match": reconciliation.id_match,
        "pdf_confidence_ok": reconciliation.pdf_confidence_ok,
        "result_data": reconciliation.result_data,
        "created_at": reconciliation.created_at.isoformat() if reconciliation.created_at else None,
        "completed_at": reconciliation.completed_at.isoformat() if reconciliation.completed_at else None
    })


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

                # Clear any previous reconciliation data
                doc.reconciliation_status = None
                doc.reconciliation_id = None
                doc.reconciliation_match_percentage = None
                doc.reconciliation_total_mismatches = None

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


# ============================================================================
# BATCH RECONCILIATION ENDPOINT
# ============================================================================

@router.post("/{upload_id}/reconcile")
async def start_batch_reconciliation(
    upload_id: UUID,
    request: ReconcileRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Start batch reconciliation for selected documents
    Processes PDF + Excel for each document in background
    """
    try:
        # Verify upload exists
        upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        # Get documents to reconcile (either specified or all "ready" documents)
        if request.document_ids:
            documents = db.query(BulkDocument).filter(
                BulkDocument.bulk_upload_id == upload_id,
                BulkDocument.document_id.in_(request.document_ids),
                BulkDocument.status == "ready"
            ).all()
        else:
            # If no document_ids specified, reconcile all ready documents
            documents = db.query(BulkDocument).filter(
                BulkDocument.bulk_upload_id == upload_id,
                BulkDocument.status == "ready"
            ).all()

        if not documents:
            raise HTTPException(
                status_code=400,
                detail="No ready documents found for reconciliation"
            )

        # Update document status to "reconciling"
        for doc in documents:
            doc.status = "reconciling"
            doc.reconciliation_status = "processing"
        db.commit()

        # Start background task
        background_tasks.add_task(
            process_batch_reconciliation,
            str(upload_id),
            [doc.document_id for doc in documents]
        )

        return {
            "message": "Batch reconciliation started",
            "upload_id": str(upload_id),
            "document_count": len(documents),
            "document_ids": [doc.document_id for doc in documents]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting batch reconciliation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def process_batch_reconciliation(upload_id: str, document_ids: List[str]):
    """
    Background task to reconcile multiple documents
    Downloads PDFs and Excel files, runs reconciliation, saves results
    """
    db = SessionLocal()

    try:
        logger.info(f"Starting batch reconciliation for upload {upload_id}, {len(document_ids)} documents")

        # Initialize blob storage and services
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        blob_service = BlobStorageService(connection_string, 'bulk-uploads')

        # Initialize Complete Positional Reconciliation Engine (Sections 1, 2, 3)
        azure_di_endpoint = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT')
        azure_di_key = os.getenv('AZURE_DOCUMENT_INTELLIGENCE_KEY')

        from .reconciliation_engine_complete import CompletePositionalReconciliationEngine
        from .main import transform_custom_model_results_to_reconciliation_result

        recon_engine = CompletePositionalReconciliationEngine()
        excel_parser = CustomExcelParser()

        total = len(document_ids)
        for idx, doc_id in enumerate(document_ids):
            try:
                logger.info(f"Processing document {idx + 1}/{total}: {doc_id}")

                # Get document from database
                doc = db.query(BulkDocument).filter(
                    BulkDocument.bulk_upload_id == upload_id,
                    BulkDocument.document_id == doc_id
                ).first()

                if not doc or not doc.pdf_blob_path or not doc.excel_blob_path:
                    logger.error(f"Document {doc_id} missing PDF or Excel file")
                    doc.status = "failed"
                    doc.reconciliation_status = "failed"
                    doc.error_message = "Missing PDF or Excel file"
                    db.commit()
                    continue

                # Download PDF and Excel from blob storage
                pdf_content = blob_service.download_file(doc.pdf_blob_path)
                excel_content = blob_service.download_file(doc.excel_blob_path)

                # Save temporarily
                temp_dir = f"/tmp/bulk_recon_{upload_id}"
                os.makedirs(temp_dir, exist_ok=True)

                pdf_path = os.path.join(temp_dir, f"{doc_id}.pdf")
                excel_path = os.path.join(temp_dir, f"{doc_id}.xlsm")

                with open(pdf_path, 'wb') as f:
                    f.write(pdf_content)
                with open(excel_path, 'wb') as f:
                    f.write(excel_content)

                # Run custom model reconciliation
                section_configs = [
                    {"section_name": "Section2", "excel_start_row": 28},
                    {"section_name": "Section3", "excel_start_row": 77}
                ]

                custom_results = recon_engine.reconcile_all_sections(pdf_path, excel_path, section_configs)

                # Transform custom model results to ReconciliationResult format
                result = transform_custom_model_results_to_reconciliation_result(
                    custom_results,
                    doc_id,
                    doc.excel_filename,
                    f"{doc_id}.pdf"
                )

                # Create reconciliation record in main reconciliations table
                reconciliation = ReconciliationDB(
                    id=str(uuid4()),
                    excel_filename=doc.excel_filename,
                    pdf_filename=f"{doc_id}.pdf",
                    emei_id=doc_id,
                    id_match=result.id_match,
                    pdf_confidence_ok=result.pdf_confidence_ok,
                    total_mismatches=result.total_mismatches,
                    overall_match_percentage=result.overall_match_percentage,
                    status="completed",
                    result_data=json.loads(result.model_dump_json())
                )
                db.add(reconciliation)
                db.flush()

                # Update bulk document with reconciliation results
                doc.reconciliation_id = reconciliation.id
                doc.reconciliation_status = "completed"
                doc.reconciliation_match_percentage = result.overall_match_percentage
                doc.reconciliation_total_mismatches = result.total_mismatches
                doc.status = "completed"

                # Clean up temp files
                os.remove(pdf_path)
                os.remove(excel_path)

                db.commit()
                logger.info(f"✅ Completed reconciliation for {doc_id}: {result.overall_match_percentage:.2f}% match")

            except Exception as e:
                logger.error(f"❌ Error processing document {doc_id}: {e}")
                doc.status = "failed"
                doc.reconciliation_status = "failed"
                doc.error_message = str(e)
                db.commit()

        # Clean up temp directory
        try:
            os.rmdir(temp_dir)
        except:
            pass

        logger.info(f"✅ Batch reconciliation complete for upload {upload_id}")

    except Exception as e:
        logger.error(f"❌ Batch reconciliation failed for upload {upload_id}: {e}")
    finally:
        db.close()


@router.post("/{upload_id}/reset-reconciliation")
async def reset_reconciliation_status(
    upload_id: UUID,
    document_ids: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    Reset reconciliation status for documents to allow re-running reconciliation
    without re-uploading files.

    If document_ids is provided, only reset those documents.
    Otherwise, reset all documents in the upload.
    """
    try:
        # Verify upload exists
        upload = db.query(BulkUpload).filter(BulkUpload.id == upload_id).first()
        if not upload:
            raise HTTPException(status_code=404, detail="Upload not found")

        # Get documents to reset
        if document_ids:
            documents = db.query(BulkDocument).filter(
                BulkDocument.bulk_upload_id == upload_id,
                BulkDocument.document_id.in_(document_ids)
            ).all()
        else:
            # Reset all documents
            documents = db.query(BulkDocument).filter(
                BulkDocument.bulk_upload_id == upload_id
            ).all()

        if not documents:
            raise HTTPException(
                status_code=404,
                detail="No documents found to reset"
            )

        # Reset each document back to "ready" status
        reset_count = 0
        for doc in documents:
            # Only reset if it has both PDF and Excel (was ready to reconcile before)
            if doc.pdf_blob_path and doc.excel_blob_path:
                doc.status = "ready"
                doc.reconciliation_status = None
                doc.reconciliation_id = None
                doc.reconciliation_match_percentage = None
                doc.reconciliation_total_mismatches = None
                reset_count += 1

        db.commit()

        return {
            "message": f"Reset {reset_count} documents to ready status",
            "upload_id": str(upload_id),
            "reset_count": reset_count
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting reconciliation status: {e}")
        raise HTTPException(status_code=500, detail=str(e))
