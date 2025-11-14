# Section 2 - Excel Column Mapping

## Complete Structure (36 fields + Dia)

### Column 1: Day
- **Col C (3)**: Dia (Day number 1-31)

### INTEGRAL Period (11 fields) - Cols 5-17
- **Col E (5)**: Frequência
- **Col G (7)**: Lanche 4h
- **Col H (8)**: Lanche 6h
- **Col J (10)**: Refeição
- **Col K (11)**: Repetição da refeição
- **Col L (12)**: Sobremesa
- **Col M (13)**: Repetição da sobremesa
- **Col N (14)**: 2ª Refeição
- **Col O (15)**: Repetição da 2ª refeição
- **Col P (16)**: 2ª Sobremesa
- **Col Q (17)**: 2ª Repetição da sobremesa

### 1º PERÍODO (7 fields) - Cols 18, 20, 21, 24, 28, 31, 35
- **Col R (18)**: Frequência
- **Col T (20)**: Lanche 4h ← MISSING!
- **Col U (21)**: Lanche 6h
- **Col X (24)**: Refeição
- **Col AB (28)**: Repetição da refeição
- **Col AE (31)**: Sobremesa
- **Col AI (35)**: Repetição da sobremesa

### INTERMEDIÁRIO (6 fields) - Cols 37, 38, 39, 41, 43, 45
Based on header row 24, appears to have duplicates. Need to identify primary columns:
- **Col AK (37)**: Frequência
- **Col AL (38)**: Lanche 4h
- **Col AM or AN (39/40)**: Refeição (need to verify which)
- **Col AO or AP (41/42)**: Repetição refeição
- **Col AQ or AR (43/44)**: Sobremesa
- **Col AS or AT (45/46)**: Repetição sobremesa

### 3º PERÍODO (7 fields) - Cols 47, 49, 51, 57, 61, 62, 69
- **Col AU (47)**: Frequência
- **Col AW (49)**: Lanche 4h ← MISSING!
- **Col AY (51)**: Lanche 6h
- **Col BE (57)**: Refeição
- **Col BI (61)**: Repetição da refeição
- **Col BJ (62)**: Sobremesa
- **Col BQ (69)**: Repetição da sobremesa

### Doce Checkboxes (4 fields) - Cols 70, 73, 74, 75
- **Col BR (70)**: INTEGRAL
- **Col BU (73)**: 1º PERÍODO
- **Col BV (74)**: INTERMEDIÁRIO
- **Col BW (75)**: 3º PERÍODO

## Data Range
- **Rows 28-58**: Days 1-31
- **Row 60 or 61**: TOTAL row (need to verify)

## Notes
- Excel has some merged cells in headers
- Some columns appear duplicated (INTERMEDIÁRIO section)
- Need to verify INTERMEDIÁRIO columns by checking actual data
- Need to find TOTAL row location
