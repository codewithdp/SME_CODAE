from typing import Dict, Type
from .base import ReconciliationPipeline
from .emei.pipeline import EMEIPipeline
from .cei.pipeline import CEIPipeline

# Registry of available pipelines
PIPELINES: Dict[str, Type[ReconciliationPipeline]] = {
    "emei": EMEIPipeline,
    "model_a": EMEIPipeline,  # Alias for backward compatibility
    "cei": CEIPipeline,
}

def get_pipeline(model_type: str = "emei") -> ReconciliationPipeline:
    """
    Factory function to get the appropriate reconciliation pipeline.
    
    Args:
        model_type: The type of document model (e.g., "emei", "cei")
        
    Returns:
        An instance of the requested ReconciliationPipeline
        
    Raises:
        ValueError: If the model_type is unknown
    """
    pipeline_class = PIPELINES.get(model_type.lower())
    
    if not pipeline_class:
        valid_models = ", ".join(PIPELINES.keys())
        raise ValueError(f"Unknown model type: '{model_type}'. Valid models are: {valid_models}")
        
    return pipeline_class()
