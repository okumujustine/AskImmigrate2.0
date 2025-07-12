from typing import Dict, Any
from langchain_core.tools import tool


@tool
def fee_calculator_tool(visa_type: str) -> Dict[str, Any]:
    """
    Calculate immigration fees for different visa types.
    
    Args:
        visa_type: The type of visa (e.g., "F-1", "H-1B", "Green Card")
        
    Returns:
        Dictionary containing fee information
    """
    fee_database = {
        "F-1": {
            "application_fee": 350.0,
            "sevis_fee": 350.0,
            "total": 700.0,
            "description": "F-1 student visa fees include application and SEVIS fees"
        },
        "H-1B": {
            "application_fee": 460.0,
            "anti_fraud_fee": 500.0,
            "total": 960.0,
            "description": "H-1B work visa basic fees (additional fees may apply)"
        },
        "J-1": {
            "application_fee": 160.0,
            "sevis_fee": 220.0,
            "total": 380.0,
            "description": "J-1 exchange visitor visa fees"
        },
        "Green Card": {
            "application_fee": 1140.0,
            "biometric_fee": 85.0,
            "total": 1225.0,
            "description": "Green card application fees"
        }
    }
    
    if visa_type in fee_database:
        return {
            "visa_type": visa_type,
            "fees": fee_database[visa_type],
            "success": True
        }
    else:
        return {
            "visa_type": visa_type,
            "fees": {},
            "success": False,
            "message": f"Fee information not available for {visa_type}"
        }