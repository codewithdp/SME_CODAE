"""
Test script to understand Azure Document Intelligence API response
"""

import os
import sys
from dotenv import load_dotenv

# Load environment
load_dotenv()

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

print(f"Endpoint: {endpoint}")
print(f"Key: {key[:20]}...")

if not endpoint or not key:
    print("Error: Missing Azure credentials")
    sys.exit(1)

# Initialize client
client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

# Test with PDF
pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"

print(f"\nAnalyzing PDF: {pdf_path}")

with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

print(f"PDF size: {len(pdf_bytes)} bytes")

# Try analyze
try:
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        analyze_request=pdf_bytes,
        content_type="application/octet-stream"
    )

    print("Polling for results...")
    result = poller.result()

    print(f"\nResult type: {type(result)}")
    print(f"Result attributes: {dir(result)}")

    # Check what's available
    if hasattr(result, 'pages'):
        print(f"\nPages: {len(result.pages) if result.pages else 'None'}")
        if result.pages:
            print(f"First page type: {type(result.pages[0])}")
            print(f"First page attributes: {dir(result.pages[0])[:10]}")

    if hasattr(result, 'tables'):
        print(f"\nTables: {len(result.tables) if result.tables else 'None'}")
        if result.tables:
            print(f"First table type: {type(result.tables[0])}")
            print(f"First table row_count: {result.tables[0].row_count if hasattr(result.tables[0], 'row_count') else 'N/A'}")

    if hasattr(result, 'key_value_pairs'):
        print(f"\nKey-value pairs: {len(result.key_value_pairs) if result.key_value_pairs else 'None'}")

    if hasattr(result, 'content'):
        print(f"\nContent length: {len(result.content) if result.content else 'None'}")
        if result.content:
            print(f"First 200 chars: {result.content[:200]}")

    print("\n✅ Azure DI call successful!")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
