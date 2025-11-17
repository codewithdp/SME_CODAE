# Table 0 (Section 1) Mapping - COMPLETED

**Date:** 2025-11-17
**Status:** ✅ Working - 93.33% match rate
**Approach:** Positional mapping with fixed column mapping

---

## Results

- **Match Rate:** 93.33% (14/15 cells)
- **Columns Mapped:** 3 student count columns
- **Remaining Mismatches:** 1 OCR error only
- **Total Row:** ✅ Matches perfectly

---

## Implementation

**File:** `app/reconciliation_engine_positional.py`

**Key Components:**

1. **Fixed Column Mapping** (`SECTION1_EXCEL_TO_PDF_MAPPING`):
   - Maps 3 Excel columns (L, R, V) to PDF columns 2, 3, 4
   - Only reconciles student count columns, not period names or hours
   - PDF Table 0: 6 rows × 5 columns
   - PDF Col 0: PERÍODOS (period names)
   - PDF Col 1: Horas de atendimento (hours)
   - PDF Cols 2-4: Student counts (mapped to Excel)

2. **Value Normalization** (`_normalize_value()`):
   - Same normalization as Section 2 and Section 3
   - Handles empty cells, numbers, and text

3. **Row Mapping:**
   - PDF row 0: Headers (PERÍODOS, Horas, student columns)
   - PDF row 1: INTEGRAL (8 horas) - empty data
   - PDF row 2: 1º PERÍODO MATUTINO - has data
   - PDF row 3: 2º PERÍODO INTERMEDIARIO - empty data
   - PDF row 4: 3º PERÍODO VESPERTINO - has data
   - PDF row 5: TOTAL - totals
   - Excel row 15 → PDF row 1 (INTEGRAL)
   - Excel row 16 → PDF row 2 (1º PERÍODO)
   - Excel row 17 → PDF row 3 (2º PERÍODO)
   - Excel row 18 → PDF row 4 (3º PERÍODO)
   - Excel row 19: Empty row (skipped)
   - Excel row 20 → PDF row 5 (TOTAL)
   - **Important:** Excel has empty row 19 between data and Total
   - Must pass `excel_row_skip=1` parameter to handle empty row before Total

---

## Column Mapping

```python
SECTION1_EXCEL_TO_PDF_MAPPING = {
    11: 2,  # L: Nº DE ALUNOS MATRICULADOS
    17: 3,  # R: Nº DE ALUNOS MATRICULADOS COM DIETA ESPECIAL - A
    21: 4,  # V: Nº DE ALUNOS MATRICULADOS COM DIETA ESPECIAL - B
}
```

---

## PDF Table Structure

**Table 0** in PDF (index 0, page 1):
- 6 rows × 5 columns
- Row 0: Headers (PERÍODOS, Horas de atendimento, Nº ALUNOS, DIETA A, DIETA B)
- Rows 1-4: Period data (INTEGRAL, 1º PERÍODO, 2º PERÍODO, 3º PERÍODO)
- Row 5: TOTAL

**Column breakdown:**
- Col 0: PERÍODOS (period names)
- Col 1: Horas de atendimento (hours)
- Col 2: Nº DE ALUNOS MATRICULADOS (total students)
- Col 3: Nº DE ALUNOS MATRICULADOS COM DIETA ESPECIAL - A (special diet A)
- Col 4: Nº DE ALUNOS MATRICULADOS COM DIETA ESPECIAL - B (special diet B)

---

## Usage Example

```python
from app.reconciliation_engine_positional import (
    PositionalReconciliationEngine,
    SECTION1_EXCEL_TO_PDF_MAPPING
)

engine = PositionalReconciliationEngine()

results = engine.reconcile_section(
    pdf_path="path/to/pdf.pdf",
    excel_path="path/to/excel.xlsm",
    table_index=0,                          # Table 0 for Section 1
    excel_start_row=15,                     # First data row in Excel (INTEGRAL)
    column_mapping=SECTION1_EXCEL_TO_PDF_MAPPING,
    pdf_data_start_row=1,                   # Data starts at PDF row 1 (not 2)
    excel_row_skip=1                        # Skip empty Excel row 19 before Total
)

print(f"Match rate: {results['match_percentage']}%")
```

---

## Known Issues

**OCR Error** (1 cell only):
- Row 2 (1º PERÍODO), Cell V16: '5' misread as 'S'

This is an expected OCR misread and represents only 6.67% of all cells (1/15).

---

## Notes

- Section 1 is simpler than Section 2/3 - only 5 rows to reconcile
- Only 3 columns need reconciliation (student counts)
- Excel has an empty row (19) between data rows and Total row
- The `excel_row_skip` parameter handles this empty row for the Total calculation
- All rows have text labels (not day numbers like Section 2/3)
- The `pdf_data_start_row=1` is crucial (Section 2/3 use 2 or 3)

---

## Next Steps

- [x] Map Table 0 (Section 1) - COMPLETED
- [x] Map Table 2 (Section 2) - COMPLETED (98.52% match)
- [x] Map Table 4 (Section 3) - COMPLETED (98.21% match)
- [ ] Integrate all 3 sections into main reconciliation API
- [ ] Add to frontend for display
