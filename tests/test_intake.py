from backend.agent_nodes.intake import intake_node

def test_extract_country_and_visa():
    state = {"user_question": "Can I switch from B-2 to F-1 if I am from Uganda?"}
    result = intake_node(state)
    assert result["visa_type"] == "F-1"
    assert result["country"] == "Uganda"

def test_no_country():
    state = {"user_question": "How do I get OPT?"}
    result = intake_node(state)
    assert result["visa_type"] == "OPT"
    assert result["country"] is None

def test_gpe_variations():
    state = {"user_question": "I'm applying from the United States for STEM OPT."}
    result = intake_node(state)
    assert result["country"] == "United States"
    assert result["visa_type"] == "STEM OPT"
