"""
Analyze Section 2 table structure to map columns to fields
"""

import os
from dotenv import load_dotenv
load_dotenv()

from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

client = DocumentIntelligenceClient(endpoint, AzureKeyCredential(key))

pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"

with open(pdf_path, "rb") as f:
    poller = client.begin_analyze_document(
        model_id="prebuilt-layout",
        analyze_request=f.read(),
        content_type="application/octet-stream"
    )
    result = poller.result()

# Find Table 3 (index 2) - Section 2
table = result.tables[2]  # 0-indexed, so Table 3 is index 2

print(f"Table 3: {table.row_count} rows × {table.column_count} columns")
print(f"Total cells: {len(table.cells)}\n")

# Build 2D array
cells = [[None for _ in range(table.column_count)] for _ in range(table.row_count)]

for cell in table.cells:
    row = cell.row_index
    col = cell.column_index
    row_span = getattr(cell, 'row_span', 1) or 1
    col_span = getattr(cell, 'column_span', 1) or 1

    # Fill cells (handle spans)
    for r in range(row, min(row + row_span, table.row_count)):
        for c in range(col, min(col + col_span, table.column_count)):
            if r < len(cells) and c < len(cells[0]):
                cells[r][c] = cell.content

# Print header row (row 0)
print("HEADER ROW (row 0):")
for col_idx in range(min(table.column_count, 20)):  # First 20 columns
    print(f"  Col {col_idx}: {cells[0][col_idx]}")

print("\n" + "="*80 + "\n")

# Print first few data rows (rows 1-3) to understand structure
for row_idx in range(1, min(4, table.row_count)):
    print(f"ROW {row_idx} (Day {row_idx}):")
    for col_idx in range(min(table.column_count, 20)):  # First 20 columns
        content = cells[row_idx][col_idx]
        if content:
            print(f"  Col {col_idx}: {content}")
    print()

print("="*80 + "\n")

# Print column count for all columns
print(f"Total columns: {table.column_count}")
print("\nAll header columns:")
for col_idx in range(table.column_count):
    header = cells[0][col_idx] if cells[0][col_idx] else ""
    print(f"  Col {col_idx}: {header[:50]}")  # Truncate long headers
