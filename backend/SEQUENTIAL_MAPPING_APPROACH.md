# Sequential Mapping Approach for PDF Reconciliation

This document describes the sequential mapping approach used in the CEI reconciliation engine to handle OCR column count variations.

## Problem

Azure Document Intelligence OCR can produce different column counts for the same table structure due to:
- Header cells being split into multiple columns
- Merged cells being interpreted differently
- Different PDF rendering

For example, a table might be detected as 18 or 19 columns, or 30 vs 32 columns, even though the actual data structure is the same.

## Solution: Sequential Mapping from First Data Cell

Instead of relying on absolute column positions that can shift, we:

1. **Detect the table** by dimension ranges (rows × columns)
2. **Identify the first data cell** position
3. **Map columns sequentially** from that starting point

### Key Insight

> "The column headers sometimes get split into 2 or more columns, but in reality, the data cells are just 1 column. We should find the first data cell and then keep adding 1 to find the next columns, not depending on the headers above."

## Implementation Pattern

### Step 1: Table Detection (Still Uses Dimensions)

Use flexible dimension ranges to identify the correct table:

```python
# Accept range of column counts
if page_num == 1 and 33 <= rows <= 37 and 16 <= cols <= 19:
    table3_page1_idx = idx
```

### Step 2: Find the First Data Cell

**Don't assume fixed row positions.** Instead, search for the actual first data cell by looking for specific content patterns in the data row.

#### For Section 1 (Age Group Table)
Search for "0 a 1" in column 0 to find the first age group row:

```python
# Find first data row by looking for "0 a 1" in column 0
pdf_data_start = 2  # default
for cell in table.cells:
    if cell.column_index == 0 and cell.content:
        content = cell.content.strip().lower()
        if "0 a 1" in content or "0a1" in content:
            pdf_data_start = cell.row_index
            break
```

#### For Section 2/3 (Day-based Tables)
Search for "1" in column 0 to find Day 1:

```python
# Find Day 1 row
for cell in table.cells:
    if cell.column_index == 0 and cell.content:
        if cell.content.strip() == "1":
            day1_row = cell.row_index
            break
```

### Step 3: Handle Column Spans (Merged Cells)

Azure Document Intelligence returns `column_span` for merged cells. Use this to find where sections actually start.

**Problem:** OCR may merge cells, causing column positions to shift. For example, OBSERVAÇÕES at col 8 might span into col 9, pushing PARCIAL to start at col 10.

**Solution:** Check the span of boundary cells to calculate correct positions:

```python
# Find OBSERVAÇÕES span to determine where PARCIAL starts
obs_span = 1  # default
for cell in table.cells:
    if cell.column_index == 8:
        # Check if this is a data row (not header)
        row_cells = {c.column_index: c for c in table.cells if c.row_index == cell.row_index}
        if row_cells.get(0) and row_cells[0].content.strip() == "1":  # Day 1
            obs_span = cell.column_span if hasattr(cell, 'column_span') and cell.column_span else 1
            break

parcial_start = 8 + obs_span  # PARCIAL starts after OBSERVAÇÕES span
```

**Example:**
- 400153 (17 cols): col 8 span=1 → PARCIAL starts at col 9
- 400187 (19 cols): col 8 span=2 → PARCIAL starts at col 10

### Step 4: Build Sequential Mapping

Once you know where each section starts, map columns sequentially:

```python
abs_mapping = {
    # INTEGRAL (cols 1-7, always fixed)
    15: 2,   # 01 a 03 M
    18: 3,   # 04 a 05 M
    # ... etc

    # PARCIAL (sequential from parcial_start)
    84: parcial_start + 5,  # 01 a 03 anos
    87: parcial_start + 6,  # 04 a 06 anos
}
```

## CEI Section Examples

### Section 1: Enrolled Students (Table 2, Page 1)

**First data cell:** Y16 (N° Matriculados Integral)

**Structure:** 6-7 columns
- Col 0: Faixa Etária (labels)
- Cols 1-6: Data columns

**Mapping:**
```python
if table.column_count == 7:
    abs_mapping = {
        24: 1,   # Y: N° Matriculados Integral
        43: 2,   # AR: N° Matriculados Parcial
        94: 5,   # CQ: Dieta Especial Tipo B Integral
    }
else:
    # 6-col table - adjust last column
    abs_mapping = {
        24: 1,
        43: 2,
        94: table.column_count - 2,  # Second to last
    }
```

### Section 2: Daily Attendance (Table 3, Page 1)

**First data cell:** M31 (Day 1, column 0 a 1 M)

**Structure:** 17-19 columns
- Col 0: DIA (day numbers)
- Cols 1-7: INTEGRAL data
- Col 8: OBSERVAÇÕES (may span multiple columns)
- Cols 9+: PARCIAL data (position depends on col 8 span)

**Finding PARCIAL start using span detection:**
```python
# Find OBSERVAÇÕES span in Day 1 data row
obs_span = 1
for cell in table.cells:
    if cell.column_index == 8:
        row_cells = {c.column_index: c for c in table.cells if c.row_index == cell.row_index}
        if row_cells.get(0) and row_cells[0].content.strip() == "1":
            obs_span = cell.column_span or 1
            break

parcial_start = 8 + obs_span
```

**Mapping:**
```python
abs_mapping = {
    # INTEGRAL (fixed positions from col 1)
    15: 2,   # 01 a 03 M
    18: 3,   # 04 a 05 M
    21: 4,   # 6 M
    24: 5,   # 07 a 11 M
    27: 6,   # 01 a 03 anos
    30: 7,   # 04 a 06 anos
    # PARCIAL (sequential from parcial_start)
    84: parcial_start + 5,  # 01 a 03 anos
    87: parcial_start + 6,  # 04 a 06 anos
}
```

### Section 3: Special Diet (Table 1, Page 2)

**First data cell:** M71 (Day 1, column 0 a 1 M)

**Structure:** 30-32 columns
- Col 0: DIA
- Cols 1-7: Section 1 (7 data columns)
- Cols 8-14: Section 2 (7 data columns)
- Cols 15-21: Section 3 (7 data columns)
- Cols 22-28: Section 4 (7 data columns)

**Mapping:**
```python
abs_mapping = {
    # Section 1 (cols 1-7)
    15: 2, 18: 3, 21: 4, 24: 5, 27: 6, 30: 7,
    # Section 2 (cols 8-14)
    34: 8, 37: 9, 40: 10, 43: 11, 46: 12, 49: 13, 53: 14,
    # Section 3 (cols 15-21)
    69: 19, 72: 20, 75: 21,
    # Section 4 (cols 22-28)
    78: 22, 81: 23, 84: 24, 87: 25, 91: 26, 94: 27,
}
```

## OCR Error Normalization

In addition to sequential mapping, normalize common OCR errors:

```python
ocr_map = {
    'I': '1', 'l': '1',  # I and l → 1
    'O': '0',            # O → 0
    'S': '5',            # S → 5
    'G': '6', 'b': '6',  # G and b → 6
    'D': '0',            # D → 0
    'Z': '2',            # Z → 2
}
```

Apply to short values (1-3 characters) that result in digits after conversion.

## Applying to EMEI Model

To apply this approach to EMEI:

1. **Analyze EMEI PDF structure** to identify:
   - Table dimensions (with acceptable ranges)
   - First data cell for each section
   - Column structure (fixed vs variable sections)

2. **Identify variation patterns:**
   - Which columns tend to split?
   - What's the typical column count range?

3. **Build dynamic mappings:**
   - Fixed positions for stable columns
   - Calculated positions for variable sections (e.g., `column_count - N`)

4. **Test with multiple PDFs** to verify the mapping works across variations

## Key Files

- `/backend/app/pipelines/cei/engine.py` - CEI reconciliation engine with sequential mapping
- `/backend/app/pipelines/cei/mappings.py` - Column name definitions
- `/backend/app/pipelines/shared/positional_engine.py` - Base engine with OCR normalization

## Results

With sequential mapping and span detection implemented:

| Test ID | Section 1 | Section 2 | Section 3 | Overall |
|---------|-----------|-----------|-----------|---------|
| 400129  | 100%      | 100%      | 99.86%    | 99.9%   |
| 400153  | 100%      | 100%      | 100%      | 100%    |
| 400187  | 91.67%    | 100%      | 99.72%    | 99.59%  |

**Key improvements:**
- Section 1: Fixed row alignment issues by finding first data cell (was 57% for 400129)
- Section 2: 100% across all tests using span detection for PARCIAL start

Remaining mismatches are typically:
- OCR quality issues (artifacts, merged text)
- Actual data differences between PDF and Excel
- Edge cases in specific PDF structures
