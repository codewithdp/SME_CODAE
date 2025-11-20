from abc import ABC, abstractmethod
from typing import Dict

class ReconciliationPipeline(ABC):
    """
    Abstract base class for reconciliation pipelines.
    Each school type (EMEI, CEI) will implement this interface.
    """
    
    @abstractmethod
    def reconcile(self, pdf_path: str, excel_path: str) -> Dict:
        """
        Process and reconcile the given files.
        
        Args:
            pdf_path: Absolute path to the PDF file
            excel_path: Absolute path to the Excel file
            
        Returns:
            Dictionary containing the reconciliation results
        """
        pass
