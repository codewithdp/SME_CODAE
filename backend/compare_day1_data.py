"""
Compare what Excel has vs what Azure DI extracted for day 1
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from app.excel_parser_custom import CustomExcelParser

excel_path = "/Users/writetodennis/dev/SME/019382.xlsm"

print("="*100)
print("EXCEL DATA FOR DAY 1 (Section 2)")
print("="*100)

excel_parser = CustomExcelParser()
excel_data = excel_parser.parse_file(excel_path)

day1_idx = 0  # Day 1 is index 0

print("\nINTEGRAL (11 fields):")
integral = excel_data.section2.integral[day1_idx]
print(f"  frequencia: {integral.frequencia}")
print(f"  lanche_4h: {integral.lanche_4h}")
print(f"  lanche_6h: {integral.lanche_6h}")
print(f"  refeicao: {integral.refeicao}")
print(f"  repeticao_refeicao: {integral.repeticao_refeicao}")
print(f"  sobremesa: {integral.sobremesa}")
print(f"  repeticao_sobremesa: {integral.repeticao_sobremesa}")
print(f"  refeicao_2a: {integral.refeicao_2a}")
print(f"  repeticao_refeicao_2a: {integral.repeticao_refeicao_2a}")
print(f"  sobremesa_2a: {integral.sobremesa_2a}")
print(f"  repeticao_sobremesa_2a: {integral.repeticao_sobremesa_2a}")

print("\nP1 / PRIMEIRO_PERIODO (7 fields):")
p1 = excel_data.section2.primeiro_periodo[day1_idx]
print(f"  frequencia: {p1.frequencia}")
print(f"  lanche_4h: {p1.lanche_4h}")
print(f"  lanche_6h: {p1.lanche_6h}")
print(f"  refeicao: {p1.refeicao}")
print(f"  repeticao_refeicao: {p1.repeticao_refeicao}")
print(f"  sobremesa: {p1.sobremesa}")
print(f"  repeticao_sobremesa: {p1.repeticao_sobremesa}")

print("\nINTERMEDIÁRIO (6 fields):")
inter = excel_data.section2.intermediario[day1_idx]
print(f"  frequencia: {inter.frequencia}")
print(f"  lanche_4h: {inter.lanche_4h}")
print(f"  refeicao: {inter.refeicao}")
print(f"  repeticao_refeicao: {inter.repeticao_refeicao}")
print(f"  sobremesa: {inter.sobremesa}")
print(f"  repeticao_sobremesa: {inter.repeticao_sobremesa}")

print("\nP3 / TERCEIRO_PERIODO (7 fields):")
p3 = excel_data.section2.terceiro_periodo[day1_idx]
print(f"  frequencia: {p3.frequencia}")
print(f"  lanche_4h: {p3.lanche_4h}")
print(f"  lanche_6h: {p3.lanche_6h}")
print(f"  refeicao: {p3.refeicao}")
print(f"  repeticao_refeicao: {p3.repeticao_refeicao}")
print(f"  sobremesa: {p3.sobremesa}")
print(f"  repeticao_sobremesa: {p3.repeticao_sobremesa}")

print("\n" + "="*100)
print("AZURE DI EXTRACTED FOR DAY 1")
print("="*100)
print("From the debug output, Azure DI extracted:")
print("  Row 2 (day 1): ['1', '', '', '', '', '16', '', '16', '', '', '', '']")
print("\nSo Azure DI found:")
print("  Col 0: '1' (day number)")
print("  Col 5: '16'")
print("  Col 7: '16'")
print("\nAll other columns are empty in Azure DI's extraction.")
