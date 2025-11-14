#!/usr/bin/env python3
"""Quick test of bulk upload endpoint"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
PDF_FILE = "../EMEI_test1.pdf"

print("=" * 70)
print("TESTING BULK UPLOAD API")
print("=" * 70)

# Test 1: Upload PDF
print("\n1. Uploading PDF...")
try:
    with open(PDF_FILE, 'rb') as f:
        files = {'file': (PDF_FILE.split('/')[-1], f, 'application/pdf')}
        response = requests.post(f"{BASE_URL}/api/v1/bulk/upload-pdf", files=files)

    print(f"   Status Code: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        upload_id = data['id']
        print(f"   ✅ Upload successful!")
        print(f"   Upload ID: {upload_id}")
        print(f"   Status: {data['status']}")
        print(f"   Filename: {data['original_filename']}")
    else:
        print(f"   ❌ Upload failed")
        print(f"   Response: {response.text}")
        exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    exit(1)

# Test 2: Check status immediately
print("\n2. Checking initial status...")
try:
    response = requests.get(f"{BASE_URL}/api/v1/bulk/{upload_id}/status")
    data = response.json()
    print(f"   Status: {data['status']}")
    print(f"   Progress: {data.get('progress_percentage', 0)}%")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Poll status until complete
print("\n3. Monitoring processing (max 2 minutes)...")
max_wait = 120
start_time = time.time()

while time.time() - start_time < max_wait:
    try:
        response = requests.get(f"{BASE_URL}/api/v1/bulk/{upload_id}/status")
        data = response.json()
        status = data['status']
        progress = data.get('progress_percentage', 0)

        print(f"   [{int(time.time() - start_time)}s] Status: {status} ({progress}%)")

        if status == "completed":
            print(f"   ✅ Processing complete!")
            print(f"   Total pages: {data.get('total_pages')}")
            print(f"   Total documents: {data.get('total_documents')}")
            break
        elif status == "failed":
            print(f"   ❌ Processing failed: {data.get('error_message')}")
            exit(1)

        time.sleep(5)
    except Exception as e:
        print(f"   ❌ Error: {e}")
        break
else:
    print(f"   ⚠️  Timeout after {max_wait}s")

# Test 4: Get documents
print("\n4. Retrieving extracted documents...")
try:
    response = requests.get(f"{BASE_URL}/api/v1/bulk/{upload_id}/documents")
    documents = response.json()

    print(f"   ✅ Found {len(documents)} document(s)")
    print("\n   " + "-" * 66)
    print(f"   {'ID':<12} {'Pages':<8} {'Tipo':<12} {'Status':<12}")
    print("   " + "-" * 66)

    for doc in documents:
        doc_id = doc['document_id']
        pages = doc['page_count']
        tipo = doc.get('tipo') or 'N/A'
        status = doc['status']
        page_indicator = f"{pages} {'✅' if pages == 2 else '⚠️'}"

        print(f"   {doc_id:<12} {page_indicator:<8} {tipo:<12} {status:<12}")

        # Show detailed metadata for first document
        if doc == documents[0]:
            print(f"\n   Metadata for {doc_id}:")
            print(f"     - Lugar: {doc.get('lugar')}")
            print(f"     - Código CODAE: {doc.get('codigo_codae')}")
            print(f"     - Mês: {doc.get('mes')}")
            print(f"     - Ano: {doc.get('ano')}")
            print(f"     - Diretoria: {doc.get('diretoria')}")
            print(f"     - Confidence: {doc.get('extraction_confidence', 0):.2f}")

except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 5: Get full upload details
print("\n5. Getting complete upload details...")
try:
    response = requests.get(f"{BASE_URL}/api/v1/bulk/{upload_id}")
    data = response.json()

    print(f"   ✅ Upload summary:")
    print(f"     - Total pages: {data.get('total_pages')}")
    print(f"     - Total documents: {data.get('total_documents')}")
    print(f"     - Documents with 2 pages: {data.get('documents_with_2_pages')}")
    print(f"     - Processing time: {data.get('processing_completed_at')}")

except Exception as e:
    print(f"   ❌ Error: {e}")

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)
print(f"\nUpload ID: {upload_id}")
print(f"View in browser: {BASE_URL}/docs")
print("=" * 70)
