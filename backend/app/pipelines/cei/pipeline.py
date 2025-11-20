from typing import Dict
from ..base import ReconciliationPipeline
from .engine import CEIReconciliationEngine

class CEIPipeline(ReconciliationPipeline):
    """
    Pipeline for CEI (Centro de Educação Infantil) reconciliation.
    """

    def __init__(self):
        self.engine = CEIReconciliationEngine()
        
    def reconcile(self, pdf_path: str, excel_path: str) -> Dict:
        """
        Reconcile CEI documents.
        """
        return self.engine.reconcile_all_sections(pdf_path, excel_path)
