"""
Mappings for CEI Reconciliation Pipeline

CEI PDF Structure:
- Page 1, Table 2 (11x7): Section 1A - Enrolled students by age group
- Page 1, Table 3 (35x18): Section 2 - Daily attendance INTEGRAL/PARCIAL
- Page 2, Table 1 (37x32): Section 3 - Special diet daily attendance
- Page 2, Table 2: Summary cells (CD110, CD111, CD113)

Excel Ranges:
- Table 2: Y16:DG24
- Table 3: M31:CN62
- Table 1 (Page 2): M71:DB102
- Table 2 (Page 2): CD110, CD111, CD113
"""

# =============================================================================
# Table 2 - Page 1 (11 rows x 7 columns)
# Section 1A: N° de Alunos Matriculados por Período/Faixa Etária
# Excel range: Y16:DG24 (relative columns 0-86)
# =============================================================================
TABLE2_PAGE1_EXCEL_TO_PDF_MAPPING = {
    # Excel relative column -> PDF column index
    # PDF cols: 0=Faixa Etária, 1=Integral(N°), 2=Parcial(N°),
    #           3=Integral(A), 4=Parcial(A), 5=Integral(B), 6=Parcial(B)
    0: 1,    # Y: N° Matriculados Integral
    19: 2,   # AR: N° Matriculados Parcial
    70: 5,   # CQ: Dieta Especial Tipo B Integral
}

TABLE2_PAGE1_COLUMN_NAMES = {
    0: "N° Matriculados Integral",
    19: "N° Matriculados Parcial",
    70: "Dieta Especial Tipo B Integral",
}

# Row mappings for Table 2 (Excel row offset from Y16)
# Excel rows: 0=header, 1-7=age groups, 8=total
TABLE2_PAGE1_ROW_OFFSET = 0  # First data row in Excel

# =============================================================================
# Table 3 - Page 1 (35 rows x 18 columns)
# Section 2: Número de Atendimento por Período (Daily attendance)
# Excel range: M31:CN62 (relative columns 0-79)
# =============================================================================
TABLE3_PAGE1_EXCEL_TO_PDF_MAPPING = {
    # INTEGRAL side
    # PDF cols: 0=DIA, 1=0a1M (empty), 2-7=remaining age groups
    # Excel data columns map to PDF cols 2-7 (skipping empty col 1)
    3: 2,    # P: 01 a 03 M
    6: 3,    # S: 04 a 05 M
    9: 4,    # V: 6 M
    12: 5,   # Y: 07 a 11 M
    15: 6,   # AB: 01 a 03 anos e 11 meses
    18: 7,   # AE: 04 a 06 anos
    # Col 8 = OBSERVAÇÕES (INTEGRAL) - not reconciled

    # PARCIAL side (cols 10-15 in PDF, skipping col 9 for 0a1M)
    72: 14,  # CI: 01 a 03 anos e 11 meses (PARCIAL)
    75: 15,  # CL: 04 a 06 anos (PARCIAL)
}

TABLE3_PAGE1_COLUMN_NAMES = {
    3: "0 a 1 M (INTEGRAL)",
    6: "01 a 03 M (INTEGRAL)",
    9: "04 a 05 M (INTEGRAL)",
    12: "6 M (INTEGRAL)",
    15: "01 a 03 anos e 11 meses (INTEGRAL)",
    18: "04 a 06 anos (INTEGRAL)",
    72: "01 a 03 anos e 11 meses (PARCIAL)",
    75: "04 a 06 anos (PARCIAL)",
}

# =============================================================================
# Table 1 - Page 2 (37 rows x 32 columns)
# Section 3: Special Diet Daily Attendance
# Excel range: M71:DB102 (relative columns 0-93)
# =============================================================================
TABLE1_PAGE2_EXCEL_TO_PDF_MAPPING = {
    # This table continues from Page 1 with special diet columns
    # Based on analysis, data columns are at positions:
    # [0, 3, 6, 9, 12, 15, 18, 19, 20, 21, 22, 24, 25, 27, 28, 31, 34, 37,
    #  41, 44, 47, 50, 54, 57, 60, 63, 66, 69, 72, 75, 79, 82, 85]
    # Note: Column 0 (DIA) is outside the data range, skip it

    # First section - similar to Table 3 INTEGRAL
    3: 1,
    6: 2,
    9: 3,
    12: 4,
    15: 5,
    18: 6,
    19: 7,
    20: 8,
    21: 9,
    22: 10,
    24: 11,
    25: 12,
    27: 13,
    28: 14,
    31: 15,
    34: 16,
    37: 17,
    41: 18,
    # Columns 44, 47, 50, 54 are empty/merged in PDF - skip them
    57: 19,
    60: 20,
    63: 21,
    66: 22,
    69: 23,
    72: 24,
    75: 25,
    79: 26,
    82: 27,
}

TABLE1_PAGE2_COLUMN_NAMES = {
    # Names from Excel row 70
    3: "01 a 03 M",
    6: "04 a 05 M",
    9: "6 M",
    12: "07 a 11 M",
    15: "01 a 03 anos e 11 meses",
    18: "04 a 06 anos",
    19: "",
    20: "",
    21: "",
    22: "0 a 1 M",
    24: "",
    25: "01 a 03 M",
    27: "",
    28: "04 a 05 M",
    31: "6 M",
    34: "07 a 11 M",
    37: "01 a 03 anos e 11 meses",
    41: "04 a 06 anos",
    57: "07 a 11 M",
    60: "01 a 03 anos e 11 meses",
    63: "04 a 06 anos",
    66: "0 a 1 M",
    69: "01 a 03 M",
    72: "04 A 05 M",
    75: "6 M",
    79: "07 a 11 M",
    82: "01 a 03 anos e 11 meses",
}

# =============================================================================
# Table 2 - Page 2 (3 specific cells)
# Summary/Total cells
# Excel cells: CD110, CD111, CD113
# =============================================================================
TABLE2_PAGE2_CELLS = {
    # (row, col) in Excel -> description
    # CD = column 81 (0-indexed)
    # Rows 110, 111, 113 = 109, 110, 112 (0-indexed)
    (109, 81): "Cell CD110",
    (110, 81): "Cell CD111",
    (112, 81): "Cell CD113",
}

# =============================================================================
# Excel range definitions for data extraction
# =============================================================================
EXCEL_RANGES = {
    "table2_page1": {
        "start_col": "Y",
        "end_col": "DG",
        "start_row": 16,
        "end_row": 24,
    },
    "table3_page1": {
        "start_col": "M",
        "end_col": "CN",
        "start_row": 31,
        "end_row": 62,
    },
    "table1_page2": {
        "start_col": "M",
        "end_col": "DB",
        "start_row": 71,
        "end_row": 102,
    },
    "table2_page2": {
        "cells": [(110, "CD"), (111, "CD"), (113, "CD")],
    },
}
