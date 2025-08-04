#!/usr/bin/env python3
"""
Comprehensive test suite for tool_registry module - Test coverage improvement
Target: 67% -> 100% coverage for backend/code/tools/tool_registry.py (12 statements, 4 missing)

Test categories:
1. Tool registry functions and tool listing
2. Agent-specific tool access
3. Tool mapping validation and configuration
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


class TestToolRegistryModule:
    """Comprehensive tool_registry module testing"""

    def test_get_all_tools_returns_list(self):
        """Test 1: get_all_tools returns a list of tools"""
        
        from backend.code.tools.tool_registry import get_all_tools
        
        tools = get_all_tools()
        
        # Verify it returns a list
        assert isinstance(tools, list)
        assert len(tools) == 3  # rag_retrieval_tool, fee_calculator_tool, web_search_tool
        
        # Verify all tools are BaseTool instances
        from langchain_core.tools import BaseTool
        for tool in tools:
            assert isinstance(tool, BaseTool)

    def test_get_all_tools_specific_tools(self):
        """Test 2: get_all_tools returns expected specific tools"""
        
        from backend.code.tools.tool_registry import get_all_tools
        
        tools = get_all_tools()
        tool_names = [tool.name for tool in tools]
        
        # Verify expected tools are included
        expected_tools = ["rag_retrieval_tool", "fee_calculator_tool", "web_search_tool"]
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_get_tools_by_agent_manager(self):
        """Test 3: Manager agent gets only RAG tool"""
        
        with patch('builtins.print') as mock_print:
            from backend.code.tools.tool_registry import get_tools_by_agent
            
            tools = get_tools_by_agent("manager")
            
            # Verify manager gets only RAG tool
            assert len(tools) == 1
            assert tools[0].name == "rag_retrieval_tool"
            
            # Verify print was called with correct message
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Agent 'manager' has access to 1 tools" in call_args
            assert "rag_retrieval_tool" in call_args

    def test_get_tools_by_agent_synthesis(self):
        """Test 4: Synthesis agent gets all tools"""
        
        with patch('builtins.print') as mock_print:
            from backend.code.tools.tool_registry import get_tools_by_agent
            
            tools = get_tools_by_agent("synthesis")
            
            # Verify synthesis gets all 3 tools
            assert len(tools) == 3
            tool_names = [tool.name for tool in tools]
            expected_tools = ["rag_retrieval_tool", "web_search_tool", "fee_calculator_tool"]
            for expected_tool in expected_tools:
                assert expected_tool in tool_names
            
            # Verify print was called with correct message
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Agent 'synthesis' has access to 3 tools" in call_args

    def test_get_tools_by_agent_reviewer(self):
        """Test 5: Reviewer agent gets fee calculator and web search tools"""
        
        with patch('builtins.print') as mock_print:
            from backend.code.tools.tool_registry import get_tools_by_agent
            
            tools = get_tools_by_agent("reviewer")
            
            # Verify reviewer gets 2 tools
            assert len(tools) == 2
            tool_names = [tool.name for tool in tools]
            expected_tools = ["fee_calculator_tool", "web_search_tool"]
            for expected_tool in expected_tools:
                assert expected_tool in tool_names
            
            # Verify RAG tool is not included
            assert "rag_retrieval_tool" not in tool_names
            
            # Verify print was called with correct message
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Agent 'reviewer' has access to 2 tools" in call_args

    def test_get_tools_by_agent_unknown_agent(self):
        """Test 6: Unknown agent gets empty list"""
        
        with patch('builtins.print') as mock_print:
            from backend.code.tools.tool_registry import get_tools_by_agent
            
            tools = get_tools_by_agent("unknown_agent")
            
            # Verify unknown agent gets empty list
            assert len(tools) == 0
            assert tools == []
            
            # Verify print was called with correct message
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            assert "Agent 'unknown_agent' has access to 0 tools" in call_args

    def test_get_tools_by_agent_empty_string(self):
        """Test 7: Empty string agent name returns empty list"""
        
        with patch('builtins.print') as mock_print:
            from backend.code.tools.tool_registry import get_tools_by_agent
            
            tools = get_tools_by_agent("")
            
            # Verify empty string gets empty list
            assert len(tools) == 0
            assert tools == []
            
            # Verify print was called
            mock_print.assert_called_once()

    def test_get_tools_by_agent_case_sensitivity(self):
        """Test 8: Agent names are case sensitive"""
        
        with patch('builtins.print') as mock_print:
            from backend.code.tools.tool_registry import get_tools_by_agent
            
            # Test different cases
            tools_upper = get_tools_by_agent("MANAGER")
            tools_mixed = get_tools_by_agent("Manager")
            
            # Verify case sensitivity - should return empty for non-exact matches
            assert len(tools_upper) == 0
            assert len(tools_mixed) == 0

    def test_tool_mapping_coverage(self):
        """Test 9: Verify all agent mappings are covered"""
        
        from backend.code.tools.tool_registry import get_tools_by_agent
        
        # Test all defined agents
        agent_configs = {
            "manager": 1,      # Should have 1 tool (RAG)
            "synthesis": 3,    # Should have 3 tools (all)
            "reviewer": 2      # Should have 2 tools (fee calc + web search)
        }
        
        for agent_name, expected_count in agent_configs.items():
            with patch('builtins.print'):
                tools = get_tools_by_agent(agent_name)
                assert len(tools) == expected_count, f"Agent {agent_name} should have {expected_count} tools, got {len(tools)}"

    def test_module_imports_and_structure(self):
        """Test 10: Module imports and structure verification"""
        
        import backend.code.tools.tool_registry as registry
        
        # Verify module has expected functions
        assert hasattr(registry, 'get_all_tools')
        assert hasattr(registry, 'get_tools_by_agent')
        assert callable(registry.get_all_tools)
        assert callable(registry.get_tools_by_agent)
        
        # Verify imports are available
        assert hasattr(registry, 'List')
        assert hasattr(registry, 'BaseTool')
        
        # Verify tool imports
        assert hasattr(registry, 'rag_retrieval_tool')
        assert hasattr(registry, 'fee_calculator_tool')
        assert hasattr(registry, 'web_search_tool')

    def test_tool_consistency_between_functions(self):
        """Test 11: Tools returned by get_all_tools match those used in get_tools_by_agent"""
        
        from backend.code.tools.tool_registry import get_all_tools, get_tools_by_agent
        
        all_tools = get_all_tools()
        all_tool_names = {tool.name for tool in all_tools}
        
        # Collect all tools used by agents
        agent_tool_names = set()
        agents = ["manager", "synthesis", "reviewer"]
        
        for agent in agents:
            with patch('builtins.print'):
                agent_tools = get_tools_by_agent(agent)
                agent_tool_names.update(tool.name for tool in agent_tools)
        
        # Verify all agent tools are subset of all tools
        assert agent_tool_names.issubset(all_tool_names), "Agent tools should be subset of all available tools"
        
        # Verify all tools from get_all_tools are used by at least one agent
        assert all_tool_names == agent_tool_names, "All tools should be used by at least one agent"

    def test_function_return_types(self):
        """Test 12: Function return types are correct"""
        
        from backend.code.tools.tool_registry import get_all_tools, get_tools_by_agent
        from langchain_core.tools import BaseTool
        from typing import List
        
        # Test get_all_tools return type
        all_tools = get_all_tools()
        assert isinstance(all_tools, list)
        for tool in all_tools:
            assert isinstance(tool, BaseTool)
        
        # Test get_tools_by_agent return type
        with patch('builtins.print'):
            agent_tools = get_tools_by_agent("manager")
            assert isinstance(agent_tools, list)
            for tool in agent_tools:
                assert isinstance(tool, BaseTool)
