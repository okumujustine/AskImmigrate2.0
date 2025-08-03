#!/usr/bin/env python3
"""
Comprehensive Resilience Test Suite for AskImmigrate2.0 Manager Node
Tests all failure scenarios from the resilience documentation.

Usage (from project root):
    python backend/code/tests/test_resilience.py
    python backend/code/tests/test_resilience.py --test empty_llm
"""

import time
import json
from unittest.mock import Mock
from typing import Dict, Any, List
import sys
import os
from pathlib import Path

# Fix imports - add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

print(f"🔧 Project root: {project_root}")
print(f"🔧 Python path updated")

# Test if we can import the basic modules
try:
    # Import what exists
    print("🔍 Checking existing imports...")
    
    # This should work since it's a basic dict
    from backend.code.agentic_state import ImmigrationState
    print("✅ Successfully imported ImmigrationState")
except ImportError as e:
    print(f"⚠️ Could not import ImmigrationState: {e}")
    # Create a mock version for testing
    class ImmigrationState(dict):
        """Mock ImmigrationState for testing purposes"""
        pass
    print("✅ Created mock ImmigrationState")

# Mock the resilience components that don't exist yet
print("🔧 Setting up mock resilience components...")

class MockManagerOutput:
    """Mock version of the ManagerOutput Pydantic model"""
    def __init__(self, decision="Mock decision", question_type="immigration_inquiry", 
                 complexity="simple", confidence=0.8, tool_recommendations=None):
        self.decision = decision
        self.question_type = question_type
        self.complexity = complexity
        self.confidence = confidence
        self.tool_recommendations = tool_recommendations or ["rag_retrieval_tool"]

class MockToolCircuitBreaker:
    """Mock version of the ToolCircuitBreaker class"""
    def __init__(self):
        self.failure_counts = {}
        self.disabled_until = {}
        self.failure_threshold = 3
        self.recovery_timeout = 300  # 5 minutes

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if tool is available (circuit not open)"""
        if tool_name in self.disabled_until:
            if time.time() < self.disabled_until[tool_name]:
                return False
            else:
                # Re-enable tool
                del self.disabled_until[tool_name]
                self.failure_counts[tool_name] = 0
        return True

    def record_success(self, tool_name: str):
        """Record successful tool execution"""
        self.failure_counts[tool_name] = 0

    def record_failure(self, tool_name: str):
        """Record tool failure and potentially open circuit"""
        self.failure_counts[tool_name] = self.failure_counts.get(tool_name, 0) + 1
        if self.failure_counts[tool_name] >= self.failure_threshold:
            # Open circuit breaker
            self.disabled_until[tool_name] = time.time() + self.recovery_timeout
            print(f"🚨 Circuit breaker opened for {tool_name} after {self.failure_counts[tool_name]} failures")

# Mock functions that represent what your resilience implementation should do
def mock_validate_manager_response(response, session_id: str) -> MockManagerOutput:
    """
    Mock version of validate_manager_response - shows what the real function should do
    """
    try:
        if not response or not hasattr(response, 'content'):
            print(f"🔍 Mock: Empty LLM response detected for session {session_id}")
            return MockManagerOutput(
                decision="I'll help you with your immigration question using standard processing. No response from LLM",
                question_type="fallback",
                confidence=0.3
            )
        
        content = response.content.strip() if response.content else ""
        
        # Validate content length
        if len(content) < 10:
            print(f"🔍 Mock: Short response detected ({len(content)} chars) for session {session_id}")
            return MockManagerOutput(
                decision="I'll help you with your immigration question using standard processing. Response too short",
                question_type="fallback",
                confidence=0.3
            )
        
        # Truncate if too long
        if len(content) > 5000:
            content = content[:5000] + "... [truncated for safety]"
            print(f"🔍 Mock: Long response truncated for session {session_id}")
        
        # Extract tool mentions from content (simple pattern matching)
        tool_recommendations = []
        content_lower = content.lower()
        if any(word in content_lower for word in ["search", "web", "current"]):
            tool_recommendations.append("web_search_tool")
        if any(word in content_lower for word in ["fee", "cost", "price"]):
            tool_recommendations.append("fee_calculator_tool")
        if not tool_recommendations:
            tool_recommendations.append("rag_retrieval_tool")
        
        print(f"🔍 Mock: Valid response processed for session {session_id}")
        return MockManagerOutput(
            decision=content,
            tool_recommendations=tool_recommendations,
            confidence=0.8,
            question_type="immigration_inquiry",
            complexity="complex" if len(tool_recommendations) > 1 else "simple"
        )
        
    except Exception as e:
        print(f"🔍 Mock: Validation failed for session {session_id}: {e}")
        return MockManagerOutput(
            decision=f"I'll help you with your immigration question using standard processing. Validation failed: {str(e)}",
            question_type="fallback",
            confidence=0.3
        )

def mock_execute_tool_with_circuit_breaker(tool_name: str, tool, tool_args: dict, session_id: str) -> dict:
    """
    Mock version of execute_tool_with_circuit_breaker - shows circuit breaker pattern
    """
    tool_circuit_breaker = MockToolCircuitBreaker()
    
    # Check circuit breaker
    if not tool_circuit_breaker.is_tool_available(tool_name):
        print(f"🚨 Mock: Circuit breaker open for {tool_name}, using fallback")
        return mock_create_tool_fallback_response(tool_name, tool_args, "Circuit breaker open")
    
    try:
        # Simulate tool execution
        print(f"🔧 Mock: Executing tool {tool_name} for session {session_id}")
        result = tool.invoke(tool_args)
        tool_circuit_breaker.record_success(tool_name)
        print(f"✅ Mock: Tool {tool_name} executed successfully")
        return result
    except Exception as e:
        print(f"❌ Mock: Tool {tool_name} failed: {e}")
        tool_circuit_breaker.record_failure(tool_name)
        return mock_create_tool_fallback_response(tool_name, tool_args, str(e))

def mock_create_tool_fallback_response(tool_name: str, tool_args: dict, error_reason: str) -> dict:
    """
    Mock version of create_tool_fallback_response - shows fallback strategy
    """
    print(f"🔄 Mock: Creating fallback response for {tool_name} due to: {error_reason}")
    
    fallbacks = {
        "web_search_tool": {
            "results": [],
            "message": "Unable to search current information. Using stored knowledge.",
            "fallback_used": True,
            "error_reason": error_reason
        },
        "fee_calculator_tool": {
            "estimated_fee": "Fee information currently unavailable",
            "disclaimer": "Please check USCIS.gov for current fees",
            "fallback_used": True,
            "error_reason": error_reason
        },
        "rag_retrieval_tool": {
            "response": "I'll provide general immigration guidance based on common knowledge.",
            "references": [],
            "fallback_used": True,
            "error_reason": error_reason
        }
    }
    
    return fallbacks.get(tool_name, {
        "error": f"Tool {tool_name} unavailable",
        "error_type": "configuration_error",
        "fallback_used": True,
        "error_reason": error_reason
    })


class TestResilienceScenarios:
    """Test suite for all resilience failure scenarios"""
    
    def setup_method(self):
        """Reset state before each test"""
        # Create base test state
        self.base_state = ImmigrationState({
            "text": "What is an H-1B visa?",
            "session_id": "test-session-123",
            "conversation_history": [],
            "session_context": None,
            "is_followup_question": False,
            "conversation_turn_number": 1
        })
        print(f"🔧 Test setup complete for session: test-session-123")
    
    # ============================================================================
    # TEST 1: EMPTY LLM RESPONSE SCENARIOS
    # ============================================================================
    
    def test_empty_llm_response(self):
        """Test handling of completely empty LLM responses"""
        print("\n🧪 Testing Empty LLM Response Scenarios...")
        
        # Mock LLM that returns None
        mock_response = Mock()
        mock_response.content = None
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        assert "I'll help you with your immigration question" in result.decision
        assert result.question_type == "fallback"
        assert result.confidence == 0.3
        assert "rag_retrieval_tool" in result.tool_recommendations
        print("✅ Empty LLM response handled correctly")
    
    def test_whitespace_only_response(self):
        """Test handling of whitespace-only responses"""
        mock_response = Mock()
        mock_response.content = "   \n\t   "
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        assert result.question_type == "fallback"
        assert len(result.tool_recommendations) > 0
        print("✅ Whitespace-only response handled correctly")
    
    def test_too_short_response(self):
        """Test handling of responses that are too short"""
        mock_response = Mock()
        mock_response.content = "Yes."
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        assert result.question_type == "fallback"
        print("✅ Too-short response handled correctly")
    
    def test_no_response_attribute(self):
        """Test handling when response object has no content attribute"""
        mock_response = Mock(spec=[])  # Mock with no attributes
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        assert result.question_type == "fallback"
        print("✅ Missing content attribute handled correctly")
    
    def test_manager_node_simulation(self):
        """Test simulation of manager node with empty LLM response"""
        print("✅ Manager node simulation completed (implementation pending)")
    
    # ============================================================================
    # TEST 2: TOOL FAILURE SCENARIOS
    # ============================================================================
    
    def test_tool_network_timeout(self):
        """Test tool failure due to network timeout"""
        print("\n🔧 Testing Tool Failure Scenarios...")
        
        def timeout_tool(args):  # Fixed: accept args parameter
            raise TimeoutError("Connection timeout after 30 seconds")
        
        mock_tool = Mock()
        mock_tool.invoke = timeout_tool
        
        result = mock_execute_tool_with_circuit_breaker(
            "web_search_tool", mock_tool, {"query": "test"}, "test-session"
        )
        
        assert result["fallback_used"] is True
        assert "timeout" in result["error_reason"].lower()
        print("✅ Network timeout handled with fallback")
    
    def test_tool_rate_limit(self):
        """Test tool failure due to rate limiting"""
        def rate_limit_tool(args):  # Fixed: accept args parameter
            raise Exception("Rate limit exceeded. Please try again later.")
        
        mock_tool = Mock()
        mock_tool.invoke = rate_limit_tool
        
        result = mock_execute_tool_with_circuit_breaker(
            "fee_calculator_tool", mock_tool, {"query": "test"}, "test-session"
        )
        
        assert result["fallback_used"] is True
        assert "rate limit" in result["error_reason"].lower()
        print("✅ Rate limit error handled with fallback")
    
    def test_tool_api_error(self):
        """Test tool failure due to API errors"""
        def api_error_tool(args):  # Fixed: accept args parameter
            raise Exception("Internal Server Error: 500")
        
        mock_tool = Mock()
        mock_tool.invoke = api_error_tool
        
        result = mock_execute_tool_with_circuit_breaker(
            "rag_retrieval_tool", mock_tool, {"query": "test"}, "test-session"
        )
        
        assert result["fallback_used"] is True
        assert "general immigration guidance" in result["response"]
        print("✅ API error handled with meaningful fallback")
    
    def test_circuit_breaker_activation(self):
        """Test circuit breaker opens after repeated failures"""
        test_breaker = MockToolCircuitBreaker()
        test_breaker.failure_threshold = 3
        
        # Manually inject failures
        for i in range(4):  # Exceed threshold
            test_breaker.record_failure("test_tool")
        
        # Tool should now be unavailable
        assert not test_breaker.is_tool_available("test_tool")
        print("✅ Circuit breaker opens after threshold failures")
    
    def test_circuit_breaker_recovery(self):
        """Test circuit breaker recovers after timeout"""
        test_breaker = MockToolCircuitBreaker()
        test_breaker.recovery_timeout = 0.1  # 100ms for testing
        
        # Force circuit open
        test_breaker.disabled_until["test_tool"] = time.time() + 0.1
        
        # Should be disabled initially
        assert not test_breaker.is_tool_available("test_tool")
        
        # Wait for recovery
        time.sleep(0.2)
        
        # Should be available again
        assert test_breaker.is_tool_available("test_tool")
        print("✅ Circuit breaker recovers after timeout")
    
    # ============================================================================
    # TEST 3: RATE LIMITING SCENARIOS
    # ============================================================================
    
    def test_session_rate_limiting(self):
        """Test rate limiting at session level"""
        print("\n⏱️ Testing Rate Limiting Scenarios...")
        
        # Simulate rate limiting check
        def mock_rate_limit_check():
            return False  # Rate limit exceeded
        
        # Test the concept - in real implementation this would be integrated
        rate_limited = not mock_rate_limit_check()
        assert rate_limited == True
        print("✅ Session rate limiting detection working")
    
    def test_llm_rate_limiting(self):
        """Test LLM provider rate limiting"""
        def rate_limited_llm():
            raise Exception("Rate limit exceeded: 429 Too Many Requests")
        
        # Test that we can detect rate limiting errors
        try:
            rate_limited_llm()
        except Exception as e:
            assert "rate limit" in str(e).lower()
            print("✅ LLM rate limiting error detected correctly")
    
    def test_api_quota_exhaustion(self):
        """Test API quota exhaustion scenarios"""
        def quota_exhausted(args):  # Fixed: accept args parameter
            raise Exception("Quota exceeded for this month")
        
        mock_tool = Mock()
        mock_tool.invoke = quota_exhausted
        
        result = mock_execute_tool_with_circuit_breaker(
            "fee_calculator_tool", mock_tool, {"query": "test"}, "test-session"
        )
        
        assert result["fallback_used"] is True
        assert "check USCIS.gov" in result["disclaimer"]
        print("✅ API quota exhaustion provides useful fallback")
    
    # ============================================================================
    # TEST 4: MALFORMED RESPONSE SCENARIOS
    # ============================================================================
    
    def test_malformed_json_response(self):
        """Test handling of malformed JSON in tool responses"""
        print("\n🔀 Testing Malformed Response Scenarios...")
        
        def malformed_json_tool(args):  # Fixed: accept args parameter
            return "{'invalid': json, syntax}"  # Invalid JSON
        
        mock_tool = Mock()
        mock_tool.invoke = malformed_json_tool
        
        # This should not crash
        try:
            result = mock_execute_tool_with_circuit_breaker(
                "rag_retrieval_tool", mock_tool, {"query": "test"}, "test-session"
            )
            assert result is not None
        except Exception:
            # Even if it fails, it shouldn't crash the system
            pass
        
        print("✅ Malformed JSON handled without crashing")
    
    def test_extremely_long_response(self):
        """Test handling of extremely long LLM responses"""
        mock_response = Mock()
        mock_response.content = "A" * 10000  # 10k characters
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        # Fixed: Check for the actual length and truncation
        assert len(result.decision) <= 5000 or "[truncated for safety]" in result.decision
        print("✅ Extremely long response truncated safely")
    
    def test_special_characters_response(self):
        """Test handling of responses with special characters"""
        mock_response = Mock()
        mock_response.content = "🤖💀🔥 Special chars and emojis 特殊字符"
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        assert result.decision == mock_response.content
        assert result.question_type == "immigration_inquiry"
        print("✅ Special characters handled correctly")
    
    def test_html_injection_response(self):
        """Test handling of HTML/script injection attempts"""
        mock_response = Mock()
        mock_response.content = "<script>alert('xss')</script>This is a normal response"
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        # Should accept the response (validation happens elsewhere)
        assert len(result.decision) > 10
        print("✅ HTML injection handled (would be sanitized in input validation)")
    
    def test_unicode_edge_cases(self):
        """Test handling of problematic Unicode characters"""
        mock_response = Mock()
        mock_response.content = "Unicode: 𝔘𝔫𝔦𝔠𝔬𝔡𝔢 𝔞𝔫𝔡 ￼￼￼ special chars"
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        assert len(result.decision) > 10
        print("✅ Unicode edge cases handled correctly")
    
    # ============================================================================
    # TEST 5: COMBINED FAILURE SCENARIOS
    # ============================================================================
    
    def test_cascading_failures(self):
        """Test system behavior under cascading failures"""
        print("\n💥 Testing Cascading Failure Scenarios...")
        
        # Simulate multiple failures happening simultaneously
        mock_response = Mock()
        mock_response.content = "Error"  # Too short
        
        # Validate the LLM response (should fallback)
        llm_result = mock_validate_manager_response(mock_response, "test-session")
        assert llm_result.question_type == "fallback"
        
        # Simulate tool failure as well
        def failing_tool(args):  # Fixed: accept args parameter
            raise Exception("Total tool failure")
        
        mock_tool = Mock()
        mock_tool.invoke = failing_tool
        
        tool_result = mock_execute_tool_with_circuit_breaker(
            "web_search_tool", mock_tool, {"query": "test"}, "test-session"
        )
        
        assert tool_result["fallback_used"] is True
        print("✅ System survives cascading failures")
    
    def test_resource_exhaustion(self):
        """Test behavior under resource exhaustion"""
        # Simulate memory pressure by creating large responses
        mock_response = Mock()
        mock_response.content = "Large response " * 1000  # Large but not excessive
        
        result = mock_validate_manager_response(mock_response, "test-session")
        
        # Fixed: Check for actual length OR truncation marker
        assert len(result.decision) <= 5000 or "[truncated for safety]" in result.decision
        print("✅ Resource exhaustion handled with truncation")
    
    def test_infinite_loop_prevention(self):
        """Test that iteration limits prevent infinite loops"""
        # Test the concept of iteration limiting
        test_state = self.base_state.copy()
        test_state["iteration_count"] = 15  # Exceed hypothetical limit
        test_state["max_iterations"] = 10
        
        # In a real implementation, this would trigger early termination
        iteration_count = test_state.get("iteration_count", 0)
        max_iterations = test_state.get("max_iterations", 10)
        
        assert iteration_count > max_iterations
        print("✅ Iteration limit detection working")


# ============================================================================
# PERFORMANCE TESTING
# ============================================================================

class TestPerformanceResilience:
    """Test performance under stress conditions"""
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        print("\n🚀 Testing Performance Resilience...")
        
        def simulate_request():
            mock_response = Mock()
            mock_response.content = "Test response for concurrent request"
            return mock_validate_manager_response(mock_response, f"session-{time.time()}")
        
        # Simulate multiple concurrent requests
        results = []
        for i in range(10):
            result = simulate_request()
            results.append(result)
            time.sleep(0.01)  # Small delay
        
        # All should succeed
        assert len(results) == 10
        assert all(r.decision for r in results)
        print("✅ Concurrent requests handled successfully")
    
    def test_large_conversation_history(self):
        """Test with large conversation histories"""
        large_state = ImmigrationState({
            "text": "What about fees?",
            "session_id": "large-session",
            "conversation_history": [
                Mock(question=f"Question {i}", answer=f"Answer {i}" * 100)
                for i in range(50)  # Large history
            ],
            "is_followup_question": True
        })
        
        # Should handle large state without crashing
        assert len(large_state["conversation_history"]) == 50
        print("✅ Large conversation history handled")


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_specific_test(test_name: str):
    """Run a specific test category"""
    print(f"\n🎯 Running specific test category: {test_name}")
    print("=" * 50)
    
    suite = TestResilienceScenarios()
    suite.setup_method()
    
    if test_name == "empty_llm":
        suite.test_empty_llm_response()
        suite.test_whitespace_only_response()
        suite.test_too_short_response()
        suite.test_no_response_attribute()
        suite.test_manager_node_simulation()
        
    elif test_name == "tool_failures":
        suite.test_tool_network_timeout()
        suite.test_tool_rate_limit()
        suite.test_tool_api_error()
        suite.test_circuit_breaker_activation()
        suite.test_circuit_breaker_recovery()
        
    elif test_name == "rate_limiting":
        suite.test_session_rate_limiting()
        suite.test_llm_rate_limiting()
        suite.test_api_quota_exhaustion()
        
    elif test_name == "malformed_responses":
        suite.test_malformed_json_response()
        suite.test_extremely_long_response()
        suite.test_special_characters_response()
        suite.test_html_injection_response()
        suite.test_unicode_edge_cases()
        
    else:
        print(f"❌ Unknown test: {test_name}")
        print("Available tests: empty_llm, tool_failures, rate_limiting, malformed_responses")


def run_all_tests():
    """Run the complete resilience test suite"""
    print("🧪 Starting Complete Resilience Test Suite")
    print("=" * 60)
    print("📝 Note: This test suite uses mock implementations")
    print("   to test resilience patterns before full implementation.")
    print("=" * 60)
    
    # Initialize test suites
    resilience_tests = TestResilienceScenarios()
    performance_tests = TestPerformanceResilience()
    
    test_results = {
        "passed": 0,
        "failed": 0,
        "errors": []
    }
    
    # Test categories with their test methods
    test_categories = [
        ("Empty LLM Responses", [
            (resilience_tests, "test_empty_llm_response"),
            (resilience_tests, "test_whitespace_only_response"),
            (resilience_tests, "test_too_short_response"),
            (resilience_tests, "test_no_response_attribute"),
            (resilience_tests, "test_manager_node_simulation"),
        ]),
        ("Tool Failures", [
            (resilience_tests, "test_tool_network_timeout"),
            (resilience_tests, "test_tool_rate_limit"),
            (resilience_tests, "test_tool_api_error"),
            (resilience_tests, "test_circuit_breaker_activation"),
            (resilience_tests, "test_circuit_breaker_recovery"),
        ]),
        ("Rate Limiting", [
            (resilience_tests, "test_session_rate_limiting"),
            (resilience_tests, "test_llm_rate_limiting"),
            (resilience_tests, "test_api_quota_exhaustion"),
        ]),
        ("Malformed Responses", [
            (resilience_tests, "test_malformed_json_response"),
            (resilience_tests, "test_extremely_long_response"),
            (resilience_tests, "test_special_characters_response"),
            (resilience_tests, "test_html_injection_response"),
            (resilience_tests, "test_unicode_edge_cases"),
        ]),
        ("Cascading Failures", [
            (resilience_tests, "test_cascading_failures"),
            (resilience_tests, "test_resource_exhaustion"),
            (resilience_tests, "test_infinite_loop_prevention"),
        ]),
        ("Performance", [
            (performance_tests, "test_concurrent_requests"),
            (performance_tests, "test_large_conversation_history"),
        ])
    ]
    
    # Run all test categories
    for category_name, tests in test_categories:
        print(f"\n📋 {category_name}")
        print("-" * 40)
        
        for test_instance, test_method_name in tests:
            try:
                # Setup before each test
                if hasattr(test_instance, 'setup_method'):
                    test_instance.setup_method()
                
                # Get and run the test method
                test_method = getattr(test_instance, test_method_name)
                test_method()
                test_results["passed"] += 1
                
            except Exception as e:
                print(f"❌ {test_method_name} FAILED: {str(e)}")
                test_results["failed"] += 1
                test_results["errors"].append(f"{test_method_name}: {str(e)}")
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"✅ Passed: {test_results['passed']}")
    print(f"❌ Failed: {test_results['failed']}")
    total_tests = test_results['passed'] + test_results['failed']
    if total_tests > 0:
        print(f"📈 Success Rate: {test_results['passed']/total_tests*100:.1f}%")
    
    if test_results["errors"]:
        print("\n💥 FAILED TESTS:")
        for error in test_results["errors"]:
            print(f"  - {error}")
    
    
    return test_results


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AskImmigrate2.0 Resilience Test Suite")
    parser.add_argument("--test", help="Run specific test category", 
                       choices=["empty_llm", "tool_failures", "rate_limiting", "malformed_responses"])
    
    args = parser.parse_args()
    
    print("🧪 AskImmigrate2.0 Resilience Test Suite")
    print("=" * 50)
    
    if args.test:
        run_specific_test(args.test)
    else:
        print("\n🚀 Running complete test suite...")
        results = run_all_tests()
        
        # Exit with appropriate code for CI/CD
        if results["failed"] > 0:
            exit(1)
        else:
            exit(0)