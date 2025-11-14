"""
Debug script to see what paragraphs/lines Azure DI extracts from page 2
Maybe the table structure isn't detected but the text content is there
"""

import asyncio
import os
from dotenv import load_dotenv
from azure.ai.documentintelligence.aio import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential

load_dotenv()

async def main():
    pdf_path = "/Users/writetodennis/dev/SME/EMEI_test1.pdf"
    endpoint = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT")
    key = os.getenv("AZURE_DOCUMENT_INTELLIGENCE_KEY")

    print("Analyzing PDF page 2 content...")

    client = DocumentIntelligenceClient(endpoint=endpoint, credential=AzureKeyCredential(key))

    with open(pdf_path, "rb") as f:
        poller = await client.begin_analyze_document(
            "prebuilt-layout",
            analyze_request=f,
            content_type="application/pdf"
        )
        result = await poller.result()

    # Get page 2 content
    page2 = result.pages[1] if len(result.pages) > 1 else None
    if not page2:
        print("❌ No page 2 found!")
        return

    print(f"\n✅ Page 2 found")
    print(f"   Lines: {len(page2.lines) if page2.lines else 0}")
    print(f"   Words: {len(page2.words) if page2.words else 0}")

    # Show all lines from page 2
    if page2.lines:
        print(f"\n" + "="*100)
        print(f"ALL LINES FROM PAGE 2 ({len(page2.lines)} lines)")
        print("="*100)
        for i, line in enumerate(page2.lines[:100]):  # First 100 lines
            print(f"{i:3d}: {line.content}")

    # Also check paragraphs on page 2
    if result.paragraphs:
        page2_paragraphs = [p for p in result.paragraphs
                            if p.bounding_regions and p.bounding_regions[0].page_number == 2]
        print(f"\n" + "="*100)
        print(f"PAGE 2 PARAGRAPHS ({len(page2_paragraphs)} paragraphs)")
        print("="*100)
        for i, p in enumerate(page2_paragraphs[:50]):
            print(f"{i:3d}: {p.content[:100]}")

    await client.close()

if __name__ == "__main__":
    asyncio.run(main())
