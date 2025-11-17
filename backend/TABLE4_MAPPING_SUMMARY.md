# Table 4 (Section 3) Mapping - COMPLETED

**Date:** 2025-11-17
**Status:** ✅ Working - 98.21% match rate
**Approach:** Positional mapping with fixed column mapping

---

## Results

- **Match Rate:** 98.21% (220/224 cells)
- **Columns Mapped:** 7 data columns
- **Remaining Mismatches:** 4 OCR errors only
- **Total Row:** ✅ Matches perfectly

---

## Implementation

**File:** `app/reconciliation_engine_positional.py`

**Key Components:**

1. **Fixed Column Mapping** (`SECTION3_EXCEL_TO_PDF_MAPPING`):
   - Maps 7 visible Excel columns to PDF columns 1-7
   - Skips metadata columns (A, B, C)
   - Skips merged-away cells
   - PDF Table 4: 35 rows × 10 columns
   - PDF Col 0: Day number
   - PDF Cols 1-7: Data (mapped to Excel)
   - PDF Cols 8-9: LANCHE EMERGENCIAL, KIT LANCHE (not in Excel Section 3)

2. **Value Normalization** (`_normalize_value()`):
   - Same normalization as Section 2
   - Empty cells = `:unselected:`
   - `X` or `x` = `:selected:`
   - Removes thousands separators

3. **Row Mapping:**
   - PDF row 0: Main headers
   - PDF row 1: Group headers (GRUPO A, GRUPO B)
   - PDF row 2: Detail headers
   - PDF rows 3+: Data rows (Day 1, Day 2, ..., Total)
   - Excel row 77+ → PDF row 3+ (Day 1 starts at Excel row 77)
   - **Important:** Section 3 data starts at PDF row 3 (not row 2 like Section 2)
   - Must pass `pdf_data_start_row=3` parameter to reconcile_section()

---

## Column Mapping

```python
SECTION3_EXCEL_TO_PDF_MAPPING = {
    3: 1,   # D: FREQUENCIA (GRUPO A)
    5: 2,   # F: Lanche (4h) (GRUPO A)
    7: 3,   # H: Lanche (6h) (GRUPO A)
    10: 4,  # K: REFEIÇÃO (SOMENTE DIETA ENTERAL) (GRUPO A)
    12: 5,  # M: FREQUENCIA (GRUPO B)
    14: 6,  # O: Lanche (4h) (GRUPO B)
    16: 7,  # Q: Lanche (6h) (GRUPO B)
}
```

---

## PDF Table Structure

**Table 4** in PDF (index 4, page 2):
- 35 rows × 10 columns
- Row 0: Main headers ("Dias", "I INFORMAR A QUANTIDADE...", "LANCHE EMERGENCIAL", "KIT LANCHE")
- Row 1: Group headers ("DIETA ESPECIAL GRUPO A", "DIETA ESPECIAL GRUPO B")
- Row 2: Detail headers (FREQUENCIA, Lanche 4h, Lanche 6h, REFEIÇÃO ENTERAL, ...)
- Rows 3-34: Day 1 through Day 31 + Total row

**Column breakdown:**
- Col 0: Day number
- Cols 1-4: GRUPO A (FREQUENCIA, Lanche 4h, Lanche 6h, REFEIÇÃO ENTERAL)
- Cols 5-7: GRUPO B (FREQUENCIA, Lanche 4h, Lanche 6h)
- Cols 8-9: LANCHE EMERGENCIAL, KIT LANCHE (not present in Excel Section 3)

---

## Usage Example

```python
from app.reconciliation_engine_positional import (
    PositionalReconciliationEngine,
    SECTION3_EXCEL_TO_PDF_MAPPING
)

engine = PositionalReconciliationEngine()

results = engine.reconcile_section(
    pdf_path="path/to/pdf.pdf",
    excel_path="path/to/excel.xlsm",
    table_index=4,                          # Table 4 for Section 3
    excel_start_row=77,                     # First data row in Excel (Day 1)
    column_mapping=SECTION3_EXCEL_TO_PDF_MAPPING,
    pdf_data_start_row=3                    # Day 1 data starts at PDF row 3 (not 2)
)

print(f"Match rate: {results['match_percentage']}%")
```

---

## Bug Fix: Total Row Mapping

**Issue Found:** Initial test showed Total row at Excel row 109 instead of 108, with 7 mismatches.

**Root Cause:**
- Section 2 has 2 header rows (0, 1), data starts at PDF row 2
- Section 3 has 3 header rows (0, 1, 2), data starts at PDF row 3
- Original code hardcoded `row_idx - 2` for Total row calculation, which only worked for Section 2

**Fix Applied:**
- Added `pdf_data_start_row` parameter to `reconcile_section()` method
- Updated Total row formula: `excel_row_idx = excel_start_row + (pdf_row["row_idx"] - pdf_data_start_row)`
- For Section 3: pass `pdf_data_start_row=3`

**Result:** Total row now matches perfectly at Excel row 108. Match rate improved from 95.09% to 98.21%.

---

## Known Issues

**OCR Errors** (4 cells only):
- Day 6, Cell M82: '6' misread as 'Б'
- Day 15, Cell M91: '7' misread as '?'
- Day 18, Cell Q94: '6' misread as '5'
- Day 25, Cell M101: '5' misread as 'S'

These are expected OCR misreads and represent only 1.79% of all cells.

---

## Next Steps

- [x] Map Table 4 (Section 3) - COMPLETED
- [ ] Integrate Section 2 and Section 3 into main reconciliation API
- [ ] Add to frontend for display
- [ ] Consider additional tables if needed
