"""
Analyze all columns in Section 2 table
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
table = result.tables[2]

# Build 2D array
cells = [[None for _ in range(table.column_count)] for _ in range(table.row_count)]

for cell in table.cells:
    row = cell.row_index
    col = cell.column_index
    row_span = getattr(cell, 'row_span', 1) or 1
    col_span = getattr(cell, 'column_span', 1) or 1

    for r in range(row, min(row + row_span, table.row_count)):
        for c in range(col, min(col + col_span, table.column_count)):
            if r < len(cells) and c < len(cells[0]):
                cells[r][c] = cell.content

# Print row 1 (period headers)
print("ROW 1 - Period headers:")
for col_idx in range(table.column_count):
    content = cells[1][col_idx] if cells[1][col_idx] else ""
    print(f"  Col {col_idx:2d}: {content}")

print("\n" + "="*80 + "\n")

# Print row 2 (field headers)
print("ROW 2 - Field headers:")
for col_idx in range(table.column_count):
    content = cells[2][col_idx] if cells[2][col_idx] else ""
    print(f"  Col {col_idx:2d}: {content}")

print("\n" + "="*80 + "\n")

# Print row 3 (day 1 data)
print("ROW 3 - Day 1 data:")
for col_idx in range(table.column_count):
    content = cells[3][col_idx] if cells[3][col_idx] else ""
    if content and content != "Dlas":
        print(f"  Col {col_idx:2d}: {content}")
