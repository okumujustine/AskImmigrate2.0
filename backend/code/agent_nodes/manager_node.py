from typing import Dict, Any
from backend.code.llm import get_llm
from backend.code.paths import APP_CONFIG_FPATH, PROMPT_CONFIG_FPATH
from backend.code.utils import load_config
from backend.code.prompt_builder import build_prompt_from_config
from backend.code.agentic_state import ImmigrationState
from backend.code.tools.tool_registry import get_tools_by_agent
import re

config = load_config(APP_CONFIG_FPATH)
prompt_config = load_config(PROMPT_CONFIG_FPATH)

def extract_structured_analysis(response_text: str) -> Dict[str, Any]:
    """
    Extract structured information from manager's response with improved parsing.
    
    CHANGES:
    - More flexible regex patterns that handle variations in formatting
    - Better fallback logic when structured format isn't found
    - Simplified field extraction with smart defaults
    - Enhanced debugging output
    """
    analysis = {
        "question_type": "factual",
        "visa_focus": [],
        "complexity": "medium", 
        "urgency": "routine",
        "primary_focus": "",
        "information_depth": "detailed",
        "response_format": "summary",
        "required_tools": ["rag_retrieval_tool"],
        "search_keywords": [],
        "accuracy_check": "",
        "completeness_check": "",
        "legal_compliance": ""
    }
    
    try:
        print(f"🔍 Manager: Parsing response ({len(response_text)} chars)")
        
        # IMPROVED: More flexible patterns that handle spacing and formatting variations
        patterns = {
            "question_type": [
                r"Type:\s*\[([^\]]+)\]",
                r"Question\s*Type:\s*\[([^\]]+)\]",
                r"Type:\s*([a-zA-Z]+)",
                r"question.*type.*:.*?([a-zA-Z]+)",
            ],
            "visa_focus": [
                r"Visa_Focus:\s*\[([^\]]+)\]",
                r"Visa\s*Focus:\s*\[([^\]]+)\]",
                r"visa.*focus.*:.*?\[([^\]]+)\]",
            ],
            "complexity": [
                r"Complexity:\s*\[([^\]]+)\]",
                r"complexity.*:.*?\[([^\]]+)\]",
                r"complexity.*:.*?([a-zA-Z]+)",
            ],
            "primary_focus": [
                r"Primary_Focus:\s*\[([^\]]+)\]",
                r"Primary\s*Focus:\s*\[([^\]]+)\]",
                r"primary.*focus.*:.*?\[([^\]]+)\]",
            ],
            "information_depth": [
                r"Information_Depth:\s*\[([^\]]+)\]",
                r"Information\s*Depth:\s*\[([^\]]+)\]",
                r"information.*depth.*:.*?\[([^\]]+)\]",
            ],
            "required_tools": [
                r"Required_Tools:\s*\[([^\]]+)\]",
                r"Required\s*Tools:\s*\[([^\]]+)\]",
                r"tools.*:.*?\[([^\]]+)\]",
            ],
            "search_keywords": [
                r"Search_Keywords:\s*\[([^\]]+)\]",
                r"Search\s*Keywords:\s*\[([^\]]+)\]",
                r"keywords.*:.*?\[([^\]]+)\]",
            ]
        }
        
        # IMPROVED: Try multiple patterns for each field
        for field, pattern_list in patterns.items():
            found = False
            for pattern in pattern_list:
                match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                if match:
                    value = match.group(1).strip()
                    if field in ["visa_focus", "required_tools", "search_keywords"]:
                        # Parse comma-separated lists
                        analysis[field] = [v.strip() for v in value.split(",") if v.strip()]
                    else:
                        analysis[field] = value
                    print(f"✅ Extracted {field}: {analysis[field]}")
                    found = True
                    break
            
            if not found:
                print(f"⚠️ Could not extract {field}, using default: {analysis[field]}")
        
        # IMPROVED: Smart content-based inference when structured format fails
        response_lower = response_text.lower()
        
        # Infer question type from content
        if analysis["question_type"] == "factual":
            if any(word in response_lower for word in ["how to", "process", "steps", "apply"]):
                analysis["question_type"] = "procedural"
            elif any(word in response_lower for word in ["fee", "cost", "price", "payment"]):
                analysis["question_type"] = "fee"
            elif any(word in response_lower for word in ["eligible", "qualify", "requirements"]):
                analysis["question_type"] = "eligibility"
        
        # Infer visa focus from content
        if not analysis["visa_focus"]:
            visa_patterns = {
                "F-1": ["f-1", "f1", "student visa", "academic"],
                "H-1B": ["h-1b", "h1b", "work visa", "specialty occupation"],
                "OPT": ["opt", "optional practical training"],
                "Green Card": ["green card", "permanent resident", "i-485"],
                "Naturalization": ["naturalization", "citizenship", "n-400"]
            }
            
            for visa_type, keywords in visa_patterns.items():
                if any(keyword in response_lower for keyword in keywords):
                    analysis["visa_focus"].append(visa_type)
        
        # Infer primary focus if not found
        if not analysis["primary_focus"]:
            if analysis["visa_focus"]:
                analysis["primary_focus"] = f"{' and '.join(analysis['visa_focus'])} immigration procedures"
            else:
                analysis["primary_focus"] = "general immigration information"
        
        # Ensure we have useful tools
        if "fee" in response_lower and "fee_calculator_tool" not in analysis["required_tools"]:
            analysis["required_tools"].append("fee_calculator_tool")
        
        # Generate search keywords if none found
        if not analysis["search_keywords"]:
            keywords = []
            if analysis["visa_focus"]:
                keywords.extend(analysis["visa_focus"])
            keywords.extend(["immigration", "USCIS", "requirements"])
            analysis["search_keywords"] = keywords[:5]  # Limit to 5 keywords
            
    except Exception as e:
        print(f"❌ Manager: Error parsing structured response: {e}")
        # Keep defaults which are already set
    
    print(f"📋 Manager: Final analysis - Type: {analysis['question_type']}, Focus: {analysis['visa_focus']}")
    return analysis

def build_session_aware_prompt(user_question: str, state: ImmigrationState) -> str:
    """
    Build manager prompt with enhanced session context awareness.
    
    CHANGES:
    - More explicit instructions for structured output format
    - Better session context integration
    - Clearer examples of expected output
    - Enhanced prompt structure for better LLM understanding
    """
    
    # Get base prompt
    base_prompt = build_prompt_from_config(
        config=prompt_config["manager_agent_prompt"], 
        input_data=user_question
    )
    
    # IMPROVED: More comprehensive session context
    session_context = ""
    if state.get("session_id") and state.get("conversation_history"):
        session_context = f"""
🔄 SESSION CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📱 Session: {state.get("session_id")}
🔢 Turn: #{state.get("conversation_turn_number", 1)}
🔗 Follow-up: {state.get("is_followup_question", False)}

📝 CONVERSATION HISTORY:
"""
        
        history = state.get("conversation_history", [])
        for i, turn in enumerate(history[-3:], 1):  # Show last 3 turns
            session_context += f"""
Q{i}: {turn.question}
A{i}: {turn.answer[:200]}{'...' if len(turn.answer) > 200 else ''}
"""
        
        # Add ongoing topics if available
        if state.get("session_context"):
            ctx = state["session_context"]
            if hasattr(ctx, 'ongoing_topics') and ctx.ongoing_topics:
                session_context += f"\n🎯 ONGOING TOPICS: {', '.join(ctx.ongoing_topics)}"
            if hasattr(ctx, 'visa_types_mentioned') and ctx.visa_types_mentioned:
                session_context += f"\n📋 VISA TYPES DISCUSSED: {', '.join(ctx.visa_types_mentioned)}"
        
        session_context += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # IMPROVED: Add specific instructions for session-aware analysis
        session_context += f"""
🧠 SESSION AWARENESS INSTRUCTIONS:
- If this is a follow-up question, reference the conversation history above
- Build upon previous topics and visa types mentioned
- Consider the user's ongoing immigration journey
- Provide continuity with previous responses

"""
    
    # IMPROVED: Enhanced prompt with better structure and examples
    enhanced_prompt = f"""{session_context}

🎯 STRATEGIC ANALYSIS TASK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 USER QUESTION: {user_question}

STEP 1: Use your rag_retrieval_tool to gather immigration information about this question.

STEP 2: After retrieving information, provide your strategic analysis in this EXACT format:

QUESTION_ANALYSIS:
- Type: [factual/procedural/eligibility/fee/comparison/timeline]
- Visa_Focus: [specific visa types, e.g., F-1, H-1B, OPT]
- Complexity: [simple/medium/complex]
- Urgency: [routine/time-sensitive/urgent]

SYNTHESIS_STRATEGY:
- Primary_Focus: [main topic to emphasize]
- Information_Depth: [basic/detailed/comprehensive]
- Response_Format: [summary/step-by-step/comparison/checklist]

TOOL_RECOMMENDATIONS:
- Required_Tools: [rag_retrieval_tool, fee_calculator_tool, web_search_tool]
- Search_Keywords: [key terms for search]
- Priority_Sources: [types of information to prioritize]

VALIDATION_CRITERIA:
- Accuracy_Check: [what facts to verify]
- Completeness_Check: [what information to include]
- Legal_Compliance: [disclaimers needed]

🔥 CRITICAL: Use the EXACT format above with square brackets. Do not deviate from this structure.

{base_prompt}
"""
    
    return enhanced_prompt

def manager_node(state: ImmigrationState) -> Dict[str, Any]:
    """
    Enhanced Strategic Manager Agent with improved session awareness and error handling.
    
    CHANGES:
    - Better session context integration
    - More robust tool execution with proper error handling
    - Improved state management and data flow
    - Enhanced logging and debugging
    - Stronger fallback mechanisms
    """
    print("👔 Manager: Analyzing immigration question and coordinating workflow...")

    user_question = state.get("text", "")
    session_id = state.get("session_id")
    is_followup = state.get("is_followup_question", False)
    
    # Enhanced session logging
    if session_id:
        turn_num = state.get("conversation_turn_number", 1)
        print(f"📱 Session: {session_id} (Turn #{turn_num})")
        if is_followup:
            print("🔗 Follow-up question detected - using conversation context")
    else:
        print("📱 No session context available")
    
    # Get manager's tools
    tools = get_tools_by_agent("manager")
    llm = get_llm(config.get("llm", "gpt-4o-mini"))
    llm_with_tools = llm.bind_tools(tools)

    # Build enhanced session-aware prompt
    prompt = build_session_aware_prompt(user_question, state)

    print(f"🔧 Manager: Using {len(tools)} tools for strategic analysis")
    print(f"🛠️ Available tools: {[tool.name for tool in tools]}")

    try:
        # Execute strategic analysis with tools
        response = llm_with_tools.invoke(prompt)
        
        # IMPROVED: Better tool execution tracking
        tool_calls = getattr(response, 'tool_calls', [])
        tool_results = {}
        rag_response_content = ""
        
        print(f"🔧 Manager: Detected {len(tool_calls)} tool calls")
        
        if tool_calls:
            for tool_call in tool_calls:
                tool_name = tool_call['name']
                tool_args = tool_call['args']
                print(f"⚙️ Executing: {tool_name} with args: {tool_args}")
                
                # Find and execute the tool
                for tool in tools:
                    if tool.name == tool_name:
                        try:
                            # IMPROVED: Enhanced context for RAG tool in sessions
                            if tool_name == "rag_retrieval_tool" and session_id:
                                enhanced_query = user_question
                                if is_followup and state.get("session_context"):
                                    ctx = state["session_context"]
                                    if hasattr(ctx, 'visa_types_mentioned') and ctx.visa_types_mentioned:
                                        enhanced_query = f"{' '.join(ctx.visa_types_mentioned)} {user_question}"
                                
                                result = tool.invoke({"query": enhanced_query})
                                print(f"✅ RAG enhanced query: {enhanced_query[:50]}...")
                            else:
                                result = tool.invoke(tool_args)
                            
                            tool_results[tool_name] = result
                            
                            # Extract RAG content for synthesis
                            if tool_name == "rag_retrieval_tool":
                                if isinstance(result, dict):
                                    rag_response_content = result.get("response", "")
                                else:
                                    rag_response_content = str(result)
                            
                            print(f"✅ Tool {tool_name} executed successfully")
                            
                        except Exception as e:
                            print(f"❌ Tool {tool_name} failed: {e}")
                            tool_results[tool_name] = {"error": str(e)}
                        break
        else:
            # IMPROVED: Always ensure RAG is called for immigration context
            print("🔧 Manager: No tools called by LLM, forcing RAG retrieval...")
            rag_tool = next((tool for tool in tools if tool.name == "rag_retrieval_tool"), None)
            if rag_tool:
                try:
                    # Build context-aware query
                    enhanced_query = user_question
                    if is_followup and state.get("session_context"):
                        ctx = state["session_context"]
                        if hasattr(ctx, 'visa_types_mentioned') and ctx.visa_types_mentioned:
                            enhanced_query = f"{' '.join(ctx.visa_types_mentioned)} immigration: {user_question}"
                    
                    rag_result = rag_tool.invoke({"query": enhanced_query})
                    tool_results["rag_retrieval_tool"] = rag_result
                    
                    if isinstance(rag_result, dict):
                        rag_response_content = rag_result.get("response", "")
                    else:
                        rag_response_content = str(rag_result)
                    
                    print(f"✅ Forced RAG retrieval successful ({len(rag_response_content)} chars)")
                except Exception as e:
                    print(f"❌ Forced RAG retrieval failed: {e}")

        # Get strategic decision
        strategic_decision = response.content or "Strategic analysis completed with tool support."
        
        # IMPROVED: Extract structured information with better error handling
        structured_analysis = extract_structured_analysis(strategic_decision)
        
        # IMPROVED: Enhance analysis with session context
        if is_followup and state.get("session_context"):
            ctx = state["session_context"]
            if hasattr(ctx, 'visa_types_mentioned') and ctx.visa_types_mentioned:
                for visa_type in ctx.visa_types_mentioned:
                    if visa_type not in structured_analysis["visa_focus"]:
                        structured_analysis["visa_focus"].append(visa_type)
                print(f"📋 Enhanced with session visa types: {ctx.visa_types_mentioned}")
        
        # IMPROVED: Better success logging
        print(f"✅ Manager strategic analysis completed:")
        print(f"   📊 Question type: {structured_analysis['question_type']}")
        print(f"   🎯 Complexity: {structured_analysis['complexity']}")
        print(f"   🔧 Tools recommended: {len(structured_analysis['required_tools'])}")
        print(f"   📄 RAG context: {'✅' if rag_response_content else '❌'} ({len(rag_response_content)} chars)")
        if is_followup:
            print(f"   🔗 Session-aware: ✅")

        return {
            "manager_decision": strategic_decision,
            "structured_analysis": structured_analysis,
            "tool_results": tool_results,
            "tools_used": [call['name'] for call in tool_calls] if tool_calls else (["rag_retrieval_tool"] if rag_response_content else []),
            "rag_response": rag_response_content,
            "workflow_parameters": {
                "question_type": structured_analysis["question_type"],
                "complexity": structured_analysis["complexity"],
                "primary_focus": structured_analysis["primary_focus"],
                "required_tools": structured_analysis["required_tools"],
                "information_depth": structured_analysis["information_depth"],
                "search_keywords": structured_analysis["search_keywords"],
                "session_aware": bool(session_id),
                "is_followup": is_followup,
                "visa_focus": structured_analysis["visa_focus"]
            }
        }
        
    except Exception as e:
        error_msg = f"Manager strategic analysis failed: {str(e)}"
        print(f"❌ Manager error: {error_msg}")
        
        # IMPROVED: Better fallback strategy with session awareness
        fallback_strategy = {
            "question_type": "factual",
            "complexity": "medium", 
            "primary_focus": "immigration information",
            "required_tools": ["rag_retrieval_tool"],
            "information_depth": "detailed",
            "visa_focus": [],
            "search_keywords": ["immigration", "USCIS"]
        }
        
        # Try to infer some basic information from the question
        question_lower = user_question.lower()
        if any(word in question_lower for word in ["f-1", "f1", "student"]):
            fallback_strategy["visa_focus"] = ["F-1"]
            fallback_strategy["primary_focus"] = "F-1 student visa information"
        elif any(word in question_lower for word in ["h-1b", "h1b", "work"]):
            fallback_strategy["visa_focus"] = ["H-1B"]
            fallback_strategy["primary_focus"] = "H-1B work visa information"
        
        return {
            "manager_decision": f"Fallback analysis due to error: {error_msg}",
            "structured_analysis": fallback_strategy,
            "tool_results": {},
            "tools_used": [],
            "rag_response": "",
            "workflow_parameters": fallback_strategy,
            "error": error_msg
        }