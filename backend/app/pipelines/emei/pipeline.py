from typing import Dict
from ..base import ReconciliationPipeline
from .engine import CompletePositionalReconciliationEngine

class EMEIPipeline(ReconciliationPipeline):
    """
    Pipeline for EMEI (Escola Municipal de Educação Infantil) reconciliation.
    Uses the existing positional reconciliation logic.
    """
    
    def __init__(self):
        self.engine = CompletePositionalReconciliationEngine()
        
    def reconcile(self, pdf_path: str, excel_path: str) -> Dict:
        """
        Reconcile EMEI documents.
        """
        return self.engine.reconcile_all_sections(pdf_path, excel_path)
