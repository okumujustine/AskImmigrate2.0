#!/usr/bin/env python3
"""
Unit test for manager_node.py to understand current behavior
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Setup paths for tests directory: AskImmigrate2.0/backend/code/tests/
current_file = Path(__file__).resolve()
tests_dir = current_file.parent  # backend/code/tests/
code_dir = tests_dir.parent      # backend/code/
backend_dir = code_dir.parent    # backend/
project_root = backend_dir.parent # AskImmigrate2.0/

for path in [str(project_root), str(backend_dir)]:
    if path not in sys.path:
        sys.path.insert(0, path)

def test_manager_node_basic():
    """Test basic manager node functionality."""
    print("🧪 Testing Manager Node - Basic Functionality")
    print("=" * 50)
    
    try:
        from backend.code.agent_nodes.manager_node import manager_node
        from backend.code.agentic_state import ImmigrationState
        
        # Create test state
        test_state = ImmigrationState(
            text="What is an F-1 visa and how much does it cost?"
        )
        
        print(f"📋 Input state: {test_state}")
        print(f"📋 Question: {test_state['text']}")
        
        # Test the manager node
        print("\n🔄 Calling manager_node...")
        result = manager_node(test_state)
        
        # Analyze results
        print("\n📊 RESULTS ANALYSIS:")
        print(f"✅ Return type: {type(result)}")
        print(f"✅ Keys returned: {list(result.keys())}")
        
        if "manager_decision" in result:
            decision = result["manager_decision"]
            print(f"✅ Decision length: {len(decision)} characters")
            print(f"✅ Decision preview: {decision[:200]}...")
            
            # Check what kind of analysis it provides
            decision_lower = decision.lower()
            analysis_indicators = {
                "visa_analysis": any(word in decision_lower for word in ["f-1", "visa", "student"]),
                "cost_analysis": any(word in decision_lower for word in ["cost", "fee", "price", "$"]),
                "process_info": any(word in decision_lower for word in ["apply", "process", "step"]),
                "strategic_guidance": any(word in decision_lower for word in ["recommend", "suggest", "should"])
            }
            
            print("\n🔍 CONTENT ANALYSIS:")
            for indicator, present in analysis_indicators.items():
                status = "✅" if present else "❌"
                print(f"{status} {indicator}: {present}")
        
        return True, result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False, None

def test_manager_node_different_questions():
    """Test manager with different types of questions."""
    print("\n🧪 Testing Manager Node - Different Question Types")
    print("=" * 50)
    
    test_questions = [
        "What is an F-1 visa?",  # Simple factual
        "How much does H-1B cost?",  # Fee inquiry
        "How do I change from F-1 to H-1B status?",  # Complex procedural
        "What are the differences between J-1 and F-1?",  # Comparison
    ]
    
    try:
        from backend.code.agent_nodes.manager_node import manager_node
        from backend.code.agentic_state import ImmigrationState
        
        results = {}
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n📋 Test {i}: {question}")
            
            state = ImmigrationState(text=question)
            result = manager_node(state)
            
            decision = result.get("manager_decision", "")
            results[question] = {
                "length": len(decision),
                "preview": decision[:100] + "..." if len(decision) > 100 else decision
            }
            
            print(f"   Response length: {len(decision)} chars")
        
        print(f"\n📊 SUMMARY:")
        for question, info in results.items():
            print(f"• {question}: {info['length']} chars")
        
        return True, results
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False, None

def test_manager_node_mock_llm():
    """Test manager node with mocked LLM to see exact behavior."""
    print("\n🧪 Testing Manager Node - Mocked LLM")
    print("=" * 50)
    
    try:
        # Mock the LLM response
        mock_response = Mock()
        mock_response.content = "MOCK RESPONSE: This is a test manager decision about F-1 visas."
        
        mock_llm = Mock()
        mock_llm.invoke.return_value = mock_response
        
        with patch('backend.code.agent_nodes.manager_node.get_llm') as mock_get_llm:
            mock_get_llm.return_value = mock_llm
            
            from backend.code.agent_nodes.manager_node import manager_node
            from backend.code.agentic_state import ImmigrationState
            
            state = ImmigrationState(text="What is F-1?")
            result = manager_node(state)
            
            print(f"✅ LLM was called: {mock_llm.invoke.called}")
            print(f"✅ Response: {result}")
            
            # Check what prompt was sent to LLM
            if mock_llm.invoke.called:
                call_args = mock_llm.invoke.call_args
                prompt_sent = call_args[0][0]  # First argument
                print(f"✅ Prompt sent to LLM:")
                print(f"   Length: {len(prompt_sent)} characters")
                print(f"   Preview: {prompt_sent[:300]}...")
            
        return True, result
        
    except Exception as e:
        print(f"❌ Mock test failed: {e}")
        return False, None

def test_manager_config_analysis():
    """Analyze what configuration the manager is using."""
    print("\n🧪 Testing Manager Node - Configuration Analysis")
    print("=" * 50)
    
    try:
        from backend.code.utils import load_config
        from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
        from backend.code.prompt_builder import build_prompt_from_config
        
        # Load configs
        config = load_config(APP_CONFIG_FPATH)
        prompt_config = load_config(PROMPT_CONFIG_FPATH)
        
        print("📋 APP CONFIG:")
        print(f"   LLM: {config.get('llm', 'Not set')}")
        
        print("\n📋 MANAGER PROMPT CONFIG:")
        manager_prompt = prompt_config.get("manager_agent_prompt", {})
        for key, value in manager_prompt.items():
            if isinstance(value, str) and len(value) > 100:
                print(f"   {key}: {value[:100]}...")
            else:
                print(f"   {key}: {value}")
        
        # Test prompt building
        test_input = "What is F-1 visa?"
        built_prompt = build_prompt_from_config(
            config=manager_prompt, 
            input_data=test_input
        )
        
        print(f"\n📋 BUILT PROMPT:")
        print(f"   Length: {len(built_prompt)} characters")
        print(f"   Preview: {built_prompt[:400]}...")
        
        return True, {"config": config, "prompt_config": manager_prompt, "built_prompt": built_prompt}
        
    except Exception as e:
        print(f"❌ Config analysis failed: {e}")
        return False, None

def main():
    """Run all manager node tests."""
    print("🇺🇸" + "="*60 + "🇺🇸")
    print("   Manager Node Testing Suite")
    print("="*64)
    
    tests = [
        ("Configuration Analysis", test_manager_config_analysis),
        ("Mock LLM Test", test_manager_node_mock_llm),
        ("Basic Functionality", test_manager_node_basic),
        ("Different Questions", test_manager_node_different_questions),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        try:
            success, data = test_func()
            results[test_name] = {"success": success, "data": data}
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
            results[test_name] = {"success": False, "error": str(e)}
    
    # Summary
    print("\n🏁 TEST SUMMARY")
    print("="*30)
    
    passed = 0
    for test_name, result in results.items():
        status = "✅ PASS" if result["success"] else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result["success"]:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    print("\n💡 INSIGHTS:")
    print("1. Manager makes a single LLM call with configured prompt")
    print("2. It receives user question and returns text decision")
    print("3. No tool usage despite being in tool registry")
    print("4. No coordination logic - just prompt-based analysis")
    print("5. Response quality depends entirely on LLM and prompt")

if __name__ == "__main__":
    main()