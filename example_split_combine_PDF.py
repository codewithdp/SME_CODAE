import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from PyPDF2 import PdfReader, PdfWriter
import re
from collections import defaultdict

# Azure Document Intelligence setup
endpoint = "YOUR_ENDPOINT"
key = "YOUR_KEY"
document_analysis_client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))

def extract_id_from_page(page_image_or_pdf):
    """
    Use Azure Document Intelligence to OCR and extract ID from header
    """
    with open(page_image_or_pdf, "rb") as f:
        poller = document_analysis_client.begin_analyze_document(
            "prebuilt-layout", f
        )
    result = poller.result()
    
    # Extract text from top portion (header area)
    # Adjust y-coordinate threshold based on your documents
    header_text = []
    for page in result.pages:
        for line in page.lines:
            # Assuming header is in top 15% of page
            if line.bounding_box[1] < page.height * 0.15:
                header_text.append(line.content)
    
    # Extract ID using regex (adjust pattern to match your ID format)
    # Example: "ID: 12345" or "Document ID: ABC-123"
    full_text = " ".join(header_text)
    id_match = re.search(r'ID[:\s]*([A-Z0-9\-]+)', full_text, re.IGNORECASE)
    
    return id_match.group(1) if id_match else None

def process_combined_pdf(input_pdf_path, output_folder):
    """
    Main processing function
    """
    reader = PdfReader(input_pdf_path)
    page_groups = defaultdict(list)
    
    # Process each page
    for page_num, page in enumerate(reader.pages):
        print(f"Processing page {page_num + 1}/{len(reader.pages)}")
        
        # Extract single page to temporary file
        temp_pdf = f"temp_page_{page_num}.pdf"
        writer = PdfWriter()
        writer.add_page(page)
        with open(temp_pdf, "wb") as f:
            writer.write(f)
        
        # Extract ID from page
        extracted_id = extract_id_from_page(temp_pdf)
        
        if extracted_id:
            page_groups[extracted_id].append(page_num)
            print(f"  Found ID: {extracted_id}")
        else:
            page_groups["UNKNOWN"].append(page_num)
            print(f"  No ID found")
        
        os.remove(temp_pdf)
    
    # Create grouped PDFs
    os.makedirs(output_folder, exist_ok=True)
    
    for doc_id, page_numbers in page_groups.items():
        output_pdf = os.path.join(output_folder, f"{doc_id}.pdf")
        writer = PdfWriter()
        
        for page_num in page_numbers:
            writer.add_page(reader.pages[page_num])
        
        with open(output_pdf, "wb") as f:
            writer.write(f)
        
        print(f"Created {output_pdf} with {len(page_numbers)} pages")

# Usage
process_combined_pdf("combined_document.pdf", "output_grouped_pdfs")