"""
Mappings for EMEI Reconciliation Pipeline
"""

# Section 2 (Table 2) Excel → PDF column mapping
SECTION2_EXCEL_TO_PDF_MAPPING = {
    4: 1,  # E: Frequência (INTEGRAL)
    6: 2,  # G: Lanche (4h)
    7: 3,  # H: Lanche (6h)
    9: 4,  # J: Refeição
    10: 5,  # K: Repetição da refeição
    11: 6,  # L: Sobremesa
    12: 7,  # M: Repetição da sobremesa
    13: 8,  # N: 2a Refeição
    14: 9,  # O: Repetição da  2a refeição
    15: 10,  # P: 2a Sobremesa
    16: 11,  # Q: 2a Repetição da sobremesa
    17: 12,  # R: Frequência (1º PERÍODO)
    19: 13,  # T: Lanche (4h)
    20: 14,  # U: Lanche (6h)
    23: 15,  # X: Refeição
    27: 16,  # AB: Repetição da refeição
    30: 17,  # AE: Sobremesa
    34: 18,  # AI: Repetição da sobremesa
    36: 19,  # AK: Frequência (INTERMEDIARIO)
    37: 20,  # AL: Lanche (4h)
    38: 21,  # AM: Refeição
    40: 22,  # AO: Repetição da refeição
    42: 23,  # AQ: Sobremesa
    44: 24,  # AS: Repetição da sobremesa
    46: 25,  # AU: Frequência (3º PERÍODO)
    48: 26,  # AW: Lanche(4h)
    50: 27,  # AY: Lanche (6h)
    56: 28,  # BE: Refeição
    60: 29,  # BI: Repetição da refeição
    61: 30,  # BJ: Sobremesa
    68: 31,  # BQ: Repetição da sobremesa
    69: 32,  # BR: INTEGRAL (checkbox)
    72: 33,  # BU: 1º PERÍODO (checkbox)
    73: 34,  # BV: INTERMEDIÁRIO (checkbox)
    74: 35,  # BW: 3º PERÍODO (checkbox)
}

# Section 1 (Table 0) Excel → PDF column mapping
SECTION1_EXCEL_TO_PDF_MAPPING = {
    11: 2,  # L: Nº DE ALUNOS MATRICULADOS
    17: 3,  # R: Nº DE ALUNOS MATRICULADOS COM DIETA ESPECIAL - A
    21: 4,  # V: Nº DE ALUNOS MATRICULADOS COM DIETA ESPECIAL - B
}

# Section 3 (Table 4) Excel → PDF column mapping
SECTION3_EXCEL_TO_PDF_MAPPING = {
    3: 1,   # D: FREQUENCIA (GRUPO A)
    5: 2,   # F: Lanche (4h) (GRUPO A)
    7: 3,   # H: Lanche (6h) (GRUPO A)
    10: 4,  # K: REFEIÇÃO (SOMENTE DIETA ENTERAL) (GRUPO A)
    12: 5,  # M: FREQUENCIA (GRUPO B)
    14: 6,  # O: Lanche (4h) (GRUPO B)
    16: 7,  # Q: Lanche (6h) (GRUPO B)
}

# Column name mappings - Excel column index to human-readable name
SECTION1_COLUMN_NAMES = {
    11: "Nº Alunos Matriculados",
    17: "Dieta Especial - A",
    21: "Dieta Especial - B",
}

SECTION2_COLUMN_NAMES = {
    4: "Frequência (INTEGRAL)",
    6: "Lanche 4h",
    7: "Lanche 6h",
    9: "Refeição",
    10: "Repetição Refeição",
    11: "Sobremesa",
    12: "Repetição Sobremesa",
    13: "2ª Refeição",
    14: "Repetição 2ª Refeição",
    15: "2ª Sobremesa",
    16: "Repetição 2ª Sobremesa",
    17: "Frequência (1º PERÍODO)",
    19: "Lanche 4h (1º)",
    20: "Lanche 6h (1º)",
    23: "Refeição (1º)",
    27: "Repetição Refeição (1º)",
    30: "Sobremesa (1º)",
    34: "Repetição Sobremesa (1º)",
    36: "Frequência (INTERMEDIÁRIO)",
    37: "Lanche 4h (INT)",
    38: "Refeição (INT)",
    40: "Repetição Refeição (INT)",
    42: "Sobremesa (INT)",
    44: "Repetição Sobremesa (INT)",
    46: "Frequência (3º PERÍODO)",
    48: "Lanche 4h (3º)",
    50: "Lanche 6h (3º)",
    56: "Refeição (3º)",
    60: "Repetição Refeição (3º)",
    61: "Sobremesa (3º)",
    68: "Repetição Sobremesa (3º)",
    69: "INTEGRAL (checkbox)",
    72: "1º PERÍODO (checkbox)",
    73: "INTERMEDIÁRIO (checkbox)",
    74: "3º PERÍODO (checkbox)",
}

SECTION3_COLUMN_NAMES = {
    3: "Frequência (GRUPO A)",
    5: "Lanche 4h (GRUPO A)",
    7: "Lanche 6h (GRUPO A)",
    10: "Refeição Dieta Enteral (A)",
    12: "Frequência (GRUPO B)",
    14: "Lanche 4h (GRUPO B)",
    16: "Lanche 6h (GRUPO B)",
}
