#!/usr/bin/env python3
"""
Fee Calculator Test Script - Comprehensive testing for immigration fee calculations
Usage: python backend/code/tests/test_fee_calculator.py
OR: python test_fee_calculator.py (from the tests directory)
"""

import sys
import os
from pathlib import Path
import json
from datetime import datetime

# CRITICAL FIX: Properly set up Python path regardless of where script is run from
def setup_python_path():
    """Set up Python path to find backend modules"""
    current_file = Path(__file__).resolve()
    
    # Find the project root (AskImmigrate2.0 directory)
    # Go up from backend/code/tests/ to project root
    project_root = current_file.parent.parent.parent
    
    # Alternative: look for the directory containing backend/
    search_path = current_file
    while search_path.parent != search_path:
        if (search_path / "backend").exists():
            project_root = search_path
            break
        search_path = search_path.parent
    else:
        # Fallback: assume we're 3 levels deep
        project_root = current_file.parent.parent.parent
    
    print(f"🔧 Project root detected: {project_root}")
    print(f"🔧 Backend path: {project_root / 'backend'}")
    print(f"🔧 Backend exists: {(project_root / 'backend').exists()}")
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        print(f"✅ Added to Python path: {project_root}")
    
    return project_root

# Set up path before any imports
project_root = setup_python_path()

# Now try imports with better error handling
try:
    from backend.code.tools.fee_calculator_tool import (
        fee_calculator_tool,
        parse_fee_query,
        extract_procedure_type,
        extract_applicant_info,
        extract_additional_services,
        get_current_uscis_fees,
        calculate_comprehensive_fees,
        calculate_naturalization_fees,
        calculate_green_card_fees,
        calculate_h1b_fees,
        calculate_asylum_fees
    )
    print("✅ Successfully imported fee calculator modules")
except ImportError as e:
    print(f"❌ Import error: {e}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Python path: {sys.path}")
    print(f"Looking for backend in: {project_root}")
    
    # List what's actually in the project root
    if project_root.exists():
        print(f"Contents of {project_root}:")
        for item in project_root.iterdir():
            print(f"  - {item.name}")
    
    sys.exit(1)

def test_procedure_type_extraction():
    """Test extraction of procedure types from various queries"""
    print("🧪 Testing Procedure Type Extraction")
    print("=" * 50)
    
    test_cases = [
        ("naturalization for myself and wife", "naturalization"),
        ("I want to apply for citizenship", "naturalization"),
        ("N-400 application cost", "naturalization"),
        ("green card for family of 5", "green_card"),
        ("adjustment of status fees", "green_card"),
        ("I-485 application", "green_card"),
        ("H-1B work visa cost", "h1b"),
        ("specialty occupation petition", "h1b"),
        ("OPT application fees", "opt"),
        ("I-765 work authorization", "opt"),
        ("asylum application cost", "asylum"),
        ("I-589 refugee application", "asylum"),
        ("family petition for brother", "family_petition"),
        ("I-130 relative petition", "family_petition"),
        ("extend my F-1 visa", "extension"),
        ("I-539 extension application", "extension"),
        ("some random immigration question", "unknown_procedure")
    ]
    
    for query, expected in test_cases:
        result = extract_procedure_type(query.lower())
        status = "✅" if result == expected else "❌"
        print(f"{status} '{query}' -> {result} (expected: {expected})")

def test_applicant_info_extraction():
    """Test extraction of applicant information from queries"""
    print("\n🧪 Testing Applicant Information Extraction")
    print("=" * 50)
    
    test_cases = [
        {
            "query": "naturalization for myself and wife",
            "expected": {"adults": 2, "children": 0, "total": 2, "relationships": ["spouse"]}
        },
        {
            "query": "green card for family of 5",
            "expected": {"adults": 5, "children": 0, "total": 5, "relationships": []}
        },
        {
            "query": "citizenship for me, my husband, and 2 children",
            "expected": {"adults": 2, "children": 2, "total": 4, "relationships": ["spouse"]}
        },
        {
            "query": "asylum application for myself",
            "expected": {"adults": 1, "children": 0, "total": 1, "relationships": []}
        },
        {
            "query": "H-1B for group of 3 people",
            "expected": {"adults": 3, "children": 0, "total": 3, "relationships": []}
        },
        {
            "query": "extension for me and 1 child under 18",
            "expected": {"adults": 1, "children": 1, "total": 2, "relationships": []}
        }
    ]
    
    for test_case in test_cases:
        query = test_case["query"]
        expected = test_case["expected"]
        
        result = extract_applicant_info(query.lower())
        
        # Check key fields
        checks = []
        for key in ["adults", "children", "total"]:
            if key in expected:
                actual = result.get(key, 0)
                expected_val = expected[key]
                checks.append(actual == expected_val)
        
        # Check relationships
        if "relationships" in expected:
            actual_rels = result.get("relationships", [])
            expected_rels = expected["relationships"]
            checks.append(set(actual_rels) == set(expected_rels))
        
        status = "✅" if all(checks) else "❌"
        print(f"{status} '{query}'")
        print(f"    Expected: {expected}")
        print(f"    Actual:   {result}")

def test_additional_services_extraction():
    """Test extraction of additional services"""
    print("\n🧪 Testing Additional Services Extraction")
    print("=" * 50)
    
    test_cases = [
        ("H-1B with premium processing", ["premium_processing"]),
        ("expedited naturalization application", ["premium_processing"]),
        ("green card with biometric services", ["biometric_services"]),
        ("replace lost green card", ["document_replacement"]),
        ("citizenship with fee waiver due to financial hardship", ["fee_waiver"]),
        ("asylum with attorney help", ["legal_representation"]),
        ("H-1B premium processing with lawyer", ["premium_processing", "legal_representation"]),
        ("standard naturalization application", [])
    ]
    
    for query, expected in test_cases:
        result = extract_additional_services(query.lower())
        status = "✅" if set(result) == set(expected) else "❌"
        print(f"{status} '{query}'")
        print(f"    Expected: {expected}")
        print(f"    Actual:   {result}")

def test_query_parsing():
    """Test complete query parsing functionality"""
    print("\n🧪 Testing Complete Query Parsing")
    print("=" * 50)
    
    test_queries = [
        "naturalization for myself and wife and 2 children",
        "H-1B application with premium processing",
        "green card for family of 5",
        "asylum application fees",
        "extend F-1 visa for me and spouse",
        "citizenship with fee waiver"
    ]
    
    for query in test_queries:
        print(f"\nParsing: '{query}'")
        try:
            result = parse_fee_query(query)
            print(f"  ✅ Procedure: {result['procedure_type']}")
            print(f"  ✅ Applicants: {result['applicants']['total']} total")
            print(f"  ✅ Services: {result['additional_services']}")
        except Exception as e:
            print(f"  ❌ Failed: {e}")

def test_fee_calculations():
    """Test comprehensive fee calculations for different scenarios"""
    print("\n🧪 Testing Fee Calculations")
    print("=" * 50)
    
    test_scenarios = [
        {
            "description": "Single adult naturalization",
            "query": "naturalization for myself",
            "expected_min": 800,  # Approximate expected minimum
            "expected_max": 900
        },
        {
            "description": "Family naturalization (2 adults, 2 children)",
            "query": "citizenship for me, my wife, and 2 children",
            "expected_min": 1600,  # 2 adults * ~810
            "expected_max": 1700
        },
        {
            "description": "H-1B with premium processing",
            "query": "H-1B application with premium processing",
            "expected_min": 4000,  # Base + premium
            "expected_max": 5000
        },
        {
            "description": "Green card for family of 3",
            "query": "green card for family of 3",
            "expected_min": 3600,  # 3 * ~1225
            "expected_max": 3800
        },
        {
            "description": "Asylum application",
            "query": "asylum application for myself",
            "expected_min": 0,  # Should be free
            "expected_max": 100  # Maybe biometric fee
        }
    ]
    
    for scenario in test_scenarios:
        print(f"\nTesting: {scenario['description']}")
        print(f"Query: '{scenario['query']}'")
        
        try:
            result = fee_calculator_tool(scenario['query'])
            
            if result.get('success', False):
                total_cost = result.get('total_cost', 0)
                expected_min = scenario['expected_min']
                expected_max = scenario['expected_max']
                
                if expected_min <= total_cost <= expected_max:
                    print(f"  ✅ Cost: ${total_cost} (within expected range ${expected_min}-${expected_max})")
                else:
                    print(f"  ⚠️  Cost: ${total_cost} (outside expected range ${expected_min}-${expected_max})")
                
                # Show breakdown
                if 'fee_breakdown' in result:
                    breakdown = result['fee_breakdown']
                    if 'applicant_fees' in breakdown:
                        for fee in breakdown['applicant_fees']:
                            print(f"    - {fee['type']}: {fee['count']} x ${fee['cost_per_person']} = ${fee['subtotal']}")
                    
                    if 'additional_services' in breakdown:
                        for service in breakdown['additional_services']:
                            print(f"    - {service['service']}: ${service['cost']}")
                
            else:
                print(f"  ❌ Failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Exception: {e}")

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n🧪 Testing Edge Cases and Error Handling")
    print("=" * 50)
    
    edge_cases = [
        "",  # Empty query
        "completely unrelated question about weather",  # Non-immigration query
        "immigration question but no specific procedure",  # Vague query
        "naturalization for 0 people",  # Zero applicants
        "H-1B for 100 people",  # Unrealistic number
        "green card with premium processing and fee waiver and attorney",  # Many services
        "😀🎉 naturalization with emojis! 🎊",  # Special characters
        "NATURALIZATION IN ALL CAPS",  # Case sensitivity
        "naturalization\nwith\nnewlines",  # Formatting issues
    ]
    
    for query in edge_cases:
        print(f"\nTesting edge case: '{query}'")
        try:
            result = fee_calculator_tool(query)
            
            if result.get('success', False):
                print(f"  ✅ Handled successfully: ${result.get('total_cost', 0)}")
            else:
                print(f"  ✅ Gracefully failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"  ❌ Unhandled exception: {e}")

def test_fee_structure_validation():
    """Test that fee structure data is valid and complete"""
    print("\n🧪 Testing Fee Structure Validation")
    print("=" * 50)
    
    try:
        fees = get_current_uscis_fees()
        print(f"✅ Retrieved fee structure with {len(fees)} categories")
        
        # Check required fee categories
        required_categories = [
            "naturalization", "green_card", "h1b", "opt", 
            "asylum", "family_petition", "extension"
        ]
        
        missing_categories = []
        for category in required_categories:
            if category not in fees:
                missing_categories.append(category)
        
        if missing_categories:
            print(f"❌ Missing fee categories: {missing_categories}")
        else:
            print("✅ All required fee categories present")
        
        # Validate fee structure for each category
        for category, fee_data in fees.items():
            if isinstance(fee_data, dict):
                # Check for negative fees (should not exist)
                negative_fees = []
                for key, value in fee_data.items():
                    if isinstance(value, (int, float)) and value < 0:
                        negative_fees.append(f"{category}.{key}")
                
                if negative_fees:
                    print(f"❌ Negative fees found: {negative_fees}")
                else:
                    print(f"✅ {category}: No negative fees")
            
    except Exception as e:
        print(f"❌ Fee structure validation failed: {e}")

def test_performance_and_reliability():
    """Test performance and reliability with multiple queries"""
    print("\n🧪 Testing Performance and Reliability")
    print("=" * 50)
    
    # Test with multiple rapid queries
    test_queries = [
        "naturalization for myself",
        "green card for family of 3",
        "H-1B with premium processing",
        "asylum application",
        "extend F-1 visa"
    ] * 10  # Run each query 10 times
    
    start_time = datetime.now()
    successful_queries = 0
    failed_queries = 0
    
    for i, query in enumerate(test_queries):
        try:
            result = fee_calculator_tool(query)
            if result.get('success', False):
                successful_queries += 1
            else:
                failed_queries += 1
        except Exception as e:
            failed_queries += 1
            if i < 5:  # Only show first few errors
                print(f"  ❌ Query {i+1} failed: {e}")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"✅ Processed {len(test_queries)} queries in {duration:.2f} seconds")
    print(f"✅ Success rate: {successful_queries}/{len(test_queries)} ({successful_queries/len(test_queries)*100:.1f}%)")
    print(f"Average time per query: {duration/len(test_queries)*1000:.1f}ms")
    
    if failed_queries > 0:
        print(f"⚠️  {failed_queries} queries failed")

def main():
    """Run all fee calculator tests"""
    print("🔬 FEE CALCULATOR TEST SUITE")
    print("=" * 70)
    print(f"Running from: {os.getcwd()}")
    print(f"Python path includes: {len(sys.path)} directories")
    
    try:
        # Test 1: Procedure type extraction
        test_procedure_type_extraction()
        
        # Test 2: Applicant information extraction
        test_applicant_info_extraction()
        
        # Test 3: Additional services extraction
        test_additional_services_extraction()
        
        # Test 4: Query parsing
        test_query_parsing()
        
        # Test 5: Fee calculations
        test_fee_calculations()
        
        # Test 6: Edge cases
        test_edge_cases()
        
        # Test 7: Fee structure validation
        test_fee_structure_validation()
        
        # Test 8: Performance and reliability
        test_performance_and_reliability()
        
        print("\n🎉 ALL TESTS COMPLETED!")
        print("Fee calculator tool has been comprehensively tested")
        
    except Exception as e:
        print(f"\n💥 TEST SUITE FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()