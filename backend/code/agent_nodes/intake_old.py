from backend.code.agentic_state import ImmigrationState
import re
from typing import Dict

def intake_node(state: ImmigrationState) -> Dict:
    """
    Parse and validate the user's immigration question.
    Extract visa type and country where possible.
    Fill relevant fields in ImmigrationState.
    """
   
    user_question = state.get("user_question", "")

  
    visa_type = None
    visa_match = re.search(r"\b(F-1|J-1|CPT|B-2|H-1B|OPT|STEM OPT|H-4|L-1|EB-\d)\b", user_question, re.IGNORECASE)
    if visa_match:
        visa_type = visa_match.group(1).upper()

    # 3. exract country if not already set [to be improved ]
    country = state.get("country")
    if not country:
        country_match = re.search(r"\bfrom ([A-Za-z ]+)\b", user_question, re.IGNORECASE)
        if country_match:
            country = country_match.group(1).strip()

    # 4. Return new state fields to update
    return {
        "user_question": user_question,
        "visa_type": visa_type,
        "country": country,
    }
