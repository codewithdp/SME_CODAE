"""
Explore what Section 3 contains in the Excel file
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.excel_parser_custom import CustomExcelParser

excel_path = "/Users/writetodennis/dev/SME/019382.xlsm"

print("="*100)
print("SECTION 3 - EXCEL DATA STRUCTURE")
print("="*100)

excel_parser = CustomExcelParser()
excel_data = excel_parser.parse_file(excel_path)

print("\nSection 3 object type:", type(excel_data.section3))
print("\nSection 3 attributes:")

# Check what attributes section3 has
if hasattr(excel_data, 'section3') and excel_data.section3:
    section3 = excel_data.section3

    # Get all attributes
    attrs = [attr for attr in dir(section3) if not attr.startswith('_')]
    print(f"\nAvailable attributes ({len(attrs)}):")
    for attr in attrs:
        print(f"  - {attr}")

    # Try to print the section3 object
    print("\nSection 3 data:")
    print(section3)
else:
    print("\n⚠️  Section 3 not found or empty in Excel data")

print("\n" + "="*100)
