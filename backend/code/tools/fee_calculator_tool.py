from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import re
import requests
from datetime import datetime


@tool 
def fee_calculator_tool(query: str) -> Dict[str, Any]:
    """
    Dynamic immigration fee calculator that handles complex scenarios.
    
    Args:
        query: Natural language query about immigration fees
               Examples: 
               - "naturalization for myself and wife and 2 children"
               - "H-1B application with premium processing"
               - "green card for family of 5"
               - "asylum application fees"
    
    Returns:
        Comprehensive fee breakdown with totals
    """
    
    try:
        # Parse the query to understand what's being asked
        parsed_query = parse_fee_query(query)
        
        # Get current USCIS fee schedule
        current_fees = get_current_uscis_fees()
        
        # Calculate fees based on parsed query
        fee_breakdown = calculate_comprehensive_fees(parsed_query, current_fees)
        
        return {
            "query": query,
            "parsed_requirements": parsed_query,
            "fee_breakdown": fee_breakdown,
            "total_cost": fee_breakdown.get("total", 0),
            "success": True,
            "last_updated": datetime.now().isoformat(),
            "disclaimer": "Fees are subject to change. Verify with USCIS before applying."
        }
        
    except Exception as e:
        return {
            "query": query,
            "success": False,
            "error": str(e),
            "fallback_message": "Unable to calculate exact fees. Please check USCIS.gov for current fee schedule."
        }


def parse_fee_query(query: str) -> Dict[str, Any]:
    """Parse natural language query to extract fee calculation requirements."""
    
    query_lower = query.lower()
    
    # Extract procedure type
    procedure_type = extract_procedure_type(query_lower)
    
    # Extract number of applicants and relationships
    applicants = extract_applicant_info(query_lower)
    
    # Extract additional services
    additional_services = extract_additional_services(query_lower)
    
    return {
        "procedure_type": procedure_type,
        "applicants": applicants,
        "additional_services": additional_services,
        "raw_query": query
    }


def extract_procedure_type(query: str) -> str:
    """Extract the type of immigration procedure from query."""
    
    procedure_patterns = {
        "naturalization": ["natural", "citizen", "n-400", "citizenship"],
        "green_card": ["green card", "permanent resident", "i-485", "adjustment of status"],
        "h1b": ["h-1b", "h1b", "work visa", "specialty occupation"],
        "opt": ["opt", "optional practical training", "i-765"],
        "f1": ["f-1", "f1", "student visa"],
        "asylum": ["asylum", "i-589", "refugee"],
        "family_petition": ["i-130", "family petition", "relative petition"],
        "k1_fiance": ["k-1", "k1", "fiance", "fiancé"],
        "tourist_visit": ["b-1", "b-2", "tourist", "visitor"],
        "extension": ["extend", "extension", "i-539"],
        "removal_defense": ["removal", "deportation", "immigration court"]
    }
    
    for procedure, keywords in procedure_patterns.items():
        if any(keyword in query for keyword in keywords):
            return procedure
    
    return "unknown_procedure"


def extract_applicant_info(query: str) -> Dict[str, Any]:
    """Extract information about number and types of applicants."""
    
    applicants = {
        "adults": 0,
        "children": 0,
        "total": 0,
        "relationships": []
    }
    
    # Count explicit mentions
    if "myself" in query or "me" in query or "i " in query:
        applicants["adults"] += 1
    
    # Spouse/partner
    spouse_terms = ["wife", "husband", "spouse", "partner"]
    if any(term in query for term in spouse_terms):
        applicants["adults"] += 1
        applicants["relationships"].append("spouse")
    
    # Children
    child_patterns = [
        r"(\d+)\s*child(?:ren)?",
        r"(\d+)\s*kids?",
        r"(\d+)\s*son",
        r"(\d+)\s*daughter"
    ]
    
    for pattern in child_patterns:
        match = re.search(pattern, query)
        if match:
            applicants["children"] += int(match.group(1))
    
    # Age specifications
    if "under 18" in query or "minor" in query:
        # Children under 18 often have different fee structures
        applicants["children_under_18"] = True
    
    # Family size extraction
    family_patterns = [
        r"family of (\d+)",
        r"(\d+) people",
        r"(\d+) person",
        r"group of (\d+)"
    ]
    
    for pattern in family_patterns:
        match = re.search(pattern, query)
        if match:
            total = int(match.group(1))
            applicants["total"] = total
            # If we don't have specific breakdowns, assume adults
            if applicants["adults"] + applicants["children"] == 0:
                applicants["adults"] = total
    
    applicants["total"] = applicants["adults"] + applicants["children"]
    
    return applicants


def extract_additional_services(query: str) -> List[str]:
    """Extract additional services that affect fees."""
    
    services = []
    
    service_patterns = {
        "premium_processing": ["premium processing", "expedited", "fast track"],
        "biometric_services": ["biometric", "fingerprint"],
        "document_replacement": ["replace", "replacement", "lost document"],
        "fee_waiver": ["fee waiver", "waiver", "reduced fee", "financial hardship"],
        "legal_representation": ["attorney", "lawyer", "legal help"]
    }
    
    for service, keywords in service_patterns.items():
        if any(keyword in query for keyword in keywords):
            services.append(service)
    
    return services


def get_current_uscis_fees() -> Dict[str, Any]:
    """
    Get current USCIS fees. In production, this would scrape USCIS website
    or use their API. For now, returns comprehensive fee database.
    """
    
    # This would ideally fetch from USCIS.gov/fees
    # For now, comprehensive static database with realistic current fees
    
    return {
        "naturalization": {
            "base_fee": 725,
            "biometric_fee": 85,
            "total_per_person": 810,
            "children_under_18_exemption": True,
            "military_exemption": True
        },
        "green_card": {
            "i485_fee": 1140,
            "biometric_fee": 85,
            "total_per_person": 1225,
            "family_based_same_petition": False
        },
        "h1b": {
            "i129_base_fee": 460,
            "fraud_prevention_fee": 500,
            "acwia_fee": 750,  # For employers with <26 employees
            "premium_processing": 2500,
            "total_minimum": 1710
        },
        "opt": {
            "i765_fee": 410,
            "biometric_fee": 85,
            "total_per_person": 495
        },
        "asylum": {
            "i589_fee": 0,  # Currently no fee for asylum applications
            "work_authorization": 0,  # No fee for asylum-based work auth
            "biometric_fee": 85
        },
        "family_petition": {
            "i130_fee": 535,
            "biometric_fee": 85,
            "total_per_petition": 620
        },
        "extension": {
            "i539_fee": 370,
            "biometric_fee": 85,
            "total_per_person": 455
        },
        "premium_processing": {
            "general_fee": 2500,
            "available_for": ["h1b", "green_card", "extension"]
        },
        "fee_waivers": {
            "available_for": ["naturalization", "green_card", "asylum"],
            "income_threshold": "150% of federal poverty guidelines"
        }
    }


def calculate_comprehensive_fees(parsed_query: Dict[str, Any], fee_schedule: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate comprehensive fee breakdown based on parsed query."""
    
    procedure = parsed_query["procedure_type"]
    applicants = parsed_query["applicants"]
    services = parsed_query["additional_services"]
    
    breakdown = {
        "procedure": procedure,
        "applicant_fees": [],
        "additional_services": [],
        "total": 0,
        "savings": [],
        "notes": []
    }
    
    if procedure == "naturalization":
        return calculate_naturalization_fees(applicants, services, fee_schedule, breakdown)
    elif procedure == "green_card":
        return calculate_green_card_fees(applicants, services, fee_schedule, breakdown)
    elif procedure == "h1b":
        return calculate_h1b_fees(applicants, services, fee_schedule, breakdown)
    elif procedure == "asylum":
        return calculate_asylum_fees(applicants, services, fee_schedule, breakdown)
    else:
        breakdown["error"] = f"Fee calculation not yet implemented for {procedure}"
        breakdown["total"] = 0
        
    return breakdown


def calculate_naturalization_fees(applicants: Dict, services: List, fees: Dict, breakdown: Dict) -> Dict:
    """Calculate naturalization fees with family considerations."""
    
    nat_fees = fees["naturalization"]
    
    # Adults pay full fee
    adult_cost = applicants["adults"] * nat_fees["total_per_person"]
    breakdown["applicant_fees"].append({
        "type": "Adults",
        "count": applicants["adults"],
        "cost_per_person": nat_fees["total_per_person"],
        "subtotal": adult_cost
    })
    
    # Children under 18 are free
    if applicants["children"] > 0:
        breakdown["applicant_fees"].append({
            "type": "Children under 18",
            "count": applicants["children"],
            "cost_per_person": 0,
            "subtotal": 0
        })
        breakdown["savings"].append(f"${applicants['children'] * nat_fees['total_per_person']} saved - children under 18 exempt")
    
    breakdown["total"] = adult_cost
    breakdown["notes"].append("Children under 18 applying with parents are exempt from fees")
    
    return breakdown


def calculate_green_card_fees(applicants: Dict, services: List, fees: Dict, breakdown: Dict) -> Dict:
    """Calculate green card fees."""
    
    gc_fees = fees["green_card"]
    total_people = applicants["total"]
    
    total_cost = total_people * gc_fees["total_per_person"]
    
    breakdown["applicant_fees"].append({
        "type": "Green Card Applications",
        "count": total_people,
        "cost_per_person": gc_fees["total_per_person"],
        "subtotal": total_cost
    })
    
    breakdown["total"] = total_cost
    
    return breakdown


def calculate_h1b_fees(applicants: Dict, services: List, fees: Dict, breakdown: Dict) -> Dict:
    """Calculate H-1B fees with employer considerations."""
    
    h1b_fees = fees["h1b"]
    
    # H-1B is typically per petition, not per person
    base_cost = h1b_fees["total_minimum"]
    
    breakdown["applicant_fees"].append({
        "type": "H-1B Petition",
        "count": 1,
        "cost_per_person": base_cost,
        "subtotal": base_cost
    })
    
    if "premium_processing" in services:
        premium_cost = fees["premium_processing"]["general_fee"]
        breakdown["additional_services"].append({
            "service": "Premium Processing",
            "cost": premium_cost
        })
        base_cost += premium_cost
    
    breakdown["total"] = base_cost
    breakdown["notes"].append("H-1B fees are typically paid by employer")
    
    return breakdown


def calculate_asylum_fees(applicants: Dict, services: List, fees: Dict, breakdown: Dict) -> Dict:
    """Calculate asylum fees (currently free)."""
    
    asylum_fees = fees["asylum"]
    
    breakdown["applicant_fees"].append({
        "type": "Asylum Application (I-589)",
        "count": applicants["total"],
        "cost_per_person": asylum_fees["i589_fee"],
        "subtotal": 0
    })
    
    breakdown["total"] = 0
    breakdown["notes"].append("Asylum applications are currently free of charge")
    
    return breakdown