"""AHCP AI Service extracted from ACP.ipynb and adapted for standalone use."""
from __future__ import annotations
import os, secrets, logging, json, re
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
import numpy as np
from fastapi import FastAPI, Depends, Header, HTTPException
from pydantic import BaseModel, Field
try:
    from openai import OpenAI, RateLimitError
except ImportError:  # Allows offline API tests before optional LLM dependency is installed.
    OpenAI = None
    class RateLimitError(Exception):
        pass

logger = logging.getLogger("ahcp_ai")
BASE_DIR = Path(__file__).resolve().parent
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass

_raw_kdir = os.getenv("AHCP_KNOWLEDGE_DIR")
if _raw_kdir:
    _kpath = Path(_raw_kdir)
    if not _kpath.is_absolute():
        _kpath = (BASE_DIR / _kpath).resolve()
else:
    _kpath = (BASE_DIR / "knowledge").resolve()
KNOWLEDGE_DIR = _kpath
CACHE_DIR = KNOWLEDGE_DIR / ".cache"

EMBEDDING_MODEL_NAME = os.getenv("AHCP_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
AI_SERVICE_API_KEY = os.getenv("AHCP_AI_SERVICE_API_KEY", "")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")
CHUNK_SIZE, CHUNK_OVERLAP = 800, 150
conversation_store: dict[str, dict[str, Any]] = {}
chunks: list[dict[str, Any]] = []
chunk_texts: list[str] = []
embedding_model = None
faiss_index = None
knowledge_load_error = None


def is_valid_openrouter_key(key: str | None) -> bool:
    """Return True only if the key is non-empty and not a template/placeholder string."""
    if not key:
        return False
    k = str(key).strip()
    if not k or len(k) < 15:
        return False
    lower = k.lower()
    if (
        "replace" in lower
        or "your-openrouter" in lower
        or "your_openrouter" in lower
        or "your-key" in lower
        or lower in ("none", "null", "undefined")
        or lower.startswith("sk-or-placeholder")
    ):
        return False
    return True



# Notebook source: latest definition of QUESTIONNAIRE
QUESTIONNAIRE = {
    1: {"key": "full_name", "category": "Personal Information", "question": "What is your full legal name?", "type": "text"},
    2: {"key": "date_of_birth", "category": "Personal Information", "question": "What is your date of birth?", "type": "text"},
    3: {"key": "gender", "category": "Personal Information", "question": "What is your gender?", "type": "choice", "options": ["Male", "Female", "Other"]},
    4: {"key": "phone", "category": "Personal Information", "question": "What is your mobile phone number?", "type": "text"},
    5: {"key": "preferred_language", "category": "Personal Information", "question": "What language would you prefer for communication?", "type": "choice", "options": ["English", "Kannada"]},
    6: {"key": "current_address", "category": "Personal Information", "question": "What is your current residential address?", "type": "text"},
    7: {"key": "chronic_conditions", "category": "Medical Treatment Preferences", "question": "Do you have any chronic medical conditions?", "type": "text", "options": None},
    8: {"key": "serious_hospitalization", "category": "Medical Treatment Preferences", "question": "Have you ever had a serious hospitalization or major illness?", "type": "text", "options": None},
    9: {"key": "long_term_medications", "category": "Medical Treatment Preferences", "question": "What long-term medications do you currently take?", "type": "text", "options": None},
    10: {"key": "allergies", "category": "Medical Treatment Preferences", "question": "Do you have any known allergies to medications, food, or other substances?", "type": "text", "options": None},
    11: {"key": "cpr", "category": "Medical Treatment Preferences", "question": "If your heart stops beating, would you want Cardiopulmonary Resuscitation (CPR)?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    12: {"key": "ventilator", "category": "Medical Treatment Preferences", "question": "If you are unable to breathe on your own, would you want mechanical ventilation (a breathing machine / ventilator)?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    13: {"key": "dialysis", "category": "Medical Treatment Preferences", "question": "If your kidneys stop working, would you want kidney dialysis?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    14: {"key": "chemotherapy", "category": "Medical Treatment Preferences", "question": "What would you prefer regarding chemotherapy (cancer treatment)?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    15: {"key": "radiotherapy", "category": "Medical Treatment Preferences", "question": "What would you prefer regarding radiotherapy (radiation treatment)?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    16: {"key": "surgery", "category": "Medical Treatment Preferences", "question": "What would you prefer regarding major surgery or invasive operations?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    17: {"key": "artificial_hydration", "category": "Medical Treatment Preferences", "question": "Would you want artificial hydration, such as fluids given through a vein or tube, if you could not drink normally?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    18: {"key": "artificial_nutrition", "category": "Medical Treatment Preferences", "question": "Would you want artificial nutrition, such as feeding through a tube, if you could not eat normally?", "type": "choice", "options": ["Yes", "No", "Unsure"]},
    19: {"key": "goals_of_care", "category": "End-of-Life Preferences", "question": "What are your main goals of care?", "type": "choice", "options": ["Comfort-focused care", "Life-prolonging treatment", "A balance of comfort and life-prolonging treatment", "Unsure"]},
    20: {"key": "preferred_place_of_care", "category": "End-of-Life Preferences", "question": "Where would you prefer to receive care if you have a serious or life-limiting illness?", "type": "choice", "options": ["Home", "Hospital", "Hospice", "No preference", "Unsure"]},
    21: {"key": "preferred_hospital", "category": "End-of-Life Preferences", "question": "Do you have a preferred hospital or healthcare facility? (Optional)", "type": "text", "options": ["No preference", "Skip"]},
    22: {"key": "preferred_physician_name", "category": "End-of-Life Preferences", "question": "Do you have a preferred treating clinician or physician? (Optional)", "type": "text", "options": ["No preference", "Skip"]},
    23: {"key": "personal_values", "category": "End-of-Life Preferences", "question": "What are your most important personal values, spiritual beliefs, or care priorities?", "type": "text"},
    24: {"key": "level_of_medical_intervention", "category": "End-of-Life Preferences", "question": "What level of medical intervention would you prefer?", "type": "choice", "options": ["Full medical treatment", "Limited medical treatment", "Comfort-focused treatment", "Unsure"]},
    25: {"key": "additional_wishes", "category": "End-of-Life Preferences", "question": "Do you have any additional wishes or instructions you would like to record?", "type": "text", "options": ["No additional wishes", "Skip"]},
    26: {"key": "healthcare_decision_maker", "category": "Designated Healthcare Representative", "question": "Who would you like to appoint as your primary healthcare representative (healthcare proxy) to make decisions if you are unable to?", "type": "text"},
    27: {"key": "decision_maker_relationship", "category": "Designated Healthcare Representative", "question": "What is your relationship with this representative?", "type": "text"},
    28: {"key": "decision_maker_phone", "category": "Designated Healthcare Representative", "question": "What is your primary representative's mobile phone number?", "type": "text"},
    29: {"key": "decision_maker_email", "category": "Designated Healthcare Representative", "question": "What is your primary representative's email address?", "type": "text", "options": None},
    30: {"key": "decision_maker_address", "category": "Designated Healthcare Representative", "question": "What is your primary representative's residential address?", "type": "text", "options": ["Same as my address"]},
    31: {"key": "appoint_alternate_representative", "category": "Designated Healthcare Representative", "question": "Would you like to appoint an alternate healthcare representative in case your primary representative is unavailable or unable to act?", "type": "choice", "options": ["Yes", "No"]},
    32: {"key": "alternate_decision_maker", "category": "Designated Healthcare Representative", "question": "What is your alternate healthcare representative's full name?", "type": "text"},
    33: {"key": "alternate_decision_maker_relationship", "category": "Designated Healthcare Representative", "question": "What is your relationship with this alternate representative?", "type": "text"},
    34: {"key": "alternate_decision_maker_phone", "category": "Designated Healthcare Representative", "question": "What is your alternate representative's mobile phone number?", "type": "text"},
    35: {"key": "alternate_decision_maker_email", "category": "Designated Healthcare Representative", "question": "What is your alternate representative's email address?", "type": "text", "options": None},
    36: {"key": "alternate_decision_maker_address", "category": "Designated Healthcare Representative", "question": "What is your alternate representative's residential address?", "type": "text", "options": ["Same as my address"]},
    37: {"key": "organ_donation", "category": "Organ Donation", "question": "Would you like to donate your organs after death?", "type": "choice", "options": ["Yes", "No"]},
    38: {"key": "body_donation", "category": "Organ Donation", "question": "In addition to organ donation, would you like to donate your body for medical education and research after death?", "type": "choice", "options": ["Yes", "No"]},
    39: {"key": "last_rites", "category": "Organ Donation", "question": "Do you have any spiritual, cultural, or last rites / funeral wishes?", "type": "text", "options": ["No specific wishes", "Skip"]},
    40: {"key": "permanent_address", "category": "Personal Information", "question": "What is your permanent residential address?", "type": "text", "options": ["Same as current address", "Skip"]},
    41: {"key": "government_id_type", "category": "Personal Information", "question": "What type of Government ID would you like to provide? (Optional)", "type": "choice", "options": ["Aadhaar", "Passport", "Driving License", "Voter ID", "Skip"]},
    42: {"key": "government_id_number", "category": "Personal Information", "question": "Please enter your Government ID number", "type": "text", "options": ["Skip"]},
    43: {"key": "municipality_panchayat", "category": "Personal Information", "question": "What is your Municipality or Gram Panchayat?", "type": "text", "options": ["Skip"]},
    44: {"key": "review", "category": "Confirmation & Review", "question": "Please review your complete Advance Care Plan below. When you are ready, confirm to finalize your record, or choose an option to make edits:", "type": "choice", "options": ["Confirm & Complete ACP", "Edit Personal Details", "Edit Medical Treatments", "Edit End-of-Life Wishes", "Edit Healthcare Representative", "Edit Donation Preferences"]},
}

# Notebook source: latest definition of LANGUAGE_TEXT
LANGUAGE_TEXT = {
    "en": {
        1: {"question": "What is your full legal name?", "options": None},
        2: {"question": "What is your date of birth?", "options": None},
        3: {"question": "What is your gender?", "options": ["Male", "Female", "Other"]},
        4: {"question": "What is your mobile phone number?", "options": None},
        5: {"question": "What language would you prefer for communication?", "options": ["English", "Kannada"]},
        6: {"question": "What is your current residential address?", "options": None},
        7: {"question": "Do you have any chronic medical conditions?", "options": None},
        8: {"question": "Have you ever had a serious hospitalization or major illness?", "options": None},
        9: {"question": "What long-term medications do you currently take?", "options": None},
        10: {"question": "Do you have any known allergies to medications, food, or other substances?", "options": None},
        11: {"question": "If your heart stops beating, would you want Cardiopulmonary Resuscitation (CPR)?", "options": ["Yes", "No", "Unsure"]},
        12: {"question": "If you are unable to breathe on your own, would you want mechanical ventilation (a breathing machine / ventilator)?", "options": ["Yes", "No", "Unsure"]},
        13: {"question": "If your kidneys stop working, would you want kidney dialysis?", "options": ["Yes", "No", "Unsure"]},
        14: {"question": "What would you prefer regarding chemotherapy (cancer treatment)?", "options": ["Yes", "No", "Unsure"]},
        15: {"question": "What would you prefer regarding radiotherapy (radiation treatment)?", "options": ["Yes", "No", "Unsure"]},
        16: {"question": "What would you prefer regarding major surgery or invasive operations?", "options": ["Yes", "No", "Unsure"]},
        17: {"question": "Would you want artificial hydration, such as fluids given through a vein or tube, if you could not drink normally?", "options": ["Yes", "No", "Unsure"]},
        18: {"question": "Would you want artificial nutrition, such as feeding through a tube, if you could not eat normally?", "options": ["Yes", "No", "Unsure"]},
        19: {"question": "What are your main goals of care?", "options": ["Comfort-focused care", "Life-prolonging treatment", "A balance of comfort and life-prolonging treatment", "Unsure"]},
        20: {"question": "Where would you prefer to receive care if you have a serious or life-limiting illness?", "options": ["Home", "Hospital", "Hospice", "No preference", "Unsure"]},
        21: {"question": "Do you have a preferred hospital or healthcare facility? (Optional)", "options": ["No preference", "Skip"]},
        22: {"question": "Do you have a preferred treating clinician or physician? (Optional)", "options": ["No preference", "Skip"]},
        23: {"question": "What are your most important personal values, spiritual beliefs, or care priorities?", "options": None},
        24: {"question": "What level of medical intervention would you prefer?", "options": ["Full medical treatment", "Limited medical treatment", "Comfort-focused treatment", "Unsure"]},
        25: {"question": "Do you have any additional wishes or instructions you would like to record?", "options": ["No additional wishes", "Skip"]},
        26: {"question": "Who would you like to appoint as your primary healthcare representative (healthcare proxy) to make decisions if you are unable to?", "options": None},
        27: {"question": "What is your relationship with this representative?", "options": None},
        28: {"question": "What is your primary representative's mobile phone number?", "options": None},
        29: {"question": "What is your primary representative's email address?", "options": None},
        30: {"question": "What is your primary representative's residential address?", "options": ["Same as my address"]},
        31: {"question": "Would you like to appoint an alternate healthcare representative in case your primary representative is unavailable or unable to act?", "options": ["Yes", "No"]},
        32: {"question": "What is your alternate healthcare representative's full name?", "options": None},
        33: {"question": "What is your relationship with this alternate representative?", "options": None},
        34: {"question": "What is your alternate representative's mobile phone number?", "options": None},
        35: {"question": "What is your alternate representative's email address?", "options": None},
        36: {"question": "What is your alternate representative's residential address?", "options": ["Same as my address"]},
        37: {"question": "Would you like to donate your organs after death?", "options": ["Yes", "No"]},
        38: {"question": "In addition to organ donation, would you like to donate your body for medical education and research after death?", "options": ["Yes", "No"]},
        39: {"question": "Do you have any spiritual, cultural, or last rites / funeral wishes?", "options": ["No specific wishes", "Skip"]},
        40: {"question": "What is your permanent residential address?", "options": ["Same as current address", "Skip"]},
        41: {"question": "What type of Government ID would you like to provide? (Optional)", "options": ["Aadhaar", "Passport", "Driving License", "Voter ID", "Skip"]},
        42: {"question": "Please enter your Government ID number", "options": ["Skip"]},
        43: {"question": "What is your Municipality or Gram Panchayat?", "options": ["Skip"]},
        44: {"question": "Please review your complete Advance Care Plan below. When you are ready, confirm to finalize your record, or choose an option to make edits:", "options": ["Confirm & Complete ACP", "Edit Personal Details", "Edit Medical Treatments", "Edit End-of-Life Wishes", "Edit Healthcare Representative", "Edit Donation Preferences"]}
    },
    "kn": {
        1: {"question": "ನಿಮ್ಮ ಪೂರ್ಣ ಕಾನೂನುಬದ್ಧ ಹೆಸರು ಏನು?", "options": None},
        2: {"question": "ನಿಮ್ಮ ಜನ್ಮ ದಿನಾಂಕ ಏನು?", "options": None},
        3: {"question": "ನಿಮ್ಮ ಲಿಂಗ ಯಾವುದು?", "options": ["ಪುರುಷ", "ಮಹಿಳೆ", "ಇತರೆ"]},
        4: {"question": "ನಿಮ್ಮ ಮೊಬೈಲ್ ದೂರವಾಣಿ ಸಂಖ್ಯೆ ಏನು?", "options": None},
        5: {"question": "ಸಂವಹನಕ್ಕಾಗಿ ನಿಮ್ಮ ಆದ್ಯತೆಯ ಭಾಷೆ ಯಾವುದು?", "options": ["English", "Kannada"]},
        6: {"question": "ನಿಮ್ಮ ಪ್ರಸ್ತುತ ವಾಸಸ್ಥಳದ ವಿಳಾಸವೇನು?", "options": None},
        7: {"question": "ನಿಮಗೆ ಯಾವುದೇ ದೀರ್ಘಕಾಲದ ವೈದ್ಯಕೀಯ ಕಾಯಿಲೆಗಳಿವೆಯೇ?", "options": None},
        8: {"question": "ನೀವು ಎಂದಾದರೂ ಗಂಭೀರ ಕಾಯಿಲೆಯಿಂದ ಆಸ್ಪತ್ರೆಗೆ ದಾಖಲಾಗಿದ್ದೀರಾ ಅಥವಾ ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಗೆ ಒಳಗಾಗಿದ್ದೀರಾ?", "options": None},
        9: {"question": "ನೀವು ಪ್ರಸ್ತುತ ನಿಯಮಿತವಾಗಿ ತೆಗೆದುಕೊಳ್ಳುತ್ತಿರುವ ದೀರ್ಘಕಾಲದ ಔಷಧಿಗಳು ಯಾವುವು?", "options": None},
        10: {"question": "ನಿಮಗೆ ಔಷಧಿಗಳು, ಆಹಾರ ಅಥವಾ ಇತರ ವಸ್ತುಗಳಿಂದ ಯಾವುದೇ ಅಲರ್ಜಿಗಳಿವೆಯೇ?", "options": None},
        11: {"question": "ನಿಮ್ಮ ಹೃದಯ ಬಡಿತ ನಿಂತುಹೋದರೆ, CPR (ಹೃದಯ ಪುನರುಜ್ಜೀವನ ಚಿಕಿತ್ಸೆ) ಮಾಡಿಸಲು ನೀವು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        12: {"question": "ನೀವು ಸ್ವತಃ ಉಸಿರಾಡಲು ಸಾಧ್ಯವಾಗದಿದ್ದರೆ, ಯಾಂತ್ರಿಕ ವೆಂಟಿಲೇಟರ್ (ಕೃತಕ ಉಸಿರಾಟ ಯಂತ್ರ) ಸಹಾಯವನ್ನು ಪಡೆಯಲು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        13: {"question": "ನಿಮ್ಮ ಮೂತ್ರಪಿಂಡಗಳು ಕೆಲಸ ಮಾಡುವುದನ್ನು ನಿಲ್ಲಿಸಿದರೆ, ಡಯಾಲಿಸಿಸ್ ಚಿಕಿತ್ಸೆಯನ್ನು ಮಾಡಿಸಲು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        14: {"question": "ಕೀಮೋಥೆರಪಿ (ಕ್ಯಾನ್ಸರ್ ಚಿಕಿತ್ಸೆ) ಕುರಿತು ನಿಮ್ಮ ಆದ್ಯತೆ ಏನು?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        15: {"question": "ರೇಡಿಯೋಥೆರಪಿ (ವಿಕಿರಣ ಚಿಕಿತ್ಸೆ) ಕುರಿತು ನಿಮ್ಮ ಆದ್ಯತೆ ಏನು?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        16: {"question": "ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆ ಅಥವಾ ಆಕ್ರಮಣಕಾರಿ ಕಾರ್ಯಾಚರಣೆಗಳ (Major Surgery) ಕುರಿತು ನಿಮ್ಮ ಆದ್ಯತೆ ಏನು?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        17: {"question": "ನೀವು ನೀರನ್ನು ಕುಡಿಯಲು ಅಸಮರ್ಥರಾದಾಗ, ನರಗಳ ಮೂಲಕ IV ದ್ರವಗಳನ್ನು ಅಥವಾ ಕೃತಕ ಜಲಸಂಚಾರವನ್ನು ಪಡೆಯಲು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        18: {"question": "ನೀವು ನೈಸರ್ಗಿಕವಾಗಿ ಆಹಾರವನ್ನು ಸೇವಿಸಲು ಅಸಮರ್ಥರಾದಾಗ, ಟ್ಯೂಬ್ ಮೂಲಕ ಕೃತಕ ಪೋಷಣೆಯನ್ನು (Tube Feeding) ಪಡೆಯಲು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        19: {"question": "ನಿಮ್ಮ ಆರೈಕೆಯ ಮುಖ್ಯ ಗುರಿಗಳು ಯಾವುವು?", "options": ["ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಆರೈಕೆ", "ಜೀವನವನ್ನು ದೀರ್ಘಗೊಳಿಸುವ ಚಿಕಿತ್ಸೆ", "ಆರಾಮ ಮತ್ತು ಜೀವನವನ್ನು ದೀರ್ಘಗೊಳಿಸುವ ಚಿಕಿತ್ಸೆಯ ಸಮತೋಲನ", "ಖಚಿತವಿಲ್ಲ"]},
        20: {"question": "ನೀವು ಗಂಭೀರ ಕಾಯಿಲೆಯನ್ನು ಹೊಂದಿದ್ದರೆ ಎಲ್ಲಿ ಆರೈಕೆ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ?", "options": ["ಮನೆ", "ಆಸ್ಪತ್ರೆ", "ಹಾಸ್ಪಿಸ್ ಅಥವಾ ಪ್ಯಾಲಿಯೇಟಿವ್ ಆರೈಕೆ ಕೇಂದ್ರ", "ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"]},
        21: {"question": "ನೀವು ಆದ್ಯತೆ ನೀಡುವ ಆಸ್ಪತ್ರೆ ಅಥವಾ ಆರೋಗ್ಯ ಕೇಂದ್ರ ಇದೆಯೇ? (ಐಚ್ಛಿಕ)", "options": ["ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ", "Skip"]},
        22: {"question": "ನೀವು ಆದ್ಯತೆ ನೀಡುವ ವೈದ್ಯರ ಹೆಸರು ಇದೆಯೇ? (ಐಚ್ಛಿಕ)", "options": ["ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ", "Skip"]},
        23: {"question": "ನಿಮ್ಮ ಜೀವನದಲ್ಲಿ ನೀವು ಹೆಚ್ಚು ಪ್ರಾಮುಖ್ಯತೆ ನೀಡುವ ವೈಯಕ್ತಿಕ ಮೌಲ್ಯಗಳು ಅಥವಾ ಆರೈಕೆಯ ಆದ್ಯತೆಗಳು ಯಾವುವು?", "options": None},
        24: {"question": "ನೀವು ಯಾವ ಮಟ್ಟದ ವೈದ್ಯಕೀಯ ಹಸ್ತಕ್ಷೇಪವನ್ನು ಬಯಸುತ್ತೀರಿ?", "options": ["ಪೂರ್ಣ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ", "ಸೀಮಿತ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ", "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಚಿಕಿತ್ಸೆ", "ಖಚಿತವಿಲ್ಲ"]},
        25: {"question": "ನೀವು ದಾಖಲಿಸಲು ಬಯಸುವ ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಆಶಯಗಳು ಅಥವಾ ಸೂಚನೆಗಳಿವೆಯೇ?", "options": ["ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಆಶಯಗಳಿಲ್ಲ", "Skip"]},
        26: {"question": "ನೀವು ಸ್ವತಃ ನಿರ್ಧಾರಗಳನ್ನು ತೆಗೆದುಕೊಳ್ಳಲು ಸಾಧ್ಯವಾಗದಿದ್ದರೆ, ನಿಮ್ಮ ಮುಖ್ಯ ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯಾಗಿ ಯಾರನ್ನು ನೇಮಿಸಲು ಬಯಸುತ್ತೀರಿ? ಅವರ ಪೂರ್ಣ ಹೆಸರನ್ನು ನಮೂದಿಸಿ.", "options": None},
        27: {"question": "ಈ ಪ್ರತಿನಿಧಿಯೊಂದಿಗೆ ನಿಮ್ಮ ಸಂಬಂಧವೇನು?", "options": None},
        28: {"question": "ನಿಮ್ಮ ಮುಖ್ಯ ಪ್ರತಿನಿಧಿಯ ಮೊಬೈಲ್ ದೂರವಾಣಿ ಸಂಖ್ಯೆಯನ್ನು ನೀಡಿ:", "options": None},
        29: {"question": "ನಿಮ್ಮ ಮುಖ್ಯ ಪ್ರತಿನಿಧಿಯ ಇಮೇಲ್ ವಿಳಾಸವನ್ನು ನೀಡಿ:", "options": None},
        30: {"question": "ನಿಮ್ಮ ಮುಖ್ಯ ಪ್ರತಿನಿಧಿಯ ವಾಸಸ್ಥಳದ ವಿಳಾಸವೇನು?", "options": ["ನನ್ನ ವಿಳಾಸದಂತೆಯೇ"]},
        31: {"question": "ನಿಮ್ಮ ಮುಖ್ಯ ಪ್ರತಿನಿಧಿ ಅಲಭ್ಯರಾಗಿದ್ದರೆ ಅವರ ಬದಲಿಗೆ ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳಲು ಪರ್ಯಾಯ ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ನೇಮಿಸಲು ನೀವು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ"]},
        32: {"question": "ನಿಮ್ಮ ಪರ್ಯಾಯ ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯ ಪೂರ್ಣ ಹೆಸರು ಏನು?", "options": None},
        33: {"question": "ಈ ಪರ್ಯಾಯ ಪ್ರತಿನಿಧಿಯೊಂದಿಗೆ ನಿಮ್ಮ ಸಂಬಂಧವೇನು?", "options": None},
        34: {"question": "ಅವರ ಮೊಬೈಲ್ ದೂರವಾಣಿ ಸಂಖ್ಯೆಯನ್ನು ನೀಡಿ:", "options": None},
        35: {"question": "ಅವರ ಇಮೇಲ್ ವಿಳಾಸವನ್ನು ನೀಡಿ:", "options": None},
        36: {"question": "ಅವರ ವಾಸಸ್ಥಳದ ವಿಳಾಸವೇನು?", "options": ["ನನ್ನ ವಿಳಾಸದಂತೆಯೇ"]},
        37: {"question": "ನಿಮ್ಮ ಮರಣಾನಂತರ ಅಂಗಗಳನ್ನು ದಾನ ಮಾಡಲು ನೀವು ಬಯಸುವಿರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ"]},
        38: {"question": "ಅಂಗದಾನದ ಜೊತೆಗೆ, ಮರಣದ ನಂತರ ನಿಮ್ಮ ದೇಹವನ್ನು ವೈದ್ಯಕೀಯ ಶಿಕ್ಷಣ ಮತ್ತು ಸಂಶೋಧನೆಗಾಗಿ ದಾನ ಮಾಡಲು ನೀವು ಬಯಸುತ್ತೀರಾ?", "options": ["ಹೌದು", "ಇಲ್ಲ"]},
        39: {"question": "ನಿಮ್ಮ ಅಂತ್ಯಕ್ರಿಯೆ ಅಥವಾ ಕೊನೆಯ ವಿಧಿಗಳ ಬಗ್ಗೆ ಆಶಯಗಳಿವೆಯೇ?", "options": ["ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ಆಶಯವಿಲ್ಲ", "Skip"]},
        40: {"question": "ನಿಮ್ಮ ಖಾಯಂ ವಾಸಸ್ಥಳದ ವಿಳಾಸವೇನು?", "options": ["ಪ್ರಸ್ತುತ ವಿಳಾಸದಂತೆಯೇ", "Skip"]},
        41: {"question": "ನೀವು ಯಾವ ಸರ್ಕಾರಿ ಗುರುತಿನ ಚೀಟಿಯನ್ನು ನೀಡಲು ಬಯಸುತ್ತೀರಿ? (ಐಚ್ಛಿಕ)", "options": ["Aadhaar", "Passport", "Driving License", "Voter ID", "Skip"]},
        42: {"question": "ನಿಮ್ಮ ಸರ್ಕಾರಿ ಗುರುತಿನ ಚೀಟಿಯ ಸಂಖ್ಯೆಯನ್ನು ನಮೂದಿಸಿ", "options": ["Skip"]},
        43: {"question": "ನಿಮ್ಮ ಪುರಸಭೆ ಅಥವಾ ಗ್ರಾಮ ಪಂಚಾಯಿತಿ ಯಾವುದು?", "options": ["Skip"]},
        44: {"question": "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯ ಪೂರ್ಣ ಸಾರಾಂಶವನ್ನು ಪರಿಶೀಲಿಸಿ. ಸಿದ್ಧವಾದಾಗ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ, ಅಥವಾ ಬದಲಾವಣೆ ಮಾಡಲು ಆಯ್ಕೆಮಾಡಿ:", "options": ["ನನ್ನ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ", "ವೈಯಕ್ತಿಕ ವಿವರಗಳನ್ನು ತಿದ್ದು", "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು", "ಆರೈಕೆ ಆದ್ಯತೆಗಳನ್ನು ತಿದ್ದು", "ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ತಿದ್ದು", "ದಾನದ ನಿರ್ಧಾರಗಳನ್ನು ತಿದ್ದು"]}
    }
}

# Notebook source: latest definition of ANSWER_NORMALIZATION
ANSWER_NORMALIZATION = {
    # --- Gender Q3 ---
    "male": "Male",
    "m": "Male",
    "ಪುರುಷ": "Male",
    "female": "Female",
    "f": "Female",
    "ಮಹಿಳೆ": "Female",
    "other": "Other",
    "non-binary": "Other",
    "ಇತರೆ": "Other",

    # --- Language Q5 ---
    "english": "English",
    "en": "English",
    "ಇಂಗ್ಲಿಷ್": "English",
    "kannada": "Kannada",
    "kn": "Kannada",
    "ಕನ್ನಡ": "Kannada",

    # --- Yes / No / Unsure (Q11-Q18, Q31, Q37, Q38) ---
    "yes": "Yes",
    "y": "Yes",
    "ಹೌದು": "Yes",
    "i want this treatment": "Yes",
    "want": "Yes",
    "ಬಯಸುತ್ತೇನೆ": "Yes",

    "no": "No",
    "n": "No",
    "ಇಲ್ಲ": "No",
    "i do not want this treatment": "No",
    "do not want": "No",
    "don't want": "No",
    "ಬೇಡ": "No",
    "ಬಯಸುವುದಿಲ್ಲ": "No",

    "unsure": "Unsure",
    "not sure": "Unsure",
    "undecided": "Unsure",
    "unsure / undecided": "Unsure",
    "ಖಚಿತವಿಲ್ಲ": "Unsure",
    "ತೀರ್ಮಾನಿಸಿಲ್ಲ": "Unsure",

    # --- Goals of care Q19 ---
    "comfort-focused care": "Comfort-focused care",
    "comfort focused care": "Comfort-focused care",
    "comfort": "Comfort-focused care",
    "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಆರೈಕೆ": "Comfort-focused care",
    "life-prolonging treatment": "Life-prolonging treatment",
    "life prolonging treatment": "Life-prolonging treatment",
    "life prolonging": "Life-prolonging treatment",
    "ಜೀವನವನ್ನು ದೀರ್ಘಗೊಳಿಸುವ ಚಿಕಿತ್ಸೆ": "Life-prolonging treatment",
    "a balance of comfort and life-prolonging treatment": "A balance of comfort and life-prolonging treatment",
    "balance of comfort and life-prolonging treatment": "A balance of comfort and life-prolonging treatment",
    "balance": "A balance of comfort and life-prolonging treatment",
    "ಆರಾಮ ಮತ್ತು ಜೀವನವನ್ನು ದೀರ್ಘಗೊಳಿಸುವ ಚಿಕಿತ್ಸೆಯ ಸಮತೋಲನ": "A balance of comfort and life-prolonging treatment",

    # --- Preferred place of care Q20 ---
    "home": "Home",
    "ಮನೆ": "Home",
    "hospital": "Hospital",
    "ಆಸ್ಪತ್ರೆ": "Hospital",
    "hospice": "Hospice",
    "hospice or palliative care centre": "Hospice",
    "hospice or palliative care facility": "Hospice",
    "ಹಾಸ್ಪಿಸ್ ಅಥವಾ ಪ್ಯಾಲಿಯೇಟಿವ್ ಆರೈಕೆ ಕೇಂದ್ರ": "Hospice",
    "ಹಾಸ್ಪಿಸ್": "Hospice",
    "no preference": "No preference",
    "ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ": "No preference",
    "ಯಾವುದೇ ಆದ್ಯತೆಯಿಲ್ಲ": "No preference",

    # --- Level of medical intervention Q24 ---
    "full medical treatment": "Full medical treatment",
    "full treatment": "Full medical treatment",
    "full": "Full medical treatment",
    "ಪೂರ್ಣ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ": "Full medical treatment",
    "limited medical treatment": "Limited medical treatment",
    "limited treatment": "Limited medical treatment",
    "limited": "Limited medical treatment",
    "ಸೀಮಿತ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ": "Limited medical treatment",
    "comfort-focused treatment": "Comfort-focused treatment",
    "comfort treatment": "Comfort-focused treatment",
    "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಚಿಕಿತ್ಸೆ": "Comfort-focused treatment",

    # --- Address Q30, Q36 ---
    "same as my address": "Same as my address",
    "ನನ್ನ ವಿಳಾಸದಂತೆಯೇ": "Same as my address",

    # --- Permanent Address Q40 ---
    "same as current address": "Same as current address",
    "ಪ್ರಸ್ತುತ ವಿಳಾಸದಂತೆಯೇ": "Same as current address",

    # --- General Skip / Wishes ---
    "skip": "Skip",
    "ಬಿಟ್ಟುಬಿಡಿ": "Skip",
    "no specific wishes": "No specific wishes",
    "ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ಆಶಯವಿಲ್ಲ": "No specific wishes",
    "ಯಾವುದೇ ಆಶಯವಿಲ್ಲ": "No specific wishes",
    "no additional wishes": "No additional wishes",
    "ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಆಶಯಗಳಿಲ್ಲ": "No additional wishes",
    "ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಆಶಯವಿಲ್ಲ": "No additional wishes",

    # --- Government ID Type Q41 ---
    "aadhaar": "Aadhaar",
    "aadhar": "Aadhaar",
    "ಆಧಾರ್": "Aadhaar",
    "passport": "Passport",
    "ಪಾಸ್‌ಪೋರ್ಟ್": "Passport",
    "driving license": "Driving License",
    "driving licence": "Driving License",
    "dl": "Driving License",
    "ಡ್ರೈವಿಂಗ್ ಲೈಸೆನ್ಸ್": "Driving License",
    "voter id": "Voter ID",
    "voter card": "Voter ID",
    "ಮತದಾರರ ಗುರುತಿನ ಚೀಟಿ": "Voter ID",
    "ಮತದಾರರ ಐಡಿ": "Voter ID",

    # --- Review Q44 ---
    "confirm & complete acp": "Confirm & Complete ACP",
    "confirm plan": "Confirm & Complete ACP",
    "complete acp": "Confirm & Complete ACP",
    "confirm": "Confirm & Complete ACP",
    "ನನ್ನ ಯೋಜನೆಯನ್ನು ದೃಢೀಕರಿಸಿ": "Confirm & Complete ACP",
    "ದೃಢೀಕರಿಸಿ": "Confirm & Complete ACP",
    "edit personal details": "Edit Personal Details",
    "ವೈಯಕ್ತಿಕ ವಿವರಗಳನ್ನು ತಿದ್ದು": "Edit Personal Details",
    "edit medical treatments": "Edit Medical Treatments",
    "ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಗಳನ್ನು ತಿದ್ದು": "Edit Medical Treatments",
    "edit end-of-life wishes": "Edit End-of-Life Wishes",
    "ಆರೈಕೆ ಆದ್ಯತೆಗಳನ್ನು ತಿದ್ದು": "Edit End-of-Life Wishes",
    "edit healthcare representative": "Edit Healthcare Representative",
    "ಆರೋಗ್ಯ ಪ್ರತಿನಿಧಿಯನ್ನು ತಿದ್ದು": "Edit Healthcare Representative",
    "edit donation preferences": "Edit Donation Preferences",
    "ದಾನದ ನಿರ್ಧಾರಗಳನ್ನು ತಿದ್ದು": "Edit Donation Preferences",

    # --- Submenu actions ---
    "back to review": "Back to Review",
    "back": "Back to Review",
    "ಪರಿಶೀಲನೆಗೆ ಹಿಂತಿರುಗಿ": "Back to Review",
    "ಹಿಂತಿರುಗಿ": "Back to Review",
    "keep current value": "Keep Current Value",
    "keep": "Keep Current Value",
    "ಪ್ರಸ್ತುತ ಮೌಲ್ಯವನ್ನು ಇರಿಸಿ": "Keep Current Value",
}

# Notebook source: latest definition of TREATMENT_QUESTIONS
TREATMENT_QUESTIONS = {
    10: "CPR",
    11: "CPR",
    12: "mechanical ventilation",
    13: "dialysis",
    14: "chemotherapy",
    15: "radiotherapy",
    16: "major surgery",
    17: "artificial hydration",
    18: "artificial nutrition",
    19: "goals of care",
    20: "preferred place of care",
    24: "level of medical intervention",
    33: "chemotherapy",
    34: "radiotherapy",
    35: "major surgery",
}

def get_session(session_id):
    """Return a session, or None when the id is unknown."""
    return conversation_store.get(session_id)


def create_session(known_answers: dict[str, Any] | None = None):
    """
    Create a new conversation session.
    """

    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

    conversation_store[session_id] = {
        "messages": [],
        "patient_record": {k: v for k, v in (known_answers or {}).items() if v not in (None, "")},
        "current_question": None,
        "created_at": datetime.now().isoformat()
    }

    return session_id

def add_message(session_id, role, content):
    """
    Add a message to the conversation history.
    """

    session = get_session(session_id)

    session["messages"].append({
        "role": role,
        "content": content
    })

def get_conversation_history(session_id):
    """
    Return the conversation history for a session.
    """

    session = get_session(session_id)

    return session["messages"]

def start_questionnaire(session_id):
    """
    Start the AHCP questionnaire for an existing session.
    """

    session = get_session(session_id)

    session["current_question"] = 1
    session["patient_record"] = {}

    return get_current_question(session_id)

def get_current_question(session_id):
    """
    Return the current unanswered question.
    """

    session = get_session(session_id)

    question_number = session["current_question"]

    while question_number is not None and question_number <= len(QUESTIONNAIRE) and _question_is_already_answered(session, question_number):
        question_number += 1
    if question_number is not None and question_number > len(QUESTIONNAIRE):
        question_number = None
    session["current_question"] = question_number

    if question_number is None:
        return None

    question = QUESTIONNAIRE[question_number]
    question_text = LANGUAGE_TEXT.get(session.get("language", "en"), LANGUAGE_TEXT["en"])[question_number]["question"]
    options = LANGUAGE_TEXT.get(session.get("language", "en"), LANGUAGE_TEXT["en"])[question_number].get("options")
    if options is None:
        options = question.get("options", [])

    return {
        "question_number": question_number,
        "key": question["key"],
        "category": question["category"],
        "question": question_text,
        "type": question["type"],
        "options": options or []
    }


def _answer_is_present(value: Any) -> bool:
    return value is not None and str(value).strip() not in ("", "NOT SPECIFIED", "Pending", "pending@example.com")


def _question_is_already_answered(session: dict[str, Any], question_number: int) -> bool:
    record = session.get("patient_record", {})
    if question_number in QUESTIONNAIRE:
        key = QUESTIONNAIRE[question_number]["key"]
        return _answer_is_present(record.get(key))
    return False

def _labeled_answer_fields(answer: str, aliases: dict[str, tuple[str, ...]]) -> dict[str, str]:
    import re
    parsed = {}
    for key, labels in aliases.items():
        label_pattern = "|".join(re.escape(label) for label in labels)
        match = re.search(rf"(?im)^\s*(?:{label_pattern})\s*:\s*(.*?)\s*$", answer)
        if match and match.group(1).strip():
            parsed[key] = match.group(1).strip()
    return parsed


def parse_date(date_str: Any):
    """Parse date string supporting DD/MM/YYYY, DD-MM-YYYY, YYYY-MM-DD, etc."""
    if not date_str:
        return None
    cleaned = str(date_str).strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%Y/%m/%d", "%d.%m.%Y"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            pass
    return None


def save_questionnaire_answer(session_id, answer):
    """
    Save the patient's answer exactly as provided.

    Python controls the question flow.
    The patient's answer is stored without allowing
    the LLM to modify its meaning.
    """

    session = get_session(session_id)

    question_number = session["current_question"]

    if question_number is None:
        return {
            "status": "completed",
            "message": "The AHCP questionnaire is already complete."
        }

    question = QUESTIONNAIRE[question_number]

    # Clean only leading/trailing whitespace.
    # The actual answer meaning is preserved.
    answer = str(answer).strip()

    if not answer:
        return {
            "status": "error",
            "message": "Please provide an answer."
        }

    lang = session.get("language", "en")

    # Validate Question 1: Full name text
    if question_number == 1:
        if parse_date(answer) or answer.lower() in ("yes", "no", "unsure", "male", "female", "other", "ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ", "ಪುರುಷ", "ಮಹಿಳೆ", "ಇತರೆ") or len(answer) < 2:
            return {
                "status": "invalid",
                "message": "Please enter your full name, not a date." if lang != "kn" else "ದಿನಾಂಕವಲ್ಲ, ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರನ್ನು ನಮೂದಿಸಿ."
            }

    # Validate Question 2: Date of birth
    elif question_number == 2:
        dob = parse_date(answer)
        today = datetime.now().date()
        if not dob or dob > today or (today - dob).days > 130 * 366:
            return {
                "status": "invalid",
                "message": "Please enter a valid date of birth in DD/MM/YYYY format." if lang != "kn" else "ದಯವಿಟ್ಟು DD/MM/YYYY ಸ್ವರೂಪದಲ್ಲಿ ಮಾನ್ಯ ಜನ್ಮ ದಿನಾಂಕವನ್ನು ನಮೂದಿಸಿ."
            }
        answer = dob.isoformat()

    # Validate Question 7..10: Medical background cannot be skipped
    if 7 <= question_number <= 10 and answer.strip().lower() in ("skip", "ಬಿಟ್ಟುಬಿಡಿ", "ಬಿಟ್ಟುಬಿಡಿ."):
        return {
            "status": "invalid",
            "message": "Please describe, or answer None / No." if lang != "kn" else "ದಯವಿಟ್ಟು ವಿವರಿಸಿ ಅಥವಾ 'ಯಾವುದೂ ಇಲ್ಲ' / 'ಇಲ್ಲ' ಎಂದು ಉತ್ತರಿಸಿ."
        }

    # Validate Question 29, 35: Email format (no Skip, valid email required)
    if question_number in (29, 35):
        clean_email = answer.strip()
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if clean_email.lower() in ("skip", "none", "n/a", "ಬಿಟ್ಟುಬಿಡಿ") or not re.match(email_pattern, clean_email):
            return {
                "status": "invalid",
                "message": "Please provide a valid email address." if lang != "kn" else "ದಯವಿಟ್ಟು ಸರಿಯಾದ ಇಮೇಲ್ ವಿಳಾಸವನ್ನು ನಮೂದಿಸಿ."
            }

    # Validate Question 30, 36: Residential address (no Skip)
    if question_number in (30, 36):
        clean_addr = answer.strip()
        if clean_addr.lower() in ("skip", "none", "n/a", "ಬಿಟ್ಟುಬಿಡಿ"):
            return {
                "status": "invalid",
                "message": "Please enter a residential address or select 'Same as my address'." if lang != "kn" else "ದಯವಿಟ್ಟು ವಾಸಸ್ಥಳದ ವಿಳಾಸವನ್ನು ನಮೂದಿಸಿ ಅಥವಾ 'ನನ್ನ ವಿಳಾಸದಂತೆಯೇ' ಆಯ್ಕೆಮಾಡಿ."
            }

    # Validate predefined choice questions
    if question["type"] == "choice":

        valid_options = question["options"]

        matched_option = None

        for option in valid_options:
            if answer.strip().lower() == option.strip().lower():
                matched_option = option
                break

        if matched_option is None:
            norm = normalize_answer(answer)
            if norm:
                for option in valid_options:
                    if norm.strip().lower() == option.strip().lower():
                        matched_option = option
                        break

        if matched_option is None:
            return {
                "status": "invalid",
                "message": "Please select one of the available options." if lang != "kn" else "ದಯವಿಟ್ಟು ಲಭ್ಯವಿರುವ ಆಯ್ಕೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಆರಿಸಿ.",
                "options": valid_options
            }

        # Store the canonical option
        answer = matched_option

    # Combined prompts are parsed by explicit labels into independent canonical fields.
    record = session["patient_record"]
    aliases_by_question = {
        4: {"healthcare_decision_maker": ("Full name", "ಪೂರ್ಣ ಹೆಸರು"), "decision_maker_relationship": ("Relationship", "ಸಂಬಂಧ")},
        6: {"chronic_conditions": ("Chronic conditions", "ದೀರ್ಘಕಾಲದ ಕಾಯಿಲೆಗಳು"), "serious_hospitalization": ("Serious illness or hospitalization", "ಗಂಭೀರ ಕಾಯಿಲೆ ಅಥವಾ ಆಸ್ಪತ್ರೆಗೆ ದಾಖಲು")},
        8: {"long_term_medications": ("Long-term medications", "ದೀರ್ಘಕಾಲದ ಔಷಧಿಗಳು"), "allergies": ("Known allergies", "ತಿಳಿದಿರುವ ಅಲರ್ಜಿಗಳು")},
        15: {"organ_donation": ("Organ donation", "ಅಂಗದಾನ"), "body_donation": ("Body donation for medical education/research", "ವೈದ್ಯಕೀಯ ಶಿಕ್ಷಣ/ಸಂಶೋಧನೆಗಾಗಿ ದೇಹದಾನ")},
    }
    parsed_fields = _labeled_answer_fields(answer, aliases_by_question.get(question_number, {}))
    if question_number == 15 and parsed_fields:
        valid_donation_values = {"yes", "no", "unsure", "ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ"}
        if any(value.strip().lower() not in valid_donation_values for value in parsed_fields.values()):
            return {"status": "invalid", "message": "For each donation choice, enter Yes, No, or Unsure." if session.get("language") != "kn" else "ಪ್ರತಿ ದಾನ ಆಯ್ಕೆಗೆ ಹೌದು, ಇಲ್ಲ, ಅಥವಾ ಖಚಿತವಿಲ್ಲ ಎಂದು ನಮೂದಿಸಿ.", "options": []}
        canonical_donations = {"yes": "Yes", "no": "No", "unsure": "Unsure", "ಹೌದು": "Yes", "ಇಲ್ಲ": "No", "ಖಚಿತವಿಲ್ಲ": "Unsure"}
        parsed_fields = {key: canonical_donations[value.strip().lower()] for key, value in parsed_fields.items()}
    if question_number == 4 and parsed_fields:
        if not all(_answer_is_present(parsed_fields.get(key)) for key in ("healthcare_decision_maker", "decision_maker_relationship")):
            return {"status": "invalid", "message": "Please include both Full name and Relationship on separate lines." if session.get("language") != "kn" else "ಪೂರ್ಣ ಹೆಸರು ಮತ್ತು ಸಂಬಂಧವನ್ನು ಪ್ರತ್ಯೇಕ ಸಾಲುಗಳಲ್ಲಿ ನೀಡಿ.", "options": []}
        record.update(parsed_fields)
    elif parsed_fields:
        record.update(parsed_fields)
    elif question_number in (4, 6, 8):
        # Keep the original single-field behavior for legacy clients and saved sessions.
        record[question["key"]] = answer
    elif question_number == 15 and not parsed_fields:
        # Preserve the legacy one-choice organ donation answer format.
        record["organ_donation"] = {"ಹೌದು": "Yes", "ಇಲ್ಲ": "No", "ಖಚಿತವಿಲ್ಲ": "Unsure"}.get(answer, answer)
    elif question_number == 20 and answer.strip().lower() in ("skip", "ಬಿಟ್ಟುಬಿಡಿ", "ಬಿಟ್ಟುಬಿಡಿ."):
        record[question["key"]] = "Not provided"
    elif question_number in (11, 12, 13, 14, 15, 16, 17, 18) and answer == "Unsure":
        # Do not overwrite previously saved Yes or No preference
        existing_pref = record.get(question["key"])
        if existing_pref not in ("Yes", "No"):
            record[question["key"]] = "Unsure"
    elif question_number in (30, 36) and answer.strip().lower() in ("same as my address", "same as current address", "ನನ್ನ ವಿಳಾಸದಂತೆಯೇ"):
        record[question["key"]] = record.get("permanent_address") or record.get("current_address") or answer
    else:
        record[question["key"]] = answer

    # Move to next question
    if question_number == 31 and answer.strip().lower() in ("no", "ಇಲ್ಲ", "do not want", "ಬೇಡ"):
        session["current_question"] = 37
        next_question = get_current_question(session_id)
        return {
            "status": "saved",
            "question_number": question_number,
            "answer": answer,
            "next_question": next_question
        }
    elif question_number == 36:
        session["current_question"] = 37
        next_question = get_current_question(session_id)
        return {
            "status": "saved",
            "question_number": question_number,
            "answer": answer,
            "next_question": next_question
        }
    elif question_number < len(QUESTIONNAIRE):

        session["current_question"] = question_number + 1
        next_question = get_current_question(session_id)

        return {
            "status": "completed" if next_question is None else "saved",
            "question_number": question_number,
            "answer": answer,
            "next_question": next_question
        }

    else:

        session["current_question"] = None

        return {
            "status": "completed",
            "question_number": question_number,
            "answer": answer,
            "next_question": None
        }

def build_structured_patient_record(session_id):
    """
    Convert the questionnaire answers into a structured
    patient record for backend and doctor-dashboard use.

    IMPORTANT:
    Patient answers come directly from Python session data.
    The LLM is not used to generate or modify these facts.
    """

    session = get_session(session_id)
    record = session["patient_record"]

    structured_record = {
        "patient_information": {
            "full_name": record.get("full_name"),
            "date_of_birth": record.get("date_of_birth"),
            "gender": record.get("gender"),
            "healthcare_decision_maker": record.get(
                "healthcare_decision_maker"
            ),
            "decision_maker_relationship": record.get(
                "decision_maker_relationship"
            )
        },

        "medical_background": {
            "chronic_conditions": record.get(
                "chronic_conditions"
            ),
            "serious_hospitalization": record.get(
                "serious_hospitalization"
            ),
            "long_term_medications": record.get(
                "long_term_medications"
            ),
            "allergies": record.get(
                "allergies"
            )
        },

        "treatment_preferences": {
            "cpr": record.get("cpr"),
            "ventilator": record.get("ventilator"),
            "dialysis": record.get("dialysis"),
            "artificial_nutrition": record.get(
                "artificial_nutrition"
            ),
            "artificial_hydration": record.get(
                "artificial_hydration"
            ),
            "organ_donation": record.get(
                "organ_donation"
            ),
            "goals_of_care": record.get(
                "goals_of_care"
            ),
            "preferred_place_of_care": record.get(
                "preferred_place_of_care"
            ),
            "level_of_medical_intervention": record.get(
                "level_of_medical_intervention"
            )
        },

        "personal_values": {
            "most_important_goal": record.get(
                "most_important_goal"
            ),
            "additional_wishes": record.get(
                "additional_wishes"
            )
        }
    }

    return structured_record

def generate_doctor_dashboard_data(session_id):
    """
    Generate structured, visualization-ready information
    for the doctor dashboard.

    IMPORTANT:
    This function only uses the stored patient record.
    It does NOT ask the LLM to interpret or rewrite patient facts.
    """

    record = build_structured_patient_record(session_id)

    treatment = record["treatment_preferences"]

    # Count treatment preferences
    preference_values = [
        treatment["cpr"],
        treatment["ventilator"],
        treatment["dialysis"],
        treatment["artificial_nutrition"],
        treatment["artificial_hydration"],
        treatment["organ_donation"],
        treatment["goals_of_care"],
        treatment["preferred_place_of_care"],
        treatment["level_of_medical_intervention"]
    ]

    yes_count = preference_values.count("Yes")
    no_count = preference_values.count("No")
    unsure_count = preference_values.count("Unsure")

    # Find unanswered treatment preferences
    unanswered = [
        key
        for key, value in treatment.items()
        if value is None
    ]

    # Find explicitly unresolved preferences
    unresolved = [
        key
        for key, value in treatment.items()
        if value == "Unsure"
    ]

    return {
        "patient_information": record["patient_information"],

        "medical_background": record["medical_background"],

        "treatment_preferences": treatment,

        "personal_values": record["personal_values"],

        "visualization": {
            "preference_summary": {
                "yes": yes_count,
                "no": no_count,
                "unsure": unsure_count
            },

            "unanswered_preferences": unanswered,

            "unresolved_preferences": unresolved
        }
    }

def get_question_text(session_id, question_number):
    session = get_session(session_id)

    if session is None:
        return None

    # Handle a dictionary returned by the questionnaire function
    if isinstance(question_number, dict):
        question_number = question_number.get(
            "question_number",
            question_number.get("number")
        )

    if not isinstance(question_number, int):
        return None

    language = session.get("language", "en")

    if language not in LANGUAGE_TEXT:
        language = "en"

    return LANGUAGE_TEXT[language].get(question_number)

def normalize_answer(user_message):
    """
    Convert English/Kannada patient responses into
    canonical internal values.
    """
    if user_message is None:
        return None

    text = user_message.strip()

    # Direct lookup
    if text in ANSWER_NORMALIZATION:
        return ANSWER_NORMALIZATION[text]

    # Case-insensitive English lookup
    lower_text = text.lower()

    if lower_text in ANSWER_NORMALIZATION:
        return ANSWER_NORMALIZATION[lower_text]

    return None

def get_display_options(session_id, question_number):
    """
    Return the options displayed to the patient
    in their selected language.
    """
    question = get_question_text(
        session_id,
        question_number
    )

    if question is None:
        return []

    return question.get("options") or []


TREATMENT_EXPLANATIONS = {
    11: {
        "en": {
            "title": "Cardiopulmonary Resuscitation (CPR)",
            "summary": "CPR is an emergency medical procedure performed when a person's heartbeat or breathing stops unexpectedly. It involves vigorous chest compressions to manually pump blood and oxygen to the brain and other vital organs, often combined with artificial ventilation or an electric defibrillator to shock the heart back into rhythm.",
            "options_explanation": [
                ("Yes", "You want doctors and emergency teams to perform CPR and resuscitation attempts if your heart or breathing stops."),
                ("No", "You choose a 'Do Not Resuscitate' (DNR) approach. If your heart stops naturally, the medical team will allow a peaceful, natural death without invasive chest compressions or electric shocks, focusing fully on comfort and pain relief."),
                ("Unsure", "You need more time or wish to consult your family or doctor before making a choice.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When you are ready, please select an option (such as Yes or No) to register your preference."
        },
        "kn": {
            "title": "ಕಾರ್ಡಿಯೋಪಲ್ಮನರಿ ರಿಸಸಿಟೇಶನ್ (CPR)",
            "summary": "CPR ಎನ್ನುವುದು ವ್ಯಕ್ತಿಯ ಹೃದಯ ಅಥವಾ ಉಸಿರಾಟವು ಅನಿರೀಕ್ಷಿತವಾಗಿ ನಿಂತುಹೋದಾಗ ಮೆದುಳು ಮತ್ತು ಪ್ರಮುಖ ಅಂಗಗಳಿಗೆ ರಕ್ತ ಮತ್ತು ಆಮ್ಲಜನಕವನ್ನು ಪೂರೈಸಲು ಎದೆ ಒತ್ತಡ (chest compressions) ಹಾಗೂ ಕೃತಕ ಉಸಿರಾಟವನ್ನು ನೀಡುವ ತುರ್ತು ಚಿಕಿತ್ಸಾ ವಿಧಾನವಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಹೃದಯ ಬಡಿತ ನಿಂತಾಗ ವೈದ್ಯರು CPR ಮತ್ತು ಪುನರುಜ್ಜೀವನ ಚಿಕಿತ್ಸೆಯನ್ನು ನೀಡಲು ನೀವು ಸಮ್ಮತಿಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ಸ್ವಾಭಾವಿಕ ಅಂತ್ಯಕ್ಕೆ ಅವಕಾಶ ನೀಡಿ, ಬಲವಂತದ ಎದೆ ಒತ್ತಡ ಅಥವಾ ಶಾಕ್ ನೀಡದೆ, ಸಂಪೂರ್ಣ ನೋವು ನಿವಾರಣೆ ಮತ್ತು ಆರಾಮದಾಯಕ ಆರೈಕೆಗೆ ಮಾತ್ರ ಆದ್ಯತೆ ನೀಡಲಾಗುತ್ತದೆ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ನಿರ್ಧಾರ ಕೈಗೊಳ್ಳುವ ಮುನ್ನ ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಅಥವಾ ವೈದ್ಯರೊಂದಿಗೆ ಸಮಾಲೋಚನೆ ನಡೆಸಲು ಬಯಸುತ್ತೀರಿ.")
            ],
            "guidance": "ಗಮನಿಸಿ: 'ಖಚಿತವಿಲ್ಲ' ಆಯ್ಕೆ ಮಾಡಿದ್ದರಿಂದ ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ನೀವು ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ('ಹೌದು' ಅಥವಾ 'ಇಲ್ಲ') ಆರಿಸಿ."
        }
    },
    12: {
        "en": {
            "title": "Mechanical Ventilation",
            "summary": "Mechanical ventilation is a medical treatment that uses a breathing machine (ventilator) to help a person breathe when they cannot breathe adequately on their own. A tube may be placed through the mouth or nose into the windpipe, or through a tracheostomy.",
            "options_explanation": [
                ("Yes", "You would want mechanical ventilation if you are unable to breathe adequately on your own."),
                ("No", "You would not want mechanical ventilation and would prefer other forms of care focused on your wishes."),
                ("Unsure", "You would like more information before deciding about mechanical ventilation.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When you are ready, please select an option (such as Yes or No) to record your choice."
        },
        "kn": {
            "title": "ಕೃತಕ ಉಸಿರಾಟದ ಸಾಧನ (ವೆಂಟಿಲೇಟರ್ / Mechanical Ventilator)",
            "summary": "ವೆಂಟಿಲೇಟರ್ ಎನ್ನುವುದು ಶ್ವಾಸಕೋಶಗಳು ಸ್ವತಃ ಆಮ್ಲಜನಕವನ್ನು ಪಡೆಯಲು ಸಾಧ್ಯವಾಗದಿದ್ದಾಗ ಉಸಿರಾಟದ ನಳಿಕೆ (intubation) ಅಥವಾ ಟ್ರಾಕಿಯೊಸ್ಟೊಮಿ ಮೂಲಕ ಶ್ವಾಸಕೋಶಕ್ಕೆ ಗಾಳಿ ಮತ್ತು ಆಮ್ಲಜನಕವನ್ನು ತಲುಪಿಸುವ ಜೀವ ರಕ್ಷಕ ಯಂತ್ರವಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಸ್ವತಂತ್ರವಾಗಿ ಉಸಿರಾಡಲು ಸಾಧ್ಯವಾಗದ ಪರಿಸ್ಥಿತಿಯಲ್ಲಿ ವೆಂಟಿಲೇಟರ್ ಯಂತ್ರದ ನೆರವು ಪಡೆಯಲು ನೀವು ಬಯಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ಕೃತಕ ಉಸಿರಾಟದ ಯಂತ್ರದ ನೆರವು ಬೇಡ; ಬದಲಿಗೆ ನಿಮ್ಮ ಆಶಯಗಳಿಗೆ ಅನುಗುಣವಾಗಿ ಇತರ ಆರಾಮದಾಯಕ ಆರೈಕೆಗೆ ಆದ್ಯತೆ ನೀಡಲಾಗುತ್ತದೆ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ವೆಂಟಿಲೇಟರ್ ಬಗ್ಗೆ ಅಂತಿಮ ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳುವ ಮುನ್ನ ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಬಯಸುತ್ತೀರಿ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ನಿಮ್ಮ ಅಂತಿಮ ನಿರ್ಧಾರವನ್ನು ದಾಖಲಿಸಿ."
        }
    },
    13: {
        "en": {
            "title": "Kidney Dialysis",
            "summary": "Kidney dialysis is an artificial medical process that cleans your blood by removing waste toxins, salts, and excess water when your kidneys fail and can no longer filter blood naturally.",
            "options_explanation": [
                ("Yes", "You consent to undergo hemodialysis or peritoneal dialysis if your kidneys cease working."),
                ("No", "You prefer conservative medical kidney management without ongoing artificial blood filtering, prioritizing symptom comfort."),
                ("Unsure", "You want to learn more about dialysis and maintain an undecided status for now.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ಮೂತ್ರಪಿಂಡ ಡಯಾಲಿಸಿಸ್ (Kidney Dialysis)",
            "summary": "ಡಯಾಲಿಸಿಸ್ ಎನ್ನುವುದು ಮೂತ್ರಪಿಂಡಗಳು ಕೆಲಸ ಮಾಡದಿದ್ದಾಗ ರಕ್ತದಲ್ಲಿರುವ ತ್ಯಾಜ್ಯ ಮತ್ತು ಹೆಚ್ಚುವರಿ ನೀರನ್ನು ಯಂತ್ರದ ಮೂಲಕ ಶೋಧಿಸಿ ಶುದ್ಧೀಕರಿಸುವ ವೈದ್ಯಕೀಯ ಪ್ರಕ್ರಿಯೆಯಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಮೂತ್ರಪಿಂಡಗಳು ವಿಫಲವಾದರೆ ಡಯಾಲಿಸಿಸ್ ಚಿಕಿತ್ಸೆ ಪಡೆಯಲು ಸಮ್ಮತಿಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ಕೃತಕ ಶೋಧನೆ ಬೇಡ, ಔಷಧಿಗಳ ಮೂಲಕ ನೋವು ಮತ್ತು ರೋಗಲಕ್ಷಣಗಳ ಶಮನಕ್ಕೆ ಮಾತ್ರ ಆದ್ಯತೆ ನೀಡಲಾಗುತ್ತದೆ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಈ ಬಗ್ಗೆ ಇನ್ನೂ ಖಚಿತ ನಿರ್ಧಾರ ಕೈಗೊಂಡಿಲ್ಲ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಇನ್ನೂ ದಾಖಲಿಸಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    14: {
        "en": {
            "title": "Chemotherapy (Cancer Treatment)",
            "summary": "Chemotherapy uses specialized anti-cancer medications administered intravenously or in pill form to destroy, shrink, or slow the growth of cancer cells throughout the body.",
            "options_explanation": [
                ("Yes", "You would want chemotherapy if recommended by your medical team to treat cancer or prolong life."),
                ("No", "You do not want chemotherapy and would prefer supportive, comfort-focused cancer care managing symptoms without chemo drugs."),
                ("Unsure", "You need more information or wish to discuss the potential benefits and side effects before deciding.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ಕೀಮೋಥೆರಪಿ (ಕ್ಯಾನ್ಸರ್ ಚಿಕಿತ್ಸೆ / Chemotherapy)",
            "summary": "ಕೀಮೋಥೆರಪಿ ಎನ್ನುವುದು ದೇಹದಲ್ಲಿರುವ ಕ್ಯಾನ್ಸರ್ ಕೋಶಗಳನ್ನು ನಾಶಪಡಿಸಲು, ಕುಗ್ಗಿಸಲು ಅಥವಾ ಅವುಗಳ ಬೆಳವಣಿಗೆಯನ್ನು ನಿಧಾನಗೊಳಿಸಲು IV ನರಗಳ ಮೂಲಕ ಅಥವಾ ಮಾತ್ರೆಗಳ ರೂಪದಲ್ಲಿ ನೀಡಲಾಗುವ ವಿಶೇಷ ಕ್ಯಾನ್ಸರ್ ವಿರೋಧಿ ಔಷಧಿ ಚಿಕಿತ್ಸೆಯಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಕ್ಯಾನ್ಸರ್ ನಿಯಂತ್ರಣಕ್ಕೆ ವೈದ್ಯಕೀಯ ತಂಡ ಶಿಫಾರಸು ಮಾಡಿದರೆ ಕೀಮೋಥೆರಪಿ ಚಿಕಿತ್ಸೆ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ಕೀಮೋಥೆರಪಿ ಔಷಧಿಗಳು ಬೇಡ; ಬದಲಿಗೆ ನೋವು ನಿವಾರಣೆ ಮತ್ತು ಆರಾಮದಾಯಕ ಶುಶ್ರೂಷೆಗೆ ಮಾತ್ರ ಆದ್ಯತೆ ನೀಡುತ್ತೀರಿ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ನಿರ್ಧರಿಸುವ ಮುನ್ನ ಇದರ ಅಡ್ಡಪರಿಣಾಮಗಳು ಮತ್ತು ಪ್ರಯೋಜನಗಳ ಬಗ್ಗೆ ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಬಯಸುತ್ತೀರಿ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    15: {
        "en": {
            "title": "Radiotherapy (Radiation Treatment)",
            "summary": "Radiotherapy uses targeted high-energy radiation beams (such as X-rays) directed precisely at tumors to destroy cancer cells, shrink growths, or relieve localized pain and bleeding.",
            "options_explanation": [
                ("Yes", "You would want radiation therapy if recommended to control cancer or alleviate tumor symptoms."),
                ("No", "You do not want radiation treatment and prefer comfort-focused alternatives."),
                ("Unsure", "You want more information about radiation therapy before deciding.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ರೇಡಿಯೋಥೆರಪಿ (ವಿಕಿರಣ ಚಿಕಿತ್ಸೆ / Radiotherapy)",
            "summary": "ರೇಡಿಯೋಥೆರಪಿಯು ಕ್ಯಾನ್ಸರ್ ಕೋಶಗಳನ್ನು ನಾಶಮಾಡಲು, ಗೆಡ್ಡೆಗಳನ್ನು ಕುಗ್ಗಿಸಲು ಅಥವಾ ನೋವನ್ನು ನಿವಾರಿಸಲು ಉದ್ದೇಶಿತ ಅಧಿಕ-ಶಕ್ತಿಯ ವಿಕಿರಣ ಕಿರಣಗಳನ್ನು (Radiation beams) ಬಳಸುವ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆಯಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಕ್ಯಾನ್ಸರ್ ನಿಯಂತ್ರಣಕ್ಕೆ ಅಥವಾ ರೋಗಲಕ್ಷಣಗಳ ನಿವಾರಣೆಗೆ ವಿಕಿರಣ ಚಿಕಿತ್ಸೆ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ವಿಕಿರಣ ಚಿಕಿತ್ಸೆ ಬೇಡ; ಕೇವಲ ನೋವು ಶಮನ ಮತ್ತು ಆರಾಮದಾಯಕ ಆರೈಕೆ ಸಾಕು."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ನಿರ್ಧಾರ ತೆಗೆದುಕೊಳ್ಳುವ ಮುನ್ನ ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಬಯಸುತ್ತೀರಿ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    16: {
        "en": {
            "title": "Major Surgery (Invasive Operations)",
            "summary": "Major surgery involves invasive operative procedures performed under general anesthesia in an operating room to repair damaged organs, remove diseased tissue, or address life-threatening conditions.",
            "options_explanation": [
                ("Yes", "You consent to undergo major surgery if doctors determine it is needed to treat a life-threatening illness or improve your health."),
                ("No", "You choose to forgo invasive surgical operations, preferring non-surgical medical management and comfort care."),
                ("Unsure", "You wish to evaluate the risks, recovery expectations, and benefits before deciding about major surgery.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆ (Major Surgery)",
            "summary": "ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಯು ಸಾಮಾನ್ಯ ಅರಿವಳಿಕೆ (general anesthesia) ನೀಡಿ, ರೋಗಗ್ರಸ್ತ ಅಂಗಾಂಶಗಳನ್ನು ತೆಗೆದುಹಾಕಲು ಅಥವಾ ಜೀವಕ್ಕೆ ಅಪಾಯವಿರುವ ಪರಿಸ್ಥಿತಿಗಳನ್ನು ಸರಿಪಡಿಸಲು ಮಾಡುವ ಆಪರೇಷನ್ ವಿಧಾನವಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಜೀವ ಉಳಿಸಲು ಅಥವಾ ಆರೋಗ್ಯ ಸುಧಾರಿಸಲು ಅಗತ್ಯವಿದ್ದರೆ ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಗೆ ಸಮ್ಮತಿಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ದೊಡ್ಡ ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಗಳು ಬೇಡ; ಕೇವಲ ಶಸ್ತ್ರಚಿಕಿತ್ಸೇತರ ಔಷಧಿ ಮತ್ತು ಆರಾಮದಾಯಕ ಆರೈಕೆ ಸಾಕು."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಶಸ್ತ್ರಚಿಕಿತ್ಸೆಯ ಅಪಾಯಗಳು ಮತ್ತು ಚೇತರಿಕೆಯ ಸಾಧ್ಯತೆಗಳ ಬಗ್ಗೆ ಹೆಚ್ಚಿನ ಮಾಹಿತಿ ಬಯಸುತ್ತೀರಿ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    17: {
        "en": {
            "title": "Artificial Hydration (Intravenous Fluids)",
            "summary": "Artificial hydration involves giving water and electrolytes through an intravenous (IV) drip into a vein or through a tube when a person cannot drink fluids naturally.",
            "options_explanation": [
                ("Yes", "You want IV fluids to prevent dehydration if you cannot drink normally."),
                ("No", "You prefer natural mouth moistening (such as ice chips and lip balms) to keep your mouth comfortable without invasive IV fluid lines."),
                ("Unsure", "You wish to explore the benefits and burdens of artificial hydration before deciding.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ಕೃತಕ ದ್ರವಗಳು / ಐವಿ ಫ್ಲೂಯಿಡ್ಸ್ (Artificial Hydration)",
            "summary": "ನೈಸರ್ಗಿಕವಾಗಿ ನೀರು ಕುಡಿಯಲು ಸಾಧ್ಯವಾಗದಿದ್ದಾಗ ರಕ್ತನಾಳದ (IV) ಮೂಲಕ ಅಥವಾ ಟ್ಯೂಬ್ ಮೂಲಕ ಕೃತಕವಾಗಿ ದ್ರವ ಮತ್ತು ಎಲೆಕ್ಟ್ರೋಲೈಟ್‌ಗಳನ್ನು ಪೂರೈಸುವ ಚಿಕಿತ್ಸೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ದ್ರವ ಸೇವಿಸಲು ಅಸಾಧ್ಯವಾದಾಗ IV ಡ್ರಿಪ್ಸ್ ಮೂಲಕ ದ್ರವಾಹಾರ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ನೈಸರ್ಗಿಕವಾಗಿ ಬಾಯಿ ತೇವವಾಗಿಡುವ ಶುಶ್ರೂಷೆ ಸಾಕು, ಕೃತಕ IV ನಳಿಕೆಗಳು ಬೇಡ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಈ ಬಗ್ಗೆ ಇನ್ನೂ ನಿರ್ಧಾರ ಮಾಡಿಲ್ಲ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    18: {
        "en": {
            "title": "Artificial Nutrition (Tube Feeding)",
            "summary": "Artificial nutrition supplies liquid formulas containing calories, proteins, and essential nutrients through a tube (such as a nasogastric tube through the nose or a gastrostomy PEG tube directly into the stomach) when eating by mouth is impossible.",
            "options_explanation": [
                ("Yes", "You want tube feeding if you permanently or temporarily lose the ability to eat or swallow food."),
                ("No", "You prefer to be fed by mouth for comfort as tolerated, without surgical feeding tubes."),
                ("Unsure", "You want more information before deciding on artificial nutrition.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ಕೃತಕ ಪೋಷಕಾಂಶ / ಟ್ಯೂಬ್ ಫೀಡಿಂಗ್ (Artificial Nutrition)",
            "summary": "ಬಾಯಿಯ ಮೂಲಕ ಆಹಾರ ಸೇವಿಸಲು ಸಾಧ್ಯವಾಗದಿದ್ದಾಗ ಮೂಗಿನ ಮೂಲಕ ಅಥವಾ ಹೊಟ್ಟೆಯ ಮೂಲಕ ಟ್ಯೂಬ್ ಅಳವಡಿಸಿ ದ್ರವರೂಪದ ಪೋಷಕಾಂಶಗಳನ್ನು ಪೂರೈಸುವ ವಿಧಾನವಾಗಿದೆ.",
            "options_explanation": [
                ("ಹೌದು (Yes)", "ಆಹಾರ ಸೇವಿಸಲು ಅಸಾಧ್ಯವಾದಾಗ ಟ್ಯೂಬ್ ಮೂಲಕ ಪೋಷಕಾಂಶ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಇಲ್ಲ (No)", "ಕೃತಕ ಟ್ಯೂಬ್ ಬೇಡ, ಬಾಯಿಯ ಮೂಲಕ ಸಾಧ್ಯವಾದಷ್ಟು ಆರಾಮದಾಯಕ ಆಹಾರ ನೀಡಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಹೆಚ್ಚಿನ ಸಮಾಲೋಚನೆ ಅಗತ್ಯವಿದೆ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    19: {
        "en": {
            "title": "Goals of Care",
            "summary": "Goals of care help doctors understand your overall treatment philosophy during severe illness: whether to maximize comfort, pursue every life-prolonging intervention, or maintain a thoughtful balance between the two.",
            "options_explanation": [
                ("Comfort-focused care", "Prioritizes relieving pain and distress so you remain as comfortable as possible, avoiding invasive procedures."),
                ("Life-prolonging treatment", "Prioritizes extending life using all available medical and surgical interventions."),
                ("A balance of comfort and life-prolonging treatment", "Pursues treatments that offer reasonable recovery while avoiding burdensome interventions with little benefit."),
                ("Unsure", "You are currently considering what aligns best with your values.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ಆರೈಕೆಯ ಮುಖ್ಯ ಗುರಿಗಳು (Goals of Care)",
            "summary": "ಗಂಭೀರ ಅನಾರೋಗ್ಯದ ಸಮಯದಲ್ಲಿ ಚಿಕಿತ್ಸೆಯ ಮುಖ್ಯ ಆದ್ಯತೆ ಏನಾಗಿರಬೇಕು ಎಂಬುದನ್ನು ಇದು ನಿರ್ಧರಿಸುತ್ತದೆ: ಆರಾಮ ಮತ್ತು ನೋವು ನಿವಾರಣೆಯೋ, ಜೀವಿತಾವಧಿ ವಿಸ್ತರಣೆಯೋ, ಅಥವಾ ಎರಡರ ಸಮತೋಲನವೋ.",
            "options_explanation": [
                ("ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಆರೈಕೆ (Comfort-focused care)", "ನೋವು ಮತ್ತು ಅಸ್ವಸ್ಥತೆಯನ್ನು ನಿವಾರಿಸಿ ನೆಮ್ಮದಿಯಿಂದಿರಲು ಪ್ರಮುಖ ಆದ್ಯತೆ ನೀಡುತ್ತದೆ."),
                ("ಜೀವಿತಾವಧಿ ವಿಸ್ತರಿಸುವ ಚಿಕಿತ್ಸೆ (Life-prolonging treatment)", "ಎಲ್ಲಾ ಲಭ್ಯವಿರುವ ಚಿಕಿತ್ಸಾ ಸಾಧನಗಳನ್ನು ಬಳಸಿ ಆಯಸ್ಸನ್ನು ವಿಸ್ತರಿಸಲು ಆದ್ಯತೆ ನೀಡುತ್ತದೆ."),
                ("ಆರಾಮ ಮತ್ತು ಜೀವಿತಾವಧಿ ವಿಸ್ತರಣೆಯ ಸಮತೋಲನ", "ಉಭಯ ಉದ್ದೇಶಗಳ ಸಮತೋಲಿತ ಮಾರ್ಗವನ್ನು ಅನುಸರಿಸುತ್ತದೆ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಈ ಬಗ್ಗೆ ಇನ್ನೂ ಆಲೋಚಿಸುತ್ತಿದ್ದೀರಿ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    20: {
        "en": {
            "title": "Preferred Place of Care",
            "summary": "Expresses where you would feel safest and most at peace during the final stages of illness or recovery.",
            "options_explanation": [
                ("Home", "You prefer to be cared for in the comfort and familiarity of your home."),
                ("Hospital", "You prefer the 24/7 medical surveillance and acute care facilities of a hospital."),
                ("Hospice or palliative care facility", "You prefer a specialized hospice focusing on palliative comfort and family support."),
                ("No preference", "You leave the decision to your healthcare proxy and medical team."),
                ("Unsure", "You want to think about what setting best suits your care needs.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ಆರೈಕೆ ಪಡೆಯಲು ಆದ್ಯತೆಯ ಸ್ಥಳ (Preferred Place of Care)",
            "summary": "ಗಂಭೀರ ಅನಾರೋಗ್ಯದ ಹಂತದಲ್ಲಿ ನೀವು ಎಲ್ಲಿ ಚಿಕಿತ್ಸೆ ಮತ್ತು ಆರೈಕೆ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ ಎಂಬುದನ್ನು ತಿಳಿಸುತ್ತದೆ.",
            "options_explanation": [
                ("ಮನೆ (Home)", "ನಿಮ್ಮ ಪರಿಚಿತ ಮನೆಯ ಪರಿಸರದಲ್ಲಿ ಆರೈಕೆ ಪಡೆಯಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಆಸ್ಪತ್ರೆ (Hospital)", "ವೈದ್ಯಕೀಯ ಸೌಲಭ್ಯಗಳಿರುವ ಆಸ್ಪತ್ರೆಯಲ್ಲಿರಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಉಪಶಾಮಕ ಆರೈಕೆ ಕೇಂದ್ರ (Hospice)", "ವಿಶೇಷ ಉಪಶಾಮಕ ಆರೈಕೆ ಕೇಂದ್ರದಲ್ಲಿರಲು ಬಯಸುತ್ತೀರಿ."),
                ("ಯಾವುದೇ ಆದ್ಯತೆಯಿಲ್ಲ (No preference)", "ಪರಿಸ್ಥಿತಿಗೆ ತಕ್ಕಂತೆ ವೈದ್ಯರು ಮತ್ತು ಕುಟುಂಬದ ನಿರ್ಧಾರಕ್ಕೆ ಬಿಡುತ್ತೀರಿ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಇನ್ನೂ ಅಂತಿಮ ತೀರ್ಮಾನ ಕೈಗೊಂಡಿಲ್ಲ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    },
    24: {
        "en": {
            "title": "Level of Medical Intervention",
            "summary": "Guides medical teams on how aggressively to intervene when serious medical events occur.",
            "options_explanation": [
                ("Full medical treatment", "Use all available treatments including ICU admission, CPR, and mechanical ventilation."),
                ("Limited medical treatment", "Use medical treatments such as antibiotics and IV fluids, but avoid invasive life support like intubation or CPR."),
                ("Comfort-focused treatment", "Provide care that maximizes dignity, symptom relief, and peace without invasive curative interventions."),
                ("Unsure", "You need more information before establishing your desired intervention level.")
            ],
            "guidance": "Selecting 'Unsure' provides this explanation without saving a preference. When ready, select an option to proceed."
        },
        "kn": {
            "title": "ವೈದ್ಯಕೀಯ ಹಸ್ತಕ್ಷೇಪದ ಮಟ್ಟ (Level of Medical Intervention)",
            "summary": "ಗಂಭೀರ ಆರೋಗ್ಯ ಸಮಸ್ಯೆ ಎದುರಾದಾಗ ಚಿಕಿತ್ಸೆಯ ತೀವ್ರತೆಯ ಮಟ್ಟ ಎಷ್ಟು ಇರಬೇಕು ಎಂಬುದರ ಮಾರ್ಗದರ್ಶನ.",
            "options_explanation": [
                ("ಪೂರ್ಣ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ (Full medical treatment)", "ICU, ವೆಂಟಿಲೇಟರ್, CPR ಸೇರಿದಂತೆ ಎಲ್ಲಾ ತೀವ್ರ ನಿಗಾ ಚಿಕಿತ್ಸೆಗಳನ್ನು ಬಳಸಲಾಗುತ್ತದೆ."),
                ("ಸೀಮಿತ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ (Limited medical treatment)", "ಔಷಧಿಗಳು ಮತ್ತು IV ದ್ರವಗಳನ್ನು ಬಳಸಲಾಗುತ್ತದೆ, ಆದರೆ ಆಕ್ರಮಣಕಾರಿ ಜೀವ ರಕ್ಷಕ ಯಂತ್ರಗಳನ್ನು ಬಳಸುವುದಿಲ್ಲ."),
                ("ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಚಿಕಿತ್ಸೆ (Comfort-focused treatment)", "ನೋವು ನಿವಾರಣೆ ಮತ್ತು ಘನತೆಯುಕ್ತ ಆರಾಮದಾಯಕ ಶುಶ್ರೂಷೆಗೆ ಮಾತ್ರ ಆದ್ಯತೆ ನೀಡಲಾಗುತ್ತದೆ."),
                ("ಖಚಿತವಿಲ್ಲ (Unsure)", "ಇನ್ನೂ ಅಂತಿಮ ನಿರ್ಧಾರ ಮಾಡಿಲ್ಲ.")
            ],
            "guidance": "ಗಮನಿಸಿ: ನಿಮ್ಮ ಆಯ್ಕೆಯನ್ನು ಇನ್ನೂ ಉಳಿಸಲಾಗಿಲ್ಲ. ಸಿದ್ಧರಾದ ನಂತರ ದಯವಿಟ್ಟು ಆಯ್ಕೆಮಾಡಿ."
        }
    }
}

# Aliases for legacy question numbers, follow-up IDs, and string keys
TREATMENT_EXPLANATIONS[10] = TREATMENT_EXPLANATIONS[11]   # legacy CPR
TREATMENT_EXPLANATIONS[33] = TREATMENT_EXPLANATIONS[14]   # follow-up chemo
TREATMENT_EXPLANATIONS[34] = TREATMENT_EXPLANATIONS[15]   # follow-up radio
TREATMENT_EXPLANATIONS[35] = TREATMENT_EXPLANATIONS[16]   # follow-up surgery

TREATMENT_EXPLANATIONS["cpr"] = TREATMENT_EXPLANATIONS[11]
TREATMENT_EXPLANATIONS["ventilator"] = TREATMENT_EXPLANATIONS[12]
TREATMENT_EXPLANATIONS["mechanical ventilation"] = TREATMENT_EXPLANATIONS[12]
TREATMENT_EXPLANATIONS["dialysis"] = TREATMENT_EXPLANATIONS[13]
TREATMENT_EXPLANATIONS["kidney dialysis"] = TREATMENT_EXPLANATIONS[13]
TREATMENT_EXPLANATIONS["chemotherapy"] = TREATMENT_EXPLANATIONS[14]
TREATMENT_EXPLANATIONS["radiotherapy"] = TREATMENT_EXPLANATIONS[15]
TREATMENT_EXPLANATIONS["surgery"] = TREATMENT_EXPLANATIONS[16]
TREATMENT_EXPLANATIONS["major surgery"] = TREATMENT_EXPLANATIONS[16]
TREATMENT_EXPLANATIONS["artificial_hydration"] = TREATMENT_EXPLANATIONS[17]
TREATMENT_EXPLANATIONS["hydration"] = TREATMENT_EXPLANATIONS[17]
TREATMENT_EXPLANATIONS["artificial_nutrition"] = TREATMENT_EXPLANATIONS[18]
TREATMENT_EXPLANATIONS["nutrition"] = TREATMENT_EXPLANATIONS[18]
TREATMENT_EXPLANATIONS["goals_of_care"] = TREATMENT_EXPLANATIONS[19]
TREATMENT_EXPLANATIONS["goals of care"] = TREATMENT_EXPLANATIONS[19]
TREATMENT_EXPLANATIONS["preferred_place_of_care"] = TREATMENT_EXPLANATIONS[20]
TREATMENT_EXPLANATIONS["preferred place of care"] = TREATMENT_EXPLANATIONS[20]
TREATMENT_EXPLANATIONS["level_of_medical_intervention"] = TREATMENT_EXPLANATIONS[24]
TREATMENT_EXPLANATIONS["level of medical intervention"] = TREATMENT_EXPLANATIONS[24]


def generate_knowledge_fallback_explanation(
    topic: str,
    question_number: int | str | None,
    retrieved: list[dict] | None = None,
    language: str = "en",
    display_options: list[str] | None = None
) -> str:
    """Generate a safe, patient-friendly, objective explanation synthesized from knowledge documents."""
    lang = "kn" if language == "kn" else "en"
    exp_data = None
    if question_number is not None:
        exp_data = TREATMENT_EXPLANATIONS.get(question_number, {}).get(lang)
    if not exp_data and topic:
        exp_data = TREATMENT_EXPLANATIONS.get(str(topic).lower().strip(), {}).get(lang)
    if not exp_data and question_number is not None:
        exp_data = TREATMENT_EXPLANATIONS.get(question_number, {}).get("en", {})
    if not exp_data and topic:
        exp_data = TREATMENT_EXPLANATIONS.get(str(topic).lower().strip(), {}).get("en", {})
    if not exp_data:
        exp_data = {}

    title = exp_data.get("title", topic or "Medical Treatment")
    summary = exp_data.get("summary", "")
    opts = exp_data.get("options_explanation", [])
    guidance = exp_data.get("guidance", "")

    lines = []
    if lang == "kn":
        lines.append("ಶೈಕ್ಷಣಿಕ ಮಾಹಿತಿ (ಖಚಿತವಿಲ್ಲ)\n")
        lines.append(f"ವೈದ್ಯಕೀಯ ಮಾಹಿತಿ: {title}")
        lines.append(summary)
        lines.append("\nಲಭ್ಯವಿರುವ ಆಯ್ಕೆಗಳ ವಿವರಣೆ:")
        for opt_label, opt_desc in opts:
            lines.append(f"• {opt_label}: {opt_desc}")
        lines.append(f"\n{guidance}")
    else:
        lines.append("Educational Information (Unsure)\n")
        lines.append(f"Medical Information: {title}")
        lines.append(summary)
        lines.append("\nExplanation of Choices:")
        for opt_label, opt_desc in opts:
            lines.append(f"• {opt_label}: {opt_desc}")
        lines.append(f"\n{guidance}")

    return "\n".join(lines)


def load_knowledge_base(force: bool = False) -> int:
    """Create or load the MiniLM + FAISS index from cache or OCR-readable PDFs in knowledge/."""
    global chunks, chunk_texts, embedding_model, faiss_index, knowledge_load_error
    if faiss_index is not None and not force:
        return int(faiss_index.ntotal)

    pdf_files = sorted(KNOWLEDGE_DIR.rglob("*.pdf"))
    if not pdf_files:
        knowledge_load_error = f"No PDF knowledge sources found in {KNOWLEDGE_DIR}"
        chunks, chunk_texts, embedding_model, faiss_index = [], [], None, None
        return 0

    index_cache_file = CACHE_DIR / "faiss.index"
    chunks_cache_file = CACHE_DIR / "chunks.json"
    manifest_cache_file = CACHE_DIR / "manifest.json"

    # Signature mapping for modification detection
    current_signatures = {p.name: p.stat().st_mtime for p in pdf_files}

    # 1. Fast path: load from disk cache if present and unchanged
    if not force and index_cache_file.exists() and chunks_cache_file.exists() and manifest_cache_file.exists():
        try:
            with open(manifest_cache_file, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            if (
                manifest.get("model") == EMBEDDING_MODEL_NAME
                and manifest.get("pdf_count") == len(pdf_files)
                and manifest.get("signatures") == current_signatures
            ):
                import faiss
                from sentence_transformers import SentenceTransformer
                loaded_index = faiss.read_index(str(index_cache_file))
                with open(chunks_cache_file, "r", encoding="utf-8") as f:
                    loaded_chunks = json.load(f)
                loaded_texts = [c["text"] for c in loaded_chunks]
                if embedding_model is None:
                    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                faiss_index = loaded_index
                chunks = loaded_chunks
                chunk_texts = loaded_texts
                knowledge_load_error = None
                logger.info("Loaded FAISS index from disk cache: %d chunks", len(chunks))
                return len(chunks)
        except Exception as cache_exc:
            logger.warning("Failed to load knowledge cache (%s); rebuilding...", cache_exc)

    # 2. Slow path: build index from PDFs and cache to disk
    try:
        from pypdf import PdfReader
        import faiss
        from sentence_transformers import SentenceTransformer
        documents = []
        for pdf_path in pdf_files:
            try:
                reader = PdfReader(str(pdf_path))
                text = "\n".join((page.extract_text() or "") for page in reader.pages).strip()
                if text:
                    documents.append({"source": pdf_path.name, "category": pdf_path.parent.name, "text": text})
                else:
                    logger.warning("No text extracted from %s; OCR may be needed", pdf_path.name)
            except Exception as exc:
                logger.warning("Skipping PDF %s (%s)", pdf_path.name, type(exc).__name__)
        new_chunks = []
        step = CHUNK_SIZE - CHUNK_OVERLAP
        for doc in documents:
            for start in range(0, len(doc["text"]), step):
                text = doc["text"][start:start + CHUNK_SIZE].strip()
                if text:
                    new_chunks.append({"text": text, "source": doc["source"], "category": doc["category"]})
        if not new_chunks:
            knowledge_load_error = "No extractable PDF text. OCR scanned PDFs before indexing."
            chunks, chunk_texts, embedding_model, faiss_index = [], [], None, None
            return 0
        model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        texts = [c["text"] for c in new_chunks]
        vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True, show_progress_bar=False).astype("float32")
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(vectors)
        chunks, chunk_texts, embedding_model, faiss_index = new_chunks, texts, model, index
        knowledge_load_error = None

        # Write to disk cache
        try:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            faiss.write_index(index, str(index_cache_file))
            with open(chunks_cache_file, "w", encoding="utf-8") as f:
                json.dump(new_chunks, f, ensure_ascii=False)
            with open(manifest_cache_file, "w", encoding="utf-8") as f:
                json.dump({
                    "model": EMBEDDING_MODEL_NAME,
                    "pdf_count": len(pdf_files),
                    "signatures": current_signatures,
                    "chunk_count": len(new_chunks)
                }, f, ensure_ascii=False)
            logger.info("Saved FAISS index and chunks cache to %s (%d chunks)", CACHE_DIR, len(new_chunks))
        except Exception as save_exc:
            logger.warning("Could not persist knowledge cache: %s", save_exc)

        logger.info("Built FAISS index: %s chunks from %s PDFs", len(chunks), len(documents))
        return len(chunks)
    except Exception as exc:
        knowledge_load_error = f"Knowledge initialization failed ({type(exc).__name__})"
        logger.exception("Knowledge initialization failed")
        chunks, chunk_texts, embedding_model, faiss_index = [], [], None, None
        return 0


def retrieve_relevant_chunks(query, top_k=5):
    if faiss_index is None or embedding_model is None:
        load_knowledge_base()
    if faiss_index is None or embedding_model is None or not chunk_texts:
        return []
    query_vector = embedding_model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype("float32")
    search_k = min(max(top_k * 5, 20), len(chunk_texts))
    scores, indices = faiss_index.search(query_vector, search_k)
    best_by_source = {}
    for score, idx in zip(scores[0], indices[0]):
        if idx < 0:
            continue
        c = chunks[int(idx)]
        item = {"text": c["text"], "source": c["source"], "category": c.get("category", "unknown"), "score": float(score)}
        if item["source"] not in best_by_source or item["score"] > best_by_source[item["source"]]["score"]:
            best_by_source[item["source"]] = item
    return sorted(best_by_source.values(), key=lambda x: x["score"], reverse=True)[:top_k]


def _clean_knowledge_chunk_text(text: str) -> str:
    """Sanitize raw knowledge chunk text by stripping URLs, document metadata, page numbers, and formatting cleanly."""
    if not text:
        return ""
    import re
    # Remove URLs
    text = re.sub(r"https?://\S+|www\.\S+", "", text)
    # Remove file system paths
    text = re.sub(r"[A-Za-z]:\\[^\s\n]+", "", text)
    text = re.sub(r"/(?:Users|home|tmp|var)/[^\s\n]+", "", text)
    # Remove page headers/footers like "Page 1 of 12" or "--- Page 3 ---"
    text = re.sub(r"(?i)---*\s*page\s*\d+\s*---*", "", text)
    text = re.sub(r"(?i)page\s+\d+(\s+of\s+\d+)?", "", text)
    # Remove raw square bracket source citations like [Source: ...] or [xyz.pdf]
    text = re.sub(r"\[[^\]]*\.(?:pdf|docx|txt|html?)[^\]]*\]", "", text)
    # Normalize whitespaces
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return " ".join(lines)


def generate_rag_answer(
    user_query: str,
    top_k: int = 5,
    language_instruction: str = "Answer in English.",
    question_number: int | None = None,
    language: str = "en",
    display_options: list[str] | None = None,
    topic: str | None = None,
):
    retrieved = retrieve_relevant_chunks(user_query, top_k=top_k)
    sources = [{"source": Path(r["source"]).name if r.get("source") else "Clinical Guidance", "category": r["category"], "score": r["score"]} for r in retrieved]
    if not retrieved:
        answer = (
            "ಈ ವಿಷಯಕ್ಕೆ ಸಂಬಂಧಿಸಿದ ಪರಿಶೀಲಿತ ಜ್ಞಾನ ಮೂಲಗಳು ಲಭ್ಯವಿಲ್ಲ. ದಯವಿಟ್ಟು ನಂತರ ಮತ್ತೆ ಪ್ರಯತ್ನಿಸಿ."
            if language == "kn" or language_instruction == "Answer in Kannada."
            else "I don't have enough verified AHCP source material available to explain this topic right now. Please try again later."
        )
        return {"answer": answer, "sources": [], "error": "knowledge_unavailable"}

    api_key = get_openrouter_api_key()
    model = get_openrouter_model()

    def _synthesize_clean_fallback(retrieved_items, lang):
        clean_chunks = []
        for r in retrieved_items[:2]:
            cleaned = _clean_knowledge_chunk_text(r.get("text", "")[:350])
            if cleaned:
                clean_chunks.append(cleaned)
        chunks_summary = "\n\n".join(clean_chunks)
        if not chunks_summary:
            chunks_summary = (
                "ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯು ನಿಮ್ಮ ಭವಿಷ್ಯದ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸಾ ಆಯ್ಕೆಗಳನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ದಾಖಲಿಸಲು ಸಹಾಯ ಮಾಡುತ್ತದೆ."
                if lang == "kn"
                else "Advance care planning helps record your future medical treatment choices and personal values clearly."
            )
        if lang == "kn":
            return f"ಪರಿಶೀಲಿಸಿದ ಮುಂಗಡ ಆರೈಕೆ ಯೋಜನೆಯ ಮಾಹಿತಿ:\n\n{chunks_summary}"
        else:
            return f"Verified advance care planning information:\n\n{chunks_summary}"

    # If OpenRouter is not configured or uses placeholder credentials, use trusted knowledge synthesis directly
    if not is_valid_openrouter_key(api_key) or OpenAI is None:
        if question_number is not None and question_number in TREATMENT_EXPLANATIONS:
            fallback = generate_knowledge_fallback_explanation(
                topic=topic or TREATMENT_QUESTIONS.get(question_number, ""),
                question_number=question_number,
                retrieved=retrieved,
                language=language,
                display_options=display_options,
            )
            return {"answer": fallback, "sources": sources}
        else:
            fallback = _synthesize_clean_fallback(retrieved, language)
            return {"answer": fallback, "sources": sources}

    # OpenRouter key is valid: attempt remote generation with bounded 5.0s client timeout
    context = "\n\n".join(f"[Source {i}: {Path(r['source']).name}]\n{r['text']}" for i, r in enumerate(retrieved, 1))
    system_prompt = (
        f"You are an AI assistant for an Advance Health Care Planning (AHCP) system for users in India.\n"
        f"LANGUAGE: {language_instruction}\n"
        f"Rules: answer only from supplied context; do not introduce unrelated foreign laws; "
        f"never invent medical/legal claims or patient facts; say when context is insufficient; "
        f"do not diagnose, prescribe, or choose treatment for the patient; keep explanations concise and patient-friendly. "
        f"For Kannada, use natural Kannada and preserve terms such as CPR, dialysis, and ventilator."
    )
    try:
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1", timeout=5.0)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Knowledge context:\n\n{context}\n\nUser question:\n{user_query}\n\nAnswer only from supplied context."}
            ],
            temperature=0.2,
        )
        answer = response.choices[0].message.content or "I could not generate an explanation."
        answer = _clean_knowledge_chunk_text(answer) if ("http" in answer or ":\\" in answer) else answer
        return {"answer": answer, "sources": sources}
    except Exception as exc:
        logger.warning("Live LLM generation timed out or failed (%s); falling back to trusted knowledge explanation", type(exc).__name__)
        if question_number is not None and question_number in TREATMENT_EXPLANATIONS:
            fallback = generate_knowledge_fallback_explanation(
                topic=topic or TREATMENT_QUESTIONS.get(question_number, ""),
                question_number=question_number,
                retrieved=retrieved,
                language=language,
                display_options=display_options,
            )
            return {"answer": fallback, "sources": sources}
        else:
            fallback = _synthesize_clean_fallback(retrieved, language)
            return {"answer": fallback, "sources": sources}


def handle_unsure_response(session_id):
    session = get_session(session_id)

    if not session:
        return {
            "message": "Session not found.",
            "sources": []
        }

    question_number = session.get("current_question")

    if question_number not in TREATMENT_QUESTIONS:
        return {
            "message": "Unsure handling is not available for this question.",
            "sources": []
        }

    language = session.get("language", "en")

    if language == "kn":
        language_instruction = "Answer in Kannada."
    else:
        language_instruction = "Answer in English."

    question = QUESTIONNAIRE[question_number]
    topic = TREATMENT_QUESTIONS[question_number]
    options = question.get("options", [])

    # Use the language-specific display question/options
    display_question = get_question_text(
        session_id,
        question_number
    )

    if display_question:
        display_question_text = display_question["question"]
        display_options = display_question.get("options") or []
    else:
        display_question_text = question["question"]
        display_options = options

    if question_number in TREATMENT_EXPLANATIONS:
        explanation = generate_knowledge_fallback_explanation(
            topic=topic,
            question_number=question_number,
            language=language,
            display_options=display_options
        )
        return {
            "message": explanation,
            "sources": [
                "National Health Service (NHS) Advance Care Planning Guidelines",
                "Indian Council of Medical Research (ICMR) End-of-Life Care Guidelines"
            ]
        }

    query = f"""
Explain the following advance care planning questionnaire topic.

Topic:
{topic}

Question:
{display_question_text}

Available patient options:
{", ".join(display_options)}

The patient selected "Unsure" and needs educational information
before making their own decision.

Explain what this topic means and briefly explain the available options.

IMPORTANT:
- {language_instruction}
- Use the exact terminology of the available options.
- Do not recommend any option.
- Do not tell the patient what they should choose.
- Do not assume anything about the patient's medical condition.
- Do not invent patient-specific information.
- Keep the explanation patient-friendly.
- The patient must make the final decision.
"""

    result = generate_rag_answer(
        query,
        top_k=5,
        language_instruction=language_instruction,
        question_number=question_number,
        language=language,
        display_options=display_options,
        topic=topic,
    )

    return {
        "message": result.get(
            "answer",
            "I could not generate an explanation."
        ),
        "sources": result.get("sources", [])
    }


def chat(session_id: str, user_message: str, question_number: int | None = None):
    session = get_session(session_id)

    if session is None:
        return {
            "status": "error",
            "message": "Session not found."
        }

    user_message = user_message.strip()

    if not user_message:
        return {
            "status": "invalid",
            "message": "Please enter a response.",
            "question_number": None,
            "answer": None,
            "next_question": None,
            "sources": None
        }

    add_message(session_id, "user", user_message)

    language = session.get("language", "en")

    # --------------------------------------------------
    # Get current question number safely
    # --------------------------------------------------

    if question_number is not None:
        session["current_question"] = question_number
    else:
        question_number = session.get("current_question")

    # If somehow stored as a dictionary, extract number
    if isinstance(question_number, dict):
        question_number = question_number.get("question_number")
        session["current_question"] = question_number

    # --------------------------------------------------
    # Questionnaire mode
    # --------------------------------------------------

    if question_number is not None:

        question = QUESTIONNAIRE[question_number]

        # Explicit free-response validation for Q1 and Q2
        if question_number == 1:
            clean_text = str(user_message).strip()
            if parse_date(clean_text) or clean_text.lower() in ("yes", "no", "unsure", "male", "female", "other", "ಹೌದು", "ಇಲ್ಲ", "ಖಚಿತವಿಲ್ಲ", "ಪುರುಷ", "ಮಹಿಳೆ", "ಇತರೆ") or len(clean_text) < 2:
                display_q = get_question_text(session_id, 1)
                return {
                    "status": "invalid",
                    "message": "Please enter your full name, not a date." if language != "kn" else "ದಿನಾಂಕವಲ್ಲ, ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರನ್ನು ನಮೂದಿಸಿ.",
                    "question_number": 1,
                    "answer": None,
                    "next_question": {
                        "question_number": 1,
                        "question": display_q["question"] if display_q else "What is your full name?",
                        "options": None
                    },
                    "sources": None
                }
        elif question_number == 2:
            dob = parse_date(user_message)
            today = datetime.now().date()
            if not dob or dob > today or (today - dob).days > 130 * 366:
                display_q = get_question_text(session_id, 2)
                return {
                    "status": "invalid",
                    "message": "Please enter a valid date of birth in DD/MM/YYYY format." if language != "kn" else "ದಯವಿಟ್ಟು DD/MM/YYYY ಸ್ವರೂಪದಲ್ಲಿ ಮಾನ್ಯ ಜನ್ಮ ದಿನಾಂಕವನ್ನು ನಮೂದಿಸಿ.",
                    "question_number": 2,
                    "answer": None,
                    "next_question": {
                        "question_number": 2,
                        "question": display_q["question"] if display_q else "What is your date of birth?",
                        "options": None
                    },
                    "sources": None
                }
            user_message = dob.isoformat()

        # --------------------------------------------------
        # Normalize answer
        # --------------------------------------------------

        normalized_answer = normalize_answer(user_message)

        # --------------------------------------------------
        # UNSURE
        # --------------------------------------------------

        if (
            question_number in TREATMENT_QUESTIONS
            and normalized_answer == "Unsure"
        ):

            explanation = handle_unsure_response(session_id)
            save_questionnaire_answer(session_id, "Unsure")
            next_question = get_current_question(session_id)

            return {
                "status": "explanation",
                "message": explanation.get(
                    "message",
                    explanation.get(
                        "explanation",
                        "I could not generate an explanation."
                    )
                ),
                "question_number": question_number,
                "answer": "Unsure",
                "next_question": next_question,
                "sources": explanation.get("sources", [])
            }

        # --------------------------------------------------
        # Choice question
        # --------------------------------------------------

        if question["type"] == "choice":
            english_options = question.get("options") or []
            display_question = get_question_text(
                session_id,
                question_number
            )
            display_options = (
                display_question.get("options") or []
            )

            valid_answer = None

            # 1. Direct case-insensitive match against canonical English options
            for opt in english_options:
                if user_message.strip().lower() == opt.strip().lower():
                    valid_answer = opt
                    break

            # 2. Match against displayed options (Kannada or English)
            if valid_answer is None:
                for idx, d_opt in enumerate(display_options):
                    if (
                        user_message.strip() == d_opt.strip()
                        or user_message.strip().lower() == d_opt.strip().lower()
                    ):
                        if idx < len(english_options):
                            valid_answer = english_options[idx]
                            break

            # 3. Match normalized_answer against canonical English options
            if valid_answer is None and normalized_answer:
                for opt in english_options:
                    if normalized_answer.strip().lower() == opt.strip().lower():
                        valid_answer = opt
                        break

            # Invalid option
            if valid_answer is None:
                err_msg = (
                    "ದಯವಿಟ್ಟು ಲಭ್ಯವಿರುವ ಆಯ್ಕೆಗಳಲ್ಲಿ ಒಂದನ್ನು ಆರಿಸಿ."
                    if session.get("language") == "kn"
                    else "Please select one of the available options."
                )
                return {
                    "status": "invalid",
                    "message": err_msg,
                    "question_number": question_number,
                    "answer": None,
                    "next_question": {
                        "question_number": question_number,
                        "question": display_question["question"],
                        "options": display_question.get("options")
                    },
                    "sources": None
                }

            # Store canonical answer
            user_message = valid_answer

        # --------------------------------------------------
        # Save answer
        # --------------------------------------------------

        result = save_questionnaire_answer(
            session_id,
            user_message
        )

        # --------------------------------------------------
        # Completed
        # --------------------------------------------------

        if result["status"] == "completed":

            return {
                "status": "completed",
                "message": (
                    "Thank you. The AHCP questionnaire "
                    "has been completed."
                ),
                "question_number": question_number,
                "answer": user_message,
                "next_question": None,
                "sources": None
            }

        # --------------------------------------------------
        # Get next question safely
        # --------------------------------------------------

        next_question_number = result.get("next_question")

        # IMPORTANT:
        # save_questionnaire_answer may return a dictionary.
        # Convert it back to just the question number.

        if isinstance(next_question_number, dict):
            next_question_number = next_question_number.get(
                "question_number"
            )

        # Store ONLY the integer
        session["current_question"] = next_question_number

        # --------------------------------------------------
        # Build localized next question
        # --------------------------------------------------

        next_question = None

        if next_question_number is not None:

            next_question_data = get_question_text(
                session_id,
                next_question_number
            )

            if next_question_data:

                next_question = {
                    "question_number": next_question_number,
                    "question": next_question_data["question"],
                    "options": next_question_data.get("options")
                }

        return {
            "status": "saved",
            "message": result.get(
                "message",
                "Your answer has been saved."
            ),
            "question_number": question_number,
            "answer": user_message,
            "next_question": next_question,
            "sources": None
        }

    # --------------------------------------------------
    # General RAG mode
    # --------------------------------------------------

    language_instruction = {
        "en": "Answer in English.",
        "kn": "Answer in Kannada."
    }.get(
        language,
        "Answer in English."
    )

    result = generate_rag_answer(
        user_message,
        top_k=5,
        language_instruction=language_instruction,
        language=language,
    )

    return {
        "status": "answer",
        "message": result["answer"],
        "question_number": None,
        "answer": result["answer"],
        "next_question": None,
        "sources": result.get("sources")
    }


# API models and routes
class SessionRequest(BaseModel):
    language: str = "en"
    known_answers: dict[str, Any] = Field(default_factory=dict)

class SessionResponse(BaseModel):
    session_id: str
    language: str
    question_number: int | None
    question: str | None
    options: list[str] | None = None

class ChatRequest(BaseModel):
    session_id: str
    message: str
    question_number: int | None = None

def get_ai_service_key() -> str:
    key = os.getenv("AHCP_AI_SERVICE_API_KEY")
    if not key:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file, override=True)
                key = os.getenv("AHCP_AI_SERVICE_API_KEY")
            except Exception:
                pass
    return key or AI_SERVICE_API_KEY

def get_openrouter_api_key() -> str:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file, override=True)
                key = os.getenv("OPENROUTER_API_KEY")
            except Exception:
                pass
    return key or OPENROUTER_API_KEY

def get_openrouter_model() -> str:
    return os.getenv("OPENROUTER_MODEL") or OPENROUTER_MODEL

@asynccontextmanager
async def lifespan(app: FastAPI):
    if not get_ai_service_key():
        logger.warning("AHCP_AI_SERVICE_API_KEY is unset; protected endpoints will return 503")
    if not is_valid_openrouter_key(get_openrouter_api_key()):
        logger.warning("OPENROUTER_API_KEY is unset or placeholder; trusted knowledge fallback generator will be used")
    pdf_list = list(KNOWLEDGE_DIR.rglob("*.pdf"))
    if not pdf_list:
        logger.warning("No knowledge PDFs found in %s; add the project's processed PDF corpus", KNOWLEDGE_DIR)
    else:
        try:
            total_loaded = load_knowledge_base()
            logger.info("Knowledge base warmed up successfully with %d chunks", total_loaded)
        except Exception as exc:
            logger.warning("Failed to warm up knowledge base during startup: %s", exc)
    yield

app = FastAPI(title="AHCP AI Service", version="1.0.0", lifespan=lifespan)


def verify_ai_service_key(x_api_key: str | None = Header(default=None)):
    expected_key = get_ai_service_key()
    if not expected_key:
        raise HTTPException(status_code=503, detail="AI service API key is not configured.")
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing AI service API key.")
    if not secrets.compare_digest(x_api_key, expected_key):
        raise HTTPException(status_code=401, detail="Invalid AI service API key.")
    return True

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "AHCP AI Service", "version": "1.0.0"}

@app.post("/session", response_model=SessionResponse, dependencies=[Depends(verify_ai_service_key)])
def api_create_session(request: SessionRequest):
    language = (request.language or "en").strip().lower()
    if language not in ("en", "kn"):
        language = "en"
    # Each new conversation is a clean questionnaire. Existing patient data is
    # displayed in ACP review/forms and must never skip or renumber questions.
    session_id = create_session({})
    session = get_session(session_id)
    session["language"] = language
    session["current_question"] = 1
    first = get_current_question(session_id)
    if not first:
        return {"session_id": session_id, "language": language, "question_number": None, "question": None, "options": None}
    question_number = first["question_number"]
    return {"session_id": session_id, "language": language, "question_number": question_number, "question": first["question"], "options": get_display_options(session_id, question_number)}

@app.post("/chat", dependencies=[Depends(verify_ai_service_key)])
def api_chat(request: ChatRequest):
    if get_session(request.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return chat(request.session_id, request.message, request.question_number)

@app.post("/patient-record", dependencies=[Depends(verify_ai_service_key)])
def api_patient_record(session_id: str):
    if get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return build_structured_patient_record(session_id)

@app.post("/doctor-dashboard", dependencies=[Depends(verify_ai_service_key)])
def api_doctor_dashboard(session_id: str):
    if get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return generate_doctor_dashboard_data(session_id)


