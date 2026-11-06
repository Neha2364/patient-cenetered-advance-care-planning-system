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
        ("en", "What is your full name?", "Test Patient", "What is your date of birth?"),
        ("kn", "ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರು ಏನು?", "ಪರೀಕ್ಷಾ ರೋಗಿ", "ನಿಮ್ಮ ಜನ್ಮ ದಿನಾಂಕ ಏನು?"),
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
    for language, expected_question in (("en", "What is your full name?"), ("kn", "ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರು ಏನು?")):
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
            1: "AHCP Test Patient", 2: "2004-12-06", 3: "Female", 4: "Self", 5: "Self",
            6: "None", 7: "No", 8: "No", 9: "None", 10: "Yes", 11: "No", 12: "Yes",
            13: "No", 14: "Yes", 15: "No", 16: "Comfort-focused care", 17: "Home",
            18: "Limited medical treatment", 19: "Being comfortable and pain-free", 20: "No additional wishes",
        },
        "kn": {
            1: "AHCP ಪರೀಕ್ಷಾ ರೋಗಿ", 2: "06-12-2004", 3: "ಮಹಿಳೆ", 4: "ನಾನೇ", 5: "ನಾನೇ",
            6: "ಯಾವುದೂ ಇಲ್ಲ", 7: "ಇಲ್ಲ", 8: "ಇಲ್ಲ", 9: "ಯಾವುದೂ ಇಲ್ಲ", 10: "ಹೌದು", 11: "ಇಲ್ಲ",
            12: "ಹೌದು", 13: "ಇಲ್ಲ", 14: "ಹೌದು", 15: "ಇಲ್ಲ", 16: "ಆರಾಮಕ್ಕೆ ಆದ್ಯತೆ ನೀಡುವ ಆರೈಕೆ",
            17: "ಮನೆ", 18: "ಸೀಮಿತ ವೈದ್ಯಕೀಯ ಚಿಕಿತ್ಸೆ", 19: "ಆರಾಮವಾಗಿ ಮತ್ತು ನೋವಿಲ್ಲದೆ ಇರುವುದು", 20: "ಹೆಚ್ಚುವರಿ ಇಚ್ಛೆಗಳಿಲ್ಲ",
        },
    }
    for language, answers in answer_sets.items():
        start = client.post("/session", json={"language": language}, headers=HEADERS)
        assert start.status_code == 200
        sid = start.json()["session_id"]
        for question_number in range(1, 21):
            response = client.post("/chat", json={"session_id": sid, "message": answers[question_number]}, headers=HEADERS)
            assert response.status_code == 200, (language, question_number, response.text)
            expected = "completed" if question_number == 20 else "saved"
            assert response.json()["status"] == expected, (language, question_number, response.json())
        session = service.get_session(sid)
        assert len(session["patient_record"]) == 20
        assert session["current_question"] is None
        dashboard = client.post("/doctor-dashboard", params={"session_id": sid}, headers=HEADERS)
        assert dashboard.status_code == 200
        assert dashboard.json()["visualization"]["preference_summary"] == {"yes": 3, "no": 3, "unsure": 0}


def test_final_choice_after_unsure_is_saved(monkeypatch):
    start = client.post("/session", json={"language": "kn"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 10
    monkeypatch.setattr(service, "handle_unsure_response", lambda _sid: {"message": "mock explanation", "sources": []})
    explanation = client.post("/chat", json={"session_id": sid, "message": "ಖಚಿತವಿಲ್ಲ"}, headers=HEADERS)
    assert explanation.json()["status"] == "explanation"
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"
    assert explanation.json()["next_question"]["question_number"] == 11
    assert service.get_session(sid)["current_question"] == 11


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

    # Fast forward to choice question Q10
    service.get_session(sid)["current_question"] = 10
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
        lambda query, top_k=5, language_instruction="Answer in English.", **kwargs: {
            "answer": f"Mock answer for: {query}",
            "sources": [{"source": "mock.pdf", "category": "knowledge", "score": 0.85}],
        },
    )

    rag_response = client.post("/chat", json={"session_id": sid, "message": "What is a living will?"}, headers=HEADERS)
    assert rag_response.status_code == 200
    data = rag_response.json()
    assert data["status"] == "answer"
    assert "Mock answer for" in data["message"]
    assert len(data["sources"]) == 1


def test_real_knowledge_base_retrieval():
    """Verify FAISS retrieval from real PDFs in knowledge directory without LLM calls."""
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
    service.get_session(sid)["current_question"] = 10

    resp = client.post("/chat", json={"session_id": sid, "message": "Unsure"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "explanation"
    assert data["question_number"] == 10
    assert "Cardiopulmonary Resuscitation" in data["message"]
    assert "Explanation of Choices:" in data["message"]
    assert service.get_session(sid)["current_question"] == 11
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"
    assert len(data.get("sources") or []) > 0
    assert any("CPR" in s["source"] for s in data["sources"])

    # 2. Kannada
    start_kn = client.post("/session", json={"language": "kn"}, headers=HEADERS)
    assert start_kn.status_code == 200
    sid_kn = start_kn.json()["session_id"]
    service.get_session(sid_kn)["current_question"] = 10

    resp_kn = client.post("/chat", json={"session_id": sid_kn, "message": "ಖಚಿತವಿಲ್ಲ"}, headers=HEADERS)
    assert resp_kn.status_code == 200
    data_kn = resp_kn.json()
    assert data_kn["status"] == "explanation"
    assert data_kn["question_number"] == 10
    assert "CPR" in data_kn["message"]
    assert "ಲಭ್ಯವಿರುವ ಆಯ್ಕೆಗಳ ವಿವರಣೆ:" in data_kn["message"]
    assert service.get_session(sid_kn)["current_question"] == 11
    assert service.get_session(sid_kn)["patient_record"]["cpr"] == "Unsure"


def test_unsure_openrouter_timeout_falls_back_to_knowledge_explanation(monkeypatch):
    """Verify that when OpenRouter remote call hangs or times out, the service falls back to trusted knowledge explanation."""
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 10

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
    assert data["question_number"] == 10
    assert "Cardiopulmonary Resuscitation" in data["message"]
    assert service.get_session(sid)["current_question"] == 11
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"


def test_unsure_handles_retrieval_failure_gracefully(monkeypatch):
    """Verify that retrieval failure still records the explicit unsure choice and advances."""
    start = client.post("/session", json={"language": "en"}, headers=HEADERS)
    sid = start.json()["session_id"]
    service.get_session(sid)["current_question"] = 10

    # Simulate empty retrieval
    monkeypatch.setattr(service, "retrieve_relevant_chunks", lambda q, top_k=5: [])

    resp = client.post("/chat", json={"session_id": sid, "message": "Unsure"}, headers=HEADERS)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "explanation"
    assert "verified AHCP source material" in data["message"]
    assert service.get_session(sid)["current_question"] == 11
    assert service.get_session(sid)["patient_record"]["cpr"] == "Unsure"

