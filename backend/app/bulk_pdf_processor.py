"""
Bulk PDF Processor
Splits combined PDF into individual documents using Azure DI custom model
"""

import os
import io
import logging
from typing import List, Dict, Tuple, Optional, BinaryIO
from collections import defaultdict
from datetime import datetime

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from PyPDF2 import PdfReader, PdfWriter
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ============================================================================
# DATA MODELS
# ============================================================================

class ExtractedDocument(BaseModel):
    """Represents a single document extracted from the combined PDF"""
    document_id: str  # EMEI ID
    tipo: Optional[str] = None
    lugar: Optional[str] = None
    codigo_codae: Optional[str] = None
    mes: Optional[str] = None
    ano: Optional[str] = None
    cep: Optional[str] = None
    diretoria: Optional[str] = None
    prestador: Optional[str] = None
    page_numbers: List[int]  # Original page numbers from combined PDF
    page_count: int
    confidence: float  # Average confidence from Azure DI
    pdf_content: bytes  # The actual PDF bytes for this document


class BulkProcessingResult(BaseModel):
    """Result of processing a combined PDF"""
    total_pages: int
    total_documents: int
    documents: List[ExtractedDocument]
    processing_errors: List[str] = []
    processing_time_seconds: float


# ============================================================================
# BULK PDF PROCESSOR
# ============================================================================

class BulkPDFProcessor:
    """
    Processes combined PDFs using Azure Document Intelligence custom model
    Splits pages and groups them by document ID
    """

    def __init__(
        self,
        azure_endpoint: str,
        azure_key: str,
        custom_model_id: str = "Header_extraction"
    ):
        """
        Initialize processor

        Args:
            azure_endpoint: Azure Document Intelligence endpoint
            azure_key: Azure Document Intelligence key
            custom_model_id: Custom model name (default: "Header_extraction")
        """
        self.endpoint = azure_endpoint
        self.credential = AzureKeyCredential(azure_key)
        self.client = DocumentIntelligenceClient(self.endpoint, self.credential)
        self.custom_model_id = custom_model_id

        logger.info(f"Initialized BulkPDFProcessor with model: {custom_model_id}")

    def process_combined_pdf(self, pdf_file: BinaryIO) -> BulkProcessingResult:
        """
        Main processing method

        Args:
            pdf_file: Combined PDF file (binary stream)

        Returns:
            BulkProcessingResult with all extracted documents
        """
        start_time = datetime.now()
        processing_errors = []

        try:
            # Read the PDF
            pdf_content = pdf_file.read()
            pdf_reader = PdfReader(io.BytesIO(pdf_content))
            total_pages = len(pdf_reader.pages)

            logger.info(f"Processing combined PDF with {total_pages} pages")

            # Step 1: Extract metadata from each page using custom model
            page_metadata = []
            for page_num in range(total_pages):
                try:
                    logger.info(f"Extracting metadata from page {page_num + 1}/{total_pages}")
                    metadata = self._extract_page_metadata(pdf_reader, page_num)
                    page_metadata.append(metadata)
                except Exception as e:
                    error_msg = f"Error processing page {page_num + 1}: {str(e)}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)
                    page_metadata.append(None)

            # Step 2: Group pages by document ID
            document_groups = self._group_pages_by_id(page_metadata)

            # Step 3: Create individual PDFs for each document
            documents = []
            for doc_id, pages_info in document_groups.items():
                try:
                    document = self._create_document_pdf(
                        pdf_reader,
                        doc_id,
                        pages_info
                    )
                    documents.append(document)
                    logger.info(
                        f"Created document {doc_id} with {document.page_count} pages"
                    )
                except Exception as e:
                    error_msg = f"Error creating PDF for document {doc_id}: {str(e)}"
                    logger.error(error_msg)
                    processing_errors.append(error_msg)

            # Calculate processing time
            processing_time = (datetime.now() - start_time).total_seconds()

            result = BulkProcessingResult(
                total_pages=total_pages,
                total_documents=len(documents),
                documents=documents,
                processing_errors=processing_errors,
                processing_time_seconds=processing_time
            )

            logger.info(
                f"Processing complete: {len(documents)} documents extracted "
                f"in {processing_time:.2f}s"
            )

            return result

        except Exception as e:
            logger.error(f"Fatal error in process_combined_pdf: {e}")
            raise

    def _extract_page_metadata(self, pdf_reader: PdfReader, page_num: int) -> Dict:
        """
        Extract metadata from a single page using Azure DI custom model

        Args:
            pdf_reader: PyPDF2 PdfReader object
            page_num: Page number (0-indexed)

        Returns:
            dict: Extracted metadata including document_id and other fields
        """
        # Extract single page to temporary bytes
        writer = PdfWriter()
        writer.add_page(pdf_reader.pages[page_num])

        page_bytes = io.BytesIO()
        writer.write(page_bytes)
        page_bytes.seek(0)

        # Call Azure DI with custom model
        try:
            poller = self.client.begin_analyze_document(
                model_id=self.custom_model_id,
                analyze_request=page_bytes.read(),
                content_type="application/pdf",
                features=[]  # Disable image extraction for faster processing
            )
            result = poller.result()

            # Extract fields from custom model result
            metadata = {
                "page_number": page_num,
                "document_id": None,
                "tipo": None,
                "lugar": None,
                "codigo_codae": None,
                "mes": None,
                "ano": None,
                "cep": None,
                "diretoria": None,
                "prestador": None,
                "confidence": 0.0
            }

            # Parse custom model fields
            if result.documents and len(result.documents) > 0:
                doc = result.documents[0]
                fields = doc.fields if hasattr(doc, 'fields') else {}

                # Map custom model fields to our metadata
                # Adjust field names based on your custom model's actual field names
                field_mapping = {
                    "ID": "document_id",
                    "Tipo": "tipo",
                    "Lugar": "lugar",
                    "CodigoCODAE": "codigo_codae",
                    "Mes": "mes",
                    "Ano": "ano",
                    "CEP": "cep",
                    "Diretoria": "diretoria",
                    "Prestador": "prestador"
                }

                confidences = []
                for model_field, meta_field in field_mapping.items():
                    if model_field in fields:
                        field_obj = fields[model_field]
                        value = field_obj.content if hasattr(field_obj, 'content') else field_obj.value
                        confidence = field_obj.confidence if hasattr(field_obj, 'confidence') else 1.0

                        metadata[meta_field] = str(value).strip() if value else None
                        if confidence:
                            confidences.append(confidence)

                # Calculate average confidence
                if confidences:
                    metadata["confidence"] = sum(confidences) / len(confidences)

            logger.debug(f"Page {page_num + 1}: Extracted ID = {metadata['document_id']}")
            return metadata

        except Exception as e:
            logger.error(f"Error extracting metadata from page {page_num + 1}: {e}")
            raise

    def _group_pages_by_id(self, page_metadata: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Group pages by document ID

        Args:
            page_metadata: List of metadata dicts (one per page)

        Returns:
            dict: {document_id: [page_metadata, ...]}
        """
        groups = defaultdict(list)

        for metadata in page_metadata:
            if metadata is None:
                continue

            doc_id = metadata.get("document_id")
            if doc_id:
                groups[doc_id].append(metadata)
            else:
                # Pages without ID go to "UNKNOWN"
                groups["UNKNOWN"].append(metadata)

        logger.info(f"Grouped pages into {len(groups)} documents")
        return groups

    def _create_document_pdf(
        self,
        pdf_reader: PdfReader,
        document_id: str,
        pages_info: List[Dict]
    ) -> ExtractedDocument:
        """
        Create a single PDF document from grouped pages

        Args:
            pdf_reader: Original PDF reader
            document_id: Document ID
            pages_info: List of page metadata dicts

        Returns:
            ExtractedDocument with PDF content
        """
        # Create new PDF with these pages
        writer = PdfWriter()
        page_numbers = []

        for page_info in pages_info:
            page_num = page_info["page_number"]
            writer.add_page(pdf_reader.pages[page_num])
            page_numbers.append(page_num + 1)  # 1-indexed for display

        # Write to bytes
        pdf_bytes = io.BytesIO()
        writer.write(pdf_bytes)
        pdf_content = pdf_bytes.getvalue()

        # Get metadata from first page (all pages should have same metadata)
        first_page = pages_info[0]

        # Calculate average confidence
        confidences = [p["confidence"] for p in pages_info if p.get("confidence")]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        return ExtractedDocument(
            document_id=document_id,
            tipo=first_page.get("tipo"),
            lugar=first_page.get("lugar"),
            codigo_codae=first_page.get("codigo_codae"),
            mes=first_page.get("mes"),
            ano=first_page.get("ano"),
            cep=first_page.get("cep"),
            diretoria=first_page.get("diretoria"),
            prestador=first_page.get("prestador"),
            page_numbers=page_numbers,
            page_count=len(page_numbers),
            confidence=avg_confidence,
            pdf_content=pdf_content
        )


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Initialize processor
    processor = BulkPDFProcessor(
        azure_endpoint=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT"),
        azure_key=os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY"),
        custom_model_id="Header_extraction"
    )

    # Process a combined PDF
    with open("combined_document.pdf", "rb") as f:
        result = processor.process_combined_pdf(f)

    print(f"\nProcessing Results:")
    print(f"Total Pages: {result.total_pages}")
    print(f"Documents Extracted: {result.total_documents}")
    print(f"Processing Time: {result.processing_time_seconds:.2f}s")
    print(f"\nDocuments:")
    for doc in result.documents:
        print(f"  - ID: {doc.document_id}, Pages: {doc.page_count}, Confidence: {doc.confidence:.2f}")

    # Save individual PDFs
    for doc in result.documents:
        output_path = f"output/{doc.document_id}.pdf"
        os.makedirs("output", exist_ok=True)
        with open(output_path, "wb") as f:
            f.write(doc.pdf_content)
        print(f"Saved: {output_path}")
