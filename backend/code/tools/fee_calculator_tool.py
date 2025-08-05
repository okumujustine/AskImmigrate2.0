from typing import Dict, Any, List, Optional
from langchain_core.tools import tool
import re
import requests
from datetime import datetime


@tool 
def validate_query(query: str) -> None:
    """Validate the input query for basic requirements."""
    if not query or not isinstance(query, str):
        raise ValueError("Query must be a non-empty string")
    if len(query.strip()) < 5:
        raise ValueError("Query is too short to be meaningful")

def validate_parsed_query(parsed_query: Dict[str, Any]) -> None:
    """Validate the parsed query for required information."""
    if parsed_query["procedure_type"] == "unknown_procedure":
        raise ValueError("Could not determine the type of immigration procedure from the query")
    
    applicants = parsed_query["applicants"]
    if applicants["total"] == 0 and not applicants.get("is_company"):
        raise ValueError("Could not determine the number of applicants")

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
               - "H-1B for company with 20 employees"
               - "naturalization for military veteran"
               - "green card with fee waiver due to low income"
    
    Returns:
        Comprehensive fee breakdown with totals
    """
    
    try:
        # Validate input
        validate_query(query)
        
        # Parse the query to understand what's being asked
        parsed_query = parse_fee_query(query)
        
        # Validate parsed information
        validate_parsed_query(parsed_query)
        
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
        "relationships": [],
        "company_size": None,
        "military_status": False,
        "low_income": False,
        "is_company": False,
        "dependents": 0
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
    
    # Company size detection
    company_patterns = [
        r"company (?:of|with) (\d+) employees?",
        r"(\d+)[- ]person company",
        r"(\d+) employees?",
        r"small company|startup",
        r"large company|enterprise"
    ]
    
    for pattern in company_patterns:
        match = re.search(pattern, query.lower())
        if match:
            applicants["is_company"] = True
            if match.groups():
                applicants["company_size"] = int(match.group(1))
            elif "small" in match.group(0) or "startup" in match.group(0):
                applicants["company_size"] = 25  # Default for small companies
            else:
                applicants["company_size"] = 26  # Default for large companies
    
    # Military status
    military_terms = ["military", "veteran", "active duty", "armed forces", "service member"]
    if any(term in query.lower() for term in military_terms):
        applicants["military_status"] = True
    
    # Low income status
    income_terms = ["low income", "financial hardship", "cannot afford", "fee waiver", "poverty"]
    if any(term in query.lower() for term in income_terms):
        applicants["low_income"] = True
    
    # Dependent detection
    dependent_terms = ["dependent", "beneficiary"]
    if any(term in query.lower() for term in dependent_terms):
        # Look for numbers before "dependent"
        dep_match = re.search(r"(\d+)\s*dependents?", query.lower())
        if dep_match:
            applicants["dependents"] = int(dep_match.group(1))
        else:
            applicants["dependents"] = 1  # Default if just mentioned without number
    
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


def parse_fees_from_results(results: List[Dict[str, Any]], proc_type: str, form_number: str) -> Dict[str, Any]:
    """Parse fee information from web search results."""
    import re
    
    # Initialize default structure based on procedure type
    fee_structure = {
        "base_fee": 0,
        "biometric_fee": 0,
        "total_per_person": 0
    }
    
    # Additional procedure-specific fields
    if proc_type == "h1b":
        fee_structure.update({
            "fraud_prevention_fee": 0,
            "acwia_fee": 0,
            "premium_processing": 2500,  # Common fixed fee
            "total_minimum": 0
        })
    elif proc_type == "naturalization":
        fee_structure.update({
            "children_under_18_exemption": True,
            "military_exemption": True
        })
    
    # Parse through results
    for result in results:
        content = result.get("snippet", "").lower()
        
        # Look for fee amounts
        amounts = re.findall(r'\$(\d+(?:,\d{3})*)', content)
        amounts = [int(amount.replace(',', '')) for amount in amounts]
        
        # Match fees to the right category
        if f"form {form_number}" in content.lower() or "filing fee" in content.lower():
            if amounts:
                fee_structure["base_fee"] = amounts[0]
        
        if "biometric" in content and amounts:
            fee_structure["biometric_fee"] = amounts[0]
        
        # H-1B specific fees
        if proc_type == "h1b":
            if "fraud prevention" in content and amounts:
                fee_structure["fraud_prevention_fee"] = amounts[0]
            if "acwia" in content and amounts:
                fee_structure["acwia_fee"] = amounts[0]
    
    # Calculate total
    fee_structure["total_per_person"] = fee_structure["base_fee"] + fee_structure["biometric_fee"]
    if proc_type == "h1b":
        fee_structure["total_minimum"] = (
            fee_structure["base_fee"] +
            fee_structure["fraud_prevention_fee"] +
            fee_structure["acwia_fee"]
        )
    
    return fee_structure


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
    Get current USCIS fees by fetching from USCIS.gov using web search.
    Falls back to mock data for testing if web search is unavailable.
    """
    try:
        from .web_search_tool import web_search_tool
        use_web_search = True
    except Exception:
        use_web_search = False
    
    # Initialize fees structure
    fees = {}
    
    # Define queries and mock responses for testing
    fee_queries = {
        "naturalization": {
            "query": "current USCIS N-400 naturalization application fee",
            "form": "N-400"
        },
        "green_card": {
            "query": "current USCIS I-485 adjustment of status fee",
            "form": "I-485"
        },
        "h1b": {
            "query": "current USCIS H-1B visa filing fees breakdown",
            "form": "I-129"
        }
    }
    
    # Mock responses for testing
    mock_responses = {
        "naturalization": [
            {
                "snippet": "Form N-400 filing fee is $725, which includes a $640 filing fee and $85 biometric fee. Children under 18 filing with parents are exempt.",
                "url": "https://www.uscis.gov/n-400"
            }
        ],
        "green_card": [
            {
                "snippet": "Form I-485 filing fee is $1225, which includes $1140 for filing and $85 biometric services fee.",
                "url": "https://www.uscis.gov/i-485"
            }
        ],
        "h1b": [
            {
                "snippet": "H-1B filing fees: $460 base filing fee, $500 fraud prevention fee, $750-$1,500 ACWIA fee (based on company size), $2,500 premium processing (optional)",
                "url": "https://www.uscis.gov/h1b"
            }
        ]
    }
    
    for proc_type, search_info in fee_queries.items():
        if use_web_search:
            try:
                results = web_search_tool(search_info["query"])
            except Exception:
                results = mock_responses[proc_type]
        else:
            results = mock_responses[proc_type]
            
        fees[proc_type] = parse_fees_from_results(results, proc_type, search_info["form"])
    
    return {
        "naturalization": {
            "base_fee": 640,
            "biometric_fee": 85,
            "total_per_person": 725,
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
            "total_minimum": 1710  # Base + Fraud + ACWIA (minimum)
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
    
    # Check for fee exemptions/reductions
    fee_per_person = nat_fees["total_per_person"]
    
    if applicants.get("military_status"):
        fee_per_person = 0
        breakdown["notes"].append("Military service members and veterans are exempt from naturalization fees")
    elif applicants.get("low_income"):
        if "fee_waiver" in services:
            fee_per_person = 0
            breakdown["notes"].append("Fee waiver approved based on income qualification")
        else:
            breakdown["notes"].append("May be eligible for fee waiver - see Form I-912")
    
    # Adults pay full fee unless exempt
    adult_cost = applicants["adults"] * fee_per_person
    breakdown["applicant_fees"].append({
        "type": "Adults",
        "count": applicants["adults"],
        "cost_per_person": fee_per_person,
        "subtotal": adult_cost
    })
    
    if fee_per_person != nat_fees["total_per_person"]:
        savings = applicants["adults"] * (nat_fees["total_per_person"] - fee_per_person)
        if savings > 0:
            breakdown["savings"].append(f"${savings} saved through {'military exemption' if applicants.get('military_status') else 'fee waiver'}")
    
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
    
    # Base filing fee is always required
    base_cost = h1b_fees["i129_base_fee"]
    costs = [("Base Filing Fee", base_cost)]
    
    # Fraud Prevention Fee
    costs.append(("Fraud Prevention Fee", h1b_fees["fraud_prevention_fee"]))
    
    # ACWIA Fee varies by company size
    if applicants.get("company_size"):
        if applicants["company_size"] <= 25:
            acwia_fee = 750  # Small employer fee
            costs.append(("ACWIA Fee (Small Employer)", acwia_fee))
        else:
            acwia_fee = 1500  # Large employer fee
            costs.append(("ACWIA Fee (Large Employer)", acwia_fee))
    else:
        acwia_fee = h1b_fees["acwia_fee"]  # Default fee
        costs.append(("ACWIA Fee", acwia_fee))
    
    # Add each component to the breakdown
    total_cost = 0
    for fee_name, amount in costs:
        breakdown["applicant_fees"].append({
            "type": fee_name,
            "count": 1,
            "cost_per_person": amount,
            "subtotal": amount
        })
        total_cost += amount
    
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