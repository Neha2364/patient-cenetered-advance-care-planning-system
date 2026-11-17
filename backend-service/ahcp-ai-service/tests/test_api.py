import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("AHCP_AI_SERVICE_API_KEY", "test-secret")

from fastapi.testclient import TestClient
import app as service

client = TestClient(service.app)
HEADERS = {"X-API-Key": os.environ["AHCP_AI_SERVICE_API_KEY"]}

def test_health_is_public():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_protected_session_rejects_missing_and_invalid_key():
    assert client.post("/session", json={"language": "en"}).status_code == 401
    assert client.post("/session", json={"language": "en"}, headers={"X-API-Key": "wrong"}).status_code == 401

def test_bilingual_session_and_q1_q2():
    for lang, expected_q1, name, expected_q2 in [
        ("en", "What is your full legal name?", "Test Patient", "What is your date of birth?"),
        ("kn", "ನಿಮ್ಮ ಪೂರ್ಣ ಕಾನೂನುಬದ್ಧ ಹೆಸರು ಏನು?", "ಪರೀಕ್ಷಾ ರೋಗಿ", "ನಿಮ್ಮ ಜನ್ಮ ದಿನಾಂಕ ಏನು?"),
    ]:
        start = client.post("/session", json={"language": lang}, headers=HEADERS)
        assert start.status_code == 200, start.text
        data = start.json()
        assert data["question_number"] == 1 and data["question"] == expected_q1
        sid = data["session_id"]
        response = client.post("/chat", json={"session_id": sid, "message": name}, headers=HEADERS)
        assert response.status_code == 200, response.text
        result = response.json()
        assert result["status"] == "saved"
        assert result["next_question"]["question"] == expected_q2
        assert service.get_session(sid)["patient_record"]["full_name"] == name

def test_new_session_ignores_prefilled_answers_and_starts_at_full_name():
    known = {
        "full_name": "Saved Patient", "date_of_birth": "2000-01-01", "gender": "Other",
        "healthcare_decision_maker": "Alex", "decision_maker_relationship": "Sibling",
        "chronic_conditions": "None", "serious_hospitalization": "None",
        "long_term_medications": "None", "allergies": "None",
        "cpr": "Yes", "ventilator": "No", "dialysis": "Unsure",
        "artificial_nutrition": "Yes", "artificial_hydration": "No",
    }
    for language, expected_question in (("en", "What is your full legal name?"), ("kn", "ನಿಮ್ಮ ಪೂರ್ಣ ಕಾನೂನುಬದ್ಧ ಹೆಸರು ಏನು?")):
        start = client.post("/session", json={"language": language, "known_answers": known}, headers=HEADERS)
        assert start.status_code == 200
        payload = start.json()
        assert payload["question_number"] == 1
        assert payload["question"] == expected_question
        sid = payload["session_id"]
        record = service.get_session(sid)["patient_record"]
        assert record == {}

def test_patient_record_and_dashboard():
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]
    record = client.post("/patient-record", params={"session_id": sid}, headers=HEADERS)
    dashboard = client.post("/doctor-dashboard", params={"session_id": sid}, headers=HEADERS)
    assert record.status_code == 200 and dashboard.status_code == 200
    assert "treatment_preferences" in record.json()
    assert dashboard.json()["visualization"]["preference_summary"] == {"yes": 0, "no": 0, "unsure": 0}


def test_complete_questionnaire_in_both_languages():
    answer_sets = {
        "en": {
            1: "AHCP Test Patient", 2: "2000-01-01", 3: "Female", 4: "9876543210", 5: "English",
            6: "123 Main St, Bengaluru", 7: "None", 8: "None", 9: "None", 10: "None",
            11: "Yes", 12: "No", 13: "Yes", 14: "No", 15: "Yes", 16: "No", 17: "Yes", 18: "No",
            19: "Comfort-focused care", 20: "Home", 21: "No preference", 22: "No preference",
            23: "Quality of life", 24: "Limited medical treatment", 25: "No additional wishes",
            26: "John Doe", 27: "Sibling", 28: "9876543211", 29: "john@example.com", 30: "Same as my address",
            31: "No", 32: "None", 33: "None", 34: "9876543212", 35: "None", 36: "Same as my address",
            37: "Yes", 38: "No", 39: "No specific wishes", 40: "Same as current address",
            41: "Aadhaar", 42: "123456789012", 43: "Ward 10", 44: "Confirm & Complete ACP"
        },
        "kn": {
            1: "AHCP ಪರೀಕ್ಷಾ ರೋಗಿ", 2: "01/01/2000", 3: "ಮಹಿಳೆ", 4: "9876543210", 5: "ಕನ್ನಡ",
            6: "123 ಮುಖ್ಯ ರಸ್ತೆ, ಬೆಂಗಳೂರು", 7: "ಯಾವುದೂ ಇಲ್ಲ", 8: "ಯಾವುದೂ ಇಲ್ಲ", 9: "ಯಾವುದೂ ಇಲ್ಲ", 10: "ಯಾವುದೂ ಇಲ್ಲ",
            11: "ಹೌದು", 12: "ಇಲ್ಲ", 13: "ಹೌದು", 14: "ಇಲ್ಲ", 15: "ಹೌದು", 16: "ಇಲ್ಲ", 17: "ಹೌದು", 18: "ಇಲ್ಲ",
            19: "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಆರೈಕೆ", 20: "ಮನೆ", 21: "ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ", 22: "ಯಾವುದೇ ಆದ್ಯತೆ ಇಲ್ಲ",
            23: "ಆರಾಮವಾಗಿರುವುದು", 24: "ಸೀಮಿತ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ", 25: "ಯಾವುದೇ ಹೆಚ್ಚುವರಿ ಇಚ್ಛೆಗಳಿಲ್ಲ",
            26: "ರಮೇಶ್", 27: "ಸಹೋದರ", 28: "9876543211", 29: "ramesh@example.com", 30: "ನನ್ನ ವಿಳಾಸದಂತೆಯೇ",
            31: "ಇಲ್ಲ", 32: "ಯಾವುದೂ ಇಲ್ಲ", 33: "ಯಾವುದೂ ಇಲ್ಲ", 34: "9876543212", 35: "ಯಾವುದೂ ಇಲ್ಲ", 36: "ನನ್ನ ವಿಳಾಸದಂತೆಯೇ",
            37: "ಹೌದು", 38: "ಇಲ್ಲ", 39: "ಯಾವುದೇ ನಿರ್ದಿಷ್ಟ ಇಚ್ಛೆಗಳಿಲ್ಲ", 40: "ಪ್ರಸ್ತುತ ವಿಳಾಸದಂತೆಯೇ",
            41: "ಆಧಾರ್", 42: "123456789012", 43: "ವಾರ್ಡ್ 10", 44: "ACP ದೃಢೀಕರಿಸಿ ಮತ್ತು ಪೂರ್ಣಗೊಳಿಸಿ"
        },
    }
    for language, answers in answer_sets.items():
        start = client.post("/session", json={"language": language}, headers=HEADERS)
        assert start.status_code == 200
        sid = start.json()["session_id"]
        current_q = start.json()
        while current_q and current_q.get("question_number") is not None:
            qnum = current_q["question_number"]
            msg = answers[qnum]
            response = client.post("/chat", json={"session_id": sid, "message": msg}, headers=HEADERS)
            assert response.status_code == 200, (language, qnum, response.text)
            res_data = response.json()
            if res_data["status"] == "completed":
                break
            assert res_data["status"] == "saved", (language, qnum, res_data)
            current_q = res_data["next_question"]
        session = service.get_session(sid)
        assert session["current_question"] is None
        dashboard = client.post("/doctor-dashboard", params={"session_id": sid}, headers=HEADERS)
        assert dashboard.status_code == 200
        assert dashboard.json()["visualization"]["preference_summary"]["yes"] > 0


def test_final_choice_after_unsure_is_saved(monkeypatch):
    start = client.post("/session", json={"language": "kn"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 11
    monkeypatch.setattr(service, "handle_unsure_response", lambda _sid: {"message": "mock explanation", "sources": []})
    explanation = client.post("/chat", json={"session_id": sid, "message": "ಖಚಿತವಿಲ್ಲ"}, headers=HEADERS)
    assert explanation.json()["status"] == "explanation"
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"
    assert explanation.json()["next_question"]["question_number"] == 12
    assert service.get_session(sid)["current_question"] == 12


def test_all_protected_endpoints_require_auth():
    assert client.post("/chat", json={"session_id": "fake", "message": "hi"}).status_code == 401
    assert client.post("/patient-record", params={"session_id": "fake"}).status_code == 401
    assert client.post("/doctor-dashboard", params={"session_id": "fake"}).status_code == 401


def test_endpoints_return_404_on_missing_session():
    assert client.post("/chat", json={"session_id": "nonexistent_sid", "message": "hi"}, headers=HEADERS).status_code == 404
    assert client.post("/patient-record", params={"session_id": "nonexistent_sid"}, headers=HEADERS).status_code == 404
    assert client.post("/doctor-dashboard", params={"session_id": "nonexistent_sid"}, headers=HEADERS).status_code == 404


def test_chat_handles_empty_and_invalid_choice():
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]

    # Empty message
    empty = client.post("/chat", json={"session_id": sid, "message": "   "}, headers=HEADERS)
    assert empty.status_code == 200
    assert empty.json()["status"] == "invalid"

    # Fast forward to choice question Q11 (CPR)
    service.get_session(sid)["current_question"] = 11
    invalid_choice = client.post("/chat", json={"session_id": sid, "message": "maybe definitely"}, headers=HEADERS)
    assert invalid_choice.status_code == 200
    assert invalid_choice.json()["status"] == "invalid"
    assert "options" in invalid_choice.json()["next_question"]


def test_general_rag_mode_after_questionnaire_completed(monkeypatch):
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = None

    monkeypatch.setattr(
        service,
        "generate_rag_answer",
        lambda msg, top_k=5, language_instruction="", language="en": {
            "answer": f"Mock answer for {msg}",
            "sources": [{"source": "mock.pdf", "category": "knowledge", "score": 0.85}],
            "error": None
        }
    )

    rag_response = client.post("/chat", json={"session_id": sid, "message": "What is a living will?"}, headers=HEADERS)
    assert rag_response.status_code == 200
    data = rag_response.json()
    assert data["status"] == "answer"
    assert "Mock answer for" in data["message"]
    assert len(data["sources"]) == 1


def test_real_knowledge_base_retrieval():
    """Verify BM25 retrieval from real PDFs in knowledge directory without LLM calls."""
    chunks_found = service.retrieve_relevant_chunks("cardiopulmonary resuscitation", top_k=3)
    assert len(chunks_found) > 0
    sources = [c["source"] for c in chunks_found]
    assert any("CPR" in s or "resuscitation" in s.lower() or "ventilator" in s.lower() for s in sources)


def test_unsure_explanation_with_real_retrieval_and_openrouter_placeholder():
    """Verify that selecting Unsure returns a safe medical explanation from knowledge base when OpenRouter is placeholder."""
    # 1. English
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    assert start.status_code == 200
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 11

    resp = client.post("/chat", json={"session_id": sid, "message": "Unsure"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "explanation"
    assert data["question_number"] == 11
    assert "Cardiopulmonary Resuscitation" in data["message"]
    assert "Explanation of Choices:" in data["message"]
    assert service.get_session(sid)["current_question"] == 12
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"
    assert len(data.get("sources") or []) > 0
    assert any(
        ("CPR" in s.get("source", "")) or ("ICMR" in s.get("source", "")) or ("NHS" in s.get("source", ""))
        if isinstance(s, dict)
        else ("CPR" in str(s) or "ICMR" in str(s) or "NHS" in str(s))
        for s in data["sources"]
    )

    # 2. Kannada
    start_kn = client.post("/session", json={"language": "kn"}, headers=HEADERS)
    assert start_kn.status_code == 200
    sid_kn = start_kn.json()["session_id"]
    service.get_session(sid_kn)["current_question"] = 11

    resp_kn = client.post("/chat", json={"session_id": sid_kn, "message": "ಖಚಿತವಿಲ್ಲ"}, headers=HEADERS)
    assert resp_kn.status_code == 200
    data_kn = resp_kn.json()
    assert data_kn["status"] == "explanation"
    assert data_kn["question_number"] == 11
    assert "CPR" in data_kn["message"]
    assert "ಲಭ್ಯವಿರುವ ಆಯ್ಕೆಗಳ ವಿವರಣೆ:" in data_kn["message"]
    assert service.get_session(sid_kn)["current_question"] == 12
    assert service.get_session(sid_kn)["patient_record"]["cpr"] == "Unsure"


def test_unsure_openrouter_timeout_falls_back_to_knowledge_explanation(monkeypatch):
    """Verify that when OpenRouter remote call hangs or times out, the service falls back to trusted knowledge explanation."""
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 11

    # Simulate valid key present but OpenRouter call times out
    monkeypatch.setattr(service, "get_openrouter_api_key", lambda: "sk-or-v1-valid-looking-key-1234567890")
    monkeypatch.setattr(service, "is_valid_openrouter_key", lambda key: True)

    class MockOpenAIClient:
        def __init__(self, *args, **kwargs):
            class MockChat:
                class MockCompletions:
                    def create(self, *a, **k):
                        raise TimeoutError("Simulated OpenRouter gateway timeout")
                completions = MockCompletions()
            self.chat = MockChat()

    monkeypatch.setattr(service, "OpenAI", MockOpenAIClient)

    resp = client.post("/chat", json={"session_id": sid, "message": "Unsure"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "explanation"
    assert data["question_number"] == 11
    assert "Cardiopulmonary Resuscitation" in data["message"]
    assert service.get_session(sid)["current_question"] == 12
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"


def test_unsure_handles_retrieval_failure_gracefully(monkeypatch):
    """Verify that retrieval failure still records the explicit unsure choice and advances."""
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 11

    # Simulate empty retrieval
    monkeypatch.setattr(service, "retrieve_relevant_chunks", lambda q, top_k=5: [])

    resp = client.post("/chat", json={"session_id": sid, "message": "Unsure"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "explanation"
    assert "Cardiopulmonary Resuscitation" in data["message"]
    assert service.get_session(sid)["current_question"] == 12
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"
