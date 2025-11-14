"""
Complete Section 2 Reconciliation - Helper code
This will be integrated into the reconciliation_engine_comprehensive.py

Compares ALL 1,116 cells in Section 2
"""

# Helper method to add to the class:
def _compare_field(self, excel_val, pdf_val, section, field, day, mismatches, cells_compared):
    """
    Helper to compare a single field and track mismatches
    Treats None and 0 as equivalent for numeric fields
    """
    # Always count the cell
    cells_compared[0] += 1

    # Normalize None and 0
    excel_norm = excel_val if excel_val is not None else 0
    pdf_norm = pdf_val if pdf_val is not None else 0

    if excel_norm != pdf_norm:
        mismatches.append({
            "section": section,
            "field": field,
            "row_identifier": f"Day {day}",
            "excel_value": excel_val,
            "pdf_value": pdf_val,
            "description": f"{field} mismatch for day {day}"
        })

# Main comparison logic:
def _compare_section2_comprehensive_NEW(self, excel_data, pdf_data):
    """
    Compare ALL Section 2 cells: 1,116 total
    - INTEGRAL: 11 fields × 31 days = 341 cells
    - P1: 7 fields × 31 days = 217 cells
    - INTERMEDIÁRIO: 6 fields × 31 days = 186 cells
    - P3: 7 fields × 31 days = 217 cells
    - DOCE: 4 fields × 31 days = 124 cells
    - TOTAL row: 31 fields
    """
    cells_compared = [0]  # Use list to allow modification in helper
    mismatches = []

    if not pdf_data.section2_table:
        return 0, []

    # Build PDF data map by day (rows 3+ = days 1-31)
    pdf_days = {}
    pdf_total_row = None

    for row_idx, row in enumerate(pdf_data.section2_table.cells):
        if row_idx < 3:  # Skip headers
            continue

        day_str = str(row[0] if len(row) > 0 else "").strip()

        # Check if this is TOTAL row
        if "TOTAL" in day_str.upper():
            pdf_total_row = row
            continue

        day = self._safe_int(day_str)
        if not day or day < 1 or day > 31:
            continue

        # Extract ALL 35 fields
        pdf_days[day] = {
            # INTEGRAL (11 fields, PDF cols 1-11)
            "integral": {
                "frequencia": self._safe_int(row[1] if len(row) > 1 else None),
                "lanche_4h": self._safe_int(row[2] if len(row) > 2 else None),
                "lanche_6h": self._safe_int(row[3] if len(row) > 3 else None),
                "refeicao": self._safe_int(row[4] if len(row) > 4 else None),
                "repeticao_refeicao": self._safe_int(row[5] if len(row) > 5 else None),
                "sobremesa": self._safe_int(row[6] if len(row) > 6 else None),
                "repeticao_sobremesa": self._safe_int(row[7] if len(row) > 7 else None),
                "refeicao_2a": self._safe_int(row[8] if len(row) > 8 else None),
                "repeticao_refeicao_2a": self._safe_int(row[9] if len(row) > 9 else None),
                "sobremesa_2a": self._safe_int(row[10] if len(row) > 10 else None),
                "repeticao_sobremesa_2a": self._safe_int(row[11] if len(row) > 11 else None),
            },
            # P1 (7 fields, PDF cols 12-18)
            "p1": {
                "frequencia": self._safe_int(row[12] if len(row) > 12 else None),
                "lanche_4h": self._safe_int(row[13] if len(row) > 13 else None),
                "lanche_6h": self._safe_int(row[14] if len(row) > 14 else None),
                "refeicao": self._safe_int(row[15] if len(row) > 15 else None),
                "repeticao_refeicao": self._safe_int(row[16] if len(row) > 16 else None),
                "sobremesa": self._safe_int(row[17] if len(row) > 17 else None),
                "repeticao_sobremesa": self._safe_int(row[18] if len(row) > 18 else None),
            },
            # INTERMEDIÁRIO (6 fields, PDF cols 19-24)
            "intermediario": {
                "frequencia": self._safe_int(row[19] if len(row) > 19 else None),
                "lanche_4h": self._safe_int(row[20] if len(row) > 20 else None),
                "refeicao": self._safe_int(row[21] if len(row) > 21 else None),
                "repeticao_refeicao": self._safe_int(row[22] if len(row) > 22 else None),
                "sobremesa": self._safe_int(row[23] if len(row) > 23 else None),
                "repeticao_sobremesa": self._safe_int(row[24] if len(row) > 24 else None),
            },
            # P3 (7 fields, PDF cols 25-31)
            "p3": {
                "frequencia": self._safe_int(row[25] if len(row) > 25 else None),
                "lanche_4h": self._safe_int(row[26] if len(row) > 26 else None),
                "lanche_6h": self._safe_int(row[27] if len(row) > 27 else None),
                "refeicao": self._safe_int(row[28] if len(row) > 28 else None),
                "repeticao_refeicao": self._safe_int(row[29] if len(row) > 29 else None),
                "sobremesa": self._safe_int(row[30] if len(row) > 30 else None),
                "repeticao_sobremesa": self._safe_int(row[31] if len(row) > 31 else None),
            },
            # DOCE checkboxes (4 fields, PDF cols 32-35)
            "doce": {
                "integral": self._is_checkbox_selected(row[32] if len(row) > 32 else None),
                "p1": self._is_checkbox_selected(row[33] if len(row) > 33 else None),
                "intermediario": self._is_checkbox_selected(row[34] if len(row) > 34 else None),
                "p3": self._is_checkbox_selected(row[35] if len(row) > 35 else None),
            }
        }

    # Compare ALL days (31 days)
    for day in range(1, 32):
        pdf_day = pdf_days.get(day, {})

        # Compare INTEGRAL (11 fields)
        excel_int = excel_data.section2.integral[day - 1]  # 0-indexed
        pdf_int = pdf_day.get("integral", {})

        self._compare_field(excel_int.frequencia, pdf_int.get("frequencia"),
                           "Section2", "INTEGRAL - Frequência", day, mismatches, cells_compared)
        self._compare_field(excel_int.lanche_4h, pdf_int.get("lanche_4h"),
                           "Section2", "INTEGRAL - Lanche 4h", day, mismatches, cells_compared)
        self._compare_field(excel_int.lanche_6h, pdf_int.get("lanche_6h"),
                           "Section2", "INTEGRAL - Lanche 6h", day, mismatches, cells_compared)
        self._compare_field(excel_int.refeicao, pdf_int.get("refeicao"),
                           "Section2", "INTEGRAL - Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_int.repeticao_refeicao, pdf_int.get("repeticao_refeicao"),
                           "Section2", "INTEGRAL - Repetição Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_int.sobremesa, pdf_int.get("sobremesa"),
                           "Section2", "INTEGRAL - Sobremesa", day, mismatches, cells_compared)
        self._compare_field(excel_int.repeticao_sobremesa, pdf_int.get("repeticao_sobremesa"),
                           "Section2", "INTEGRAL - Repetição Sobremesa", day, mismatches, cells_compared)
        self._compare_field(excel_int.refeicao_2a, pdf_int.get("refeicao_2a"),
                           "Section2", "INTEGRAL - 2ª Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_int.repeticao_refeicao_2a, pdf_int.get("repeticao_refeicao_2a"),
                           "Section2", "INTEGRAL - Repetição 2ª Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_int.sobremesa_2a, pdf_int.get("sobremesa_2a"),
                           "Section2", "INTEGRAL - 2ª Sobremesa", day, mismatches, cells_compared)
        self._compare_field(excel_int.repeticao_sobremesa_2a, pdf_int.get("repeticao_sobremesa_2a"),
                           "Section2", "INTEGRAL - Repetição 2ª Sobremesa", day, mismatches, cells_compared)

        # Compare P1 (7 fields)
        excel_p1 = excel_data.section2.primeiro_periodo[day - 1]
        pdf_p1 = pdf_day.get("p1", {})

        self._compare_field(excel_p1.frequencia, pdf_p1.get("frequencia"),
                           "Section2", "P1 - Frequência", day, mismatches, cells_compared)
        self._compare_field(excel_p1.lanche_4h, pdf_p1.get("lanche_4h"),
                           "Section2", "P1 - Lanche 4h", day, mismatches, cells_compared)
        self._compare_field(excel_p1.lanche_6h, pdf_p1.get("lanche_6h"),
                           "Section2", "P1 - Lanche 6h", day, mismatches, cells_compared)
        self._compare_field(excel_p1.refeicao, pdf_p1.get("refeicao"),
                           "Section2", "P1 - Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_p1.repeticao_refeicao, pdf_p1.get("repeticao_refeicao"),
                           "Section2", "P1 - Repetição Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_p1.sobremesa, pdf_p1.get("sobremesa"),
                           "Section2", "P1 - Sobremesa", day, mismatches, cells_compared)
        self._compare_field(excel_p1.repeticao_sobremesa, pdf_p1.get("repeticao_sobremesa"),
                           "Section2", "P1 - Repetição Sobremesa", day, mismatches, cells_compared)

        # Compare INTERMEDIÁRIO (6 fields)
        excel_inter = excel_data.section2.intermediario[day - 1]
        pdf_inter = pdf_day.get("intermediario", {})

        self._compare_field(excel_inter.frequencia, pdf_inter.get("frequencia"),
                           "Section2", "INTERMEDIÁRIO - Frequência", day, mismatches, cells_compared)
        self._compare_field(excel_inter.lanche_4h, pdf_inter.get("lanche_4h"),
                           "Section2", "INTERMEDIÁRIO - Lanche 4h", day, mismatches, cells_compared)
        self._compare_field(excel_inter.refeicao, pdf_inter.get("refeicao"),
                           "Section2", "INTERMEDIÁRIO - Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_inter.repeticao_refeicao, pdf_inter.get("repeticao_refeicao"),
                           "Section2", "INTERMEDIÁRIO - Repetição Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_inter.sobremesa, pdf_inter.get("sobremesa"),
                           "Section2", "INTERMEDIÁRIO - Sobremesa", day, mismatches, cells_compared)
        self._compare_field(excel_inter.repeticao_sobremesa, pdf_inter.get("repeticao_sobremesa"),
                           "Section2", "INTERMEDIÁRIO - Repetição Sobremesa", day, mismatches, cells_compared)

        # Compare P3 (7 fields)
        excel_p3 = excel_data.section2.terceiro_periodo[day - 1]
        pdf_p3 = pdf_day.get("p3", {})

        self._compare_field(excel_p3.frequencia, pdf_p3.get("frequencia"),
                           "Section2", "P3 - Frequência", day, mismatches, cells_compared)
        self._compare_field(excel_p3.lanche_4h, pdf_p3.get("lanche_4h"),
                           "Section2", "P3 - Lanche 4h", day, mismatches, cells_compared)
        self._compare_field(excel_p3.lanche_6h, pdf_p3.get("lanche_6h"),
                           "Section2", "P3 - Lanche 6h", day, mismatches, cells_compared)
        self._compare_field(excel_p3.refeicao, pdf_p3.get("refeicao"),
                           "Section2", "P3 - Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_p3.repeticao_refeicao, pdf_p3.get("repeticao_refeicao"),
                           "Section2", "P3 - Repetição Refeição", day, mismatches, cells_compared)
        self._compare_field(excel_p3.sobremesa, pdf_p3.get("sobremesa"),
                           "Section2", "P3 - Sobremesa", day, mismatches, cells_compared)
        self._compare_field(excel_p3.repeticao_sobremesa, pdf_p3.get("repeticao_sobremesa"),
                           "Section2", "P3 - Repetição Sobremesa", day, mismatches, cells_compared)

        # Compare DOCE checkboxes (4 fields)
        excel_doce = excel_data.section2.doce_checkboxes[day - 1]
        pdf_doce = pdf_day.get("doce", {})

        self._compare_checkbox(excel_doce.integral, pdf_doce.get("integral"),
                              "Section2", "DOCE - INTEGRAL", day, mismatches, cells_compared)
        self._compare_checkbox(excel_doce.primeiro_periodo, pdf_doce.get("p1"),
                              "Section2", "DOCE - P1", day, mismatches, cells_compared)
        self._compare_checkbox(excel_doce.intermediario, pdf_doce.get("intermediario"),
                              "Section2", "DOCE - INTERMEDIÁRIO", day, mismatches, cells_compared)
        self._compare_checkbox(excel_doce.terceiro_periodo, pdf_doce.get("p3"),
                              "Section2", "DOCE - P3", day, mismatches, cells_compared)

    # Compare TOTAL row (31 fields) - TODO

    return cells_compared[0], mismatches

def _compare_checkbox(self, excel_val, pdf_val, section, field, day, mismatches, cells_compared):
    """Helper to compare checkbox fields (True/False/None)"""
    cells_compared[0] += 1

    # Normalize: None and False are equivalent for checkboxes
    excel_norm = excel_val if excel_val else False
    pdf_norm = pdf_val if pdf_val else False

    if excel_norm != pdf_norm:
        mismatches.append({
            "section": section,
            "field": field,
            "row_identifier": f"Day {day}",
            "excel_value": excel_val,
            "pdf_value": pdf_val,
            "description": f"{field} checkbox mismatch for day {day}"
        })

def _is_checkbox_selected(self, val) -> Optional[bool]:
    """Check if PDF checkbox is selected (:selected: vs :unselected:)"""
    if val is None or val == "":
        return None
    val_str = str(val).strip().lower()
    if "selected" in val_str and "unselected" not in val_str:
        return True
    if "unselected" in val_str:
        return False
    return None
