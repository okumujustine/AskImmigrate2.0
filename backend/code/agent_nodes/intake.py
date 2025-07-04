from backend.code.agentic_state import ImmigrationState
import re
from typing import Dict
import spacy
nlp = spacy.load("en_core_web_sm")


def extract_country(text: str) -> str:
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ == "GPE":  # Geo-Political Entity (country, city, state)
            country = ent.text.strip()
            if country.lower().startswith("the "):
                country = country[4:]
            return country
    return None

def intake_node(state: ImmigrationState) -> dict:
    user_question = state.get("user_question", "")
    visa_type = None
    visa_matches = re.findall(r"\b(F-1|J-1|B-2|H-1B|CPT|OPT|STEM OPT|H-4|L-1|EB-\d)\b", user_question, re.IGNORECASE)
    if visa_matches:
        #visa_type = visa_match.group(1).upper()
        visa_type = visa_matches[-1].upper()  # Get the last match for more specific visa types
    country = state.get("country") or extract_country(user_question)
    return {
        "user_question": user_question,
        "visa_type": visa_type,
        "country": country,
    }