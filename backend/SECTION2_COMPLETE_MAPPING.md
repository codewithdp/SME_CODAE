# Section 2 - Complete Excel to PDF Mapping

## Structure: 36 data fields + Day column

### Excel → PDF Column Mapping

| Period | Field | Excel Col | PDF Col |
|--------|-------|-----------|---------|
| **Day** | Day number | C (3) | 0 |
| **INTEGRAL** | | | |
| | Frequência | E (5) | 1 |
| | Lanche 4h | G (7) | 2 |
| | Lanche 6h | H (8) | 3 |
| | Refeição | J (10) | 4 |
| | Repetição refeição | K (11) | 5 |
| | Sobremesa | L (12) | 6 |
| | Repetição sobremesa | M (13) | 7 |
| | 2ª Refeição | N (14) | 8 |
| | Repetição 2ª refeição | O (15) | 9 |
| | 2ª Sobremesa | P (16) | 10 |
| | Repetição 2ª sobremesa | Q (17) | 11 |
| **1º PERÍODO** | | | |
| | Frequência | R (18) | 12 |
| | Lanche 4h | T (20) | 13 |
| | Lanche 6h | U (21) | 14 |
| | Refeição | X (24) | 15 |
| | Repetição refeição | AB (28) | 16 |
| | Sobremesa | AE (31) | 17 |
| | Repetição sobremesa | AI (35) | 18 |
| **INTERMEDIÁRIO** | | | |
| | Frequência | AK (37) | 19 |
| | Lanche 4h | AL (38) | 20 |
| | Refeição | AM (39) | 21 |
| | Repetição refeição | AO (41) | 22 |
| | Sobremesa | AQ (43) | 23 |
| | Repetição sobremesa | AS (45) | 24 |
| **3º PERÍODO** | | | |
| | Frequência | AU (47) | 25 |
| | Lanche 4h | AW (49) | 26 |
| | Lanche 6h | AY (51) | 27 |
| | Refeição | BE (57) | 28 |
| | Repetição refeição | BI (61) | 29 |
| | Sobremesa | BJ (62) | 30 |
| | Repetição sobremesa | BQ (69) | 31 |
| **DOCE** | | | |
| | INTEGRAL | BR (70) | 32 |
| | 1º PERÍODO | BU (73) | 33 |
| | INTERMEDIÁRIO | BV (74) | 34 |
| | 3º PERÍODO | BW (75) | 35 |

## Data Range
- **Excel:** Rows 28-58 (days 1-31), Row 59 (TOTAL)
- **PDF:** Rows 3-33 (days 1-31), Row 34 or last row (TOTAL)

## Total Cell Count
- **Days:** 31 days × 35 fields = 1,085 cells
- **TOTAL row:** 31 fields
- **Grand Total:** 1,116 cells (some fields may not have TOTAL)

## Notes
- All columns align perfectly between Excel and PDF
- INTEGRAL and INTERMEDIÁRIO periods are empty in both files
- Doce checkboxes use :selected: / :unselected: in PDF, X in Excel
