import os
import unittest
import json
from unittest.mock import patch, MagicMock
import requests
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.ai_session import AISession
from backend.models.chat_history import ChatHistory
from backend.models.dhr import DHR
from backend.services.ai_service import AIService
from backend.utils.auth_helpers import generate_token

class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key-123'
    JWT_SECRET_KEY = 'test-jwt-secret'

class AIIntegrationTestCase(unittest.TestCase):
    """Comprehensive test suite for AHCP AI Service Flask integration."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Clean up any lingering test users
        for email in ["ai_pat1@test.com", "ai_pat2@test.com", "ai_doc@test.com"]:
            u = User.query.filter_by(email=email).first()
            if u:
                db.session.delete(u)
        db.session.commit()

        # Seed test users
        self.user_p1 = User(full_name="Patient One", email="ai_pat1@test.com", role="patient")
        self.user_p2 = User(full_name="Patient Two", email="ai_pat2@test.com", role="patient")
        self.user_doc = User(full_name="Dr. Smith", email="ai_doc@test.com", role="doctor")
        db.session.add_all([self.user_p1, self.user_p2, self.user_doc])
        db.session.commit()

        # Create Patient profiles
        self.patient1 = Patient(user_id=self.user_p1.id, preferred_language="English")
        self.patient2 = Patient(user_id=self.user_p2.id, preferred_language="English")
        db.session.add_all([self.patient1, self.patient2])
        db.session.commit()

        # Create JWT Tokens
        self.p1_token = generate_token(self.user_p1.id, self.user_p1.email, self.user_p1.role)
        self.p2_token = generate_token(self.user_p2.id, self.user_p2.email, self.user_p2.role)
        self.doc_token = generate_token(self.user_doc.id, self.user_doc.email, self.user_doc.role)

        self.p1_headers = {"Authorization": f"Bearer {self.p1_token}", "Content-Type": "application/json"}
        self.p2_headers = {"Authorization": f"Bearer {self.p2_token}", "Content-Type": "application/json"}
        self.doc_headers = {"Authorization": f"Bearer {self.doc_token}", "Content-Type": "application/json"}

    def tearDown(self):
        for email in ["ai_pat1@test.com", "ai_pat2@test.com", "ai_doc@test.com"]:
            u = User.query.filter_by(email=email).first()
            if u:
                db.session.delete(u)
        db.session.commit()
        db.session.remove()
        self.app_context.pop()

    def test_question_answers_persist_retrieve_and_appear_in_doctor_dashboard(self):
        # Use new canonical Q numbers (Q1-Q44 schema)
        answers = {
            7: "Diabetes",                                             # chronic_conditions
            8: "Prior stroke admission",                               # serious_hospitalization
            9: "Metformin",                                            # long_term_medications
            10: "Penicillin",                                          # allergies
            11: "Unsure",                                              # cpr → UNSURE
            12: "Yes",                                                 # ventilator → WANT
            13: "No",                                                  # dialysis → DO NOT WANT
            14: "Unsure",                                              # chemotherapy → UNSURE
            15: "Yes",                                                 # radiotherapy → WANT
            16: "No",                                                  # surgery → DO NOT WANT
            17: "Unsure",                                              # iv_fluids → UNSURE
            18: "Yes",                                                 # nutrition_hydration → WANT
            19: "A balance of comfort and life-prolonging treatment",  # goals_of_care
            20: "No preference",                                       # preferred_place_of_care
            21: "No preference",                                       # preferred_hospital
            23: "Time with family",                                    # personal_values
            31: "No",                                                  # alternate_dhr_appointed = False
            39: "No specific wishes",                                  # last_rites
        }
        for question_number, answer in answers.items():
            AIService._persist_canonical_answer(self.patient1.patient_id, question_number, answer, self.user_p1.id)
        db.session.commit()

        # get_saved_answer_for_question uses new Q numbers
        self.assertEqual(AIService.get_saved_answer_for_question(self.patient1.patient_id, 7), "Diabetes")
        self.assertEqual(AIService.get_saved_answer_for_question(self.patient1.patient_id, 10), "Penicillin")
        saved = AIService._synthesize_dashboard_from_db(self.patient1.patient_id)
        self.assertEqual(saved["medical_background"]["serious_hospitalization"], "Prior stroke admission")
        self.assertEqual(saved["medical_background"]["long_term_medications"], "Metformin")
        self.assertEqual(saved["medical_background"]["allergies"], "Penicillin")
        self.assertEqual(saved["personal_values"]["most_important_goal"], "Time with family")
        self.assertEqual(saved["treatment_preferences"]["cpr"], "Unsure")
        self.assertEqual(saved["treatment_preferences"]["artificial_hydration"], "Unsure")
        self.assertEqual(saved["treatment_preferences"]["artificial_nutrition"], "Yes")
        self.assertEqual(saved["treatment_preferences"]["preferred_place_of_care"], "No preference")
        self.assertEqual(saved["treatment_preferences"]["goals_of_care"], "A balance of comfort and life-prolonging treatment")
        self.assertEqual(saved["treatment_preferences"]["last_rites"], "No specific wishes")
        detail = self.client.get(f"/api/doctor/patient/{self.patient1.patient_id}", headers=self.doc_headers)
        self.assertEqual(detail.status_code, 200)
        patient_detail = json.loads(detail.data)["patient"]
        self.assertEqual(patient_detail["chronic_conditions"], "Diabetes")
        self.assertEqual(patient_detail["allergies"], "Penicillin")
        acp_detail = json.loads(detail.data)["acp_preferences"]
        self.assertEqual(acp_detail["cpr_preference"], "UNSURE")
        self.assertEqual(acp_detail["ventilator_preference"], "WANT")
        self.assertEqual(acp_detail["dialysis_preference"], "DO NOT WANT")
        self.assertEqual(acp_detail["nutrition_hydration_preference"], "WANT")
        self.assertEqual(acp_detail["iv_fluids_preference"], "UNSURE")
        self.assertEqual(acp_detail["chemotherapy_preference"], "UNSURE")
        self.assertEqual(acp_detail["radiotherapy_preference"], "WANT")
        self.assertEqual(acp_detail["surgery_preference"], "DO NOT WANT")

    def test_combined_prompts_keep_canonical_fields_separate_and_profile_values(self):
        self.patient1.phone = "+1 555 123 4567"
        self.patient1.address = "12 Test Street"
        db.session.commit()

        # Use correct canonical Q numbers: Q7=chronic_conditions, Q8=serious_hospitalization,
        # Q9=long_term_medications, Q10=allergies, Q37=organ_donation, Q38=body_donation
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 7, "Diabetes", self.user_p1.id,
        )
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 8, "Prior stroke admission", self.user_p1.id,
        )
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 9, "Metformin", self.user_p1.id,
        )
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 10, "Penicillin", self.user_p1.id,
        )
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 37, "Unsure", self.user_p1.id,
        )
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 38, "No", self.user_p1.id,
        )
        # A partial edit of DHR phone must update patient.phone.
        # Q28 strips "Phone: " prefix and always updates patient.phone.
        AIService._persist_canonical_answer(
            self.patient1.patient_id, 28, "Phone: +1 555 999 0000", self.user_p1.id
        )
        db.session.commit()

        db.session.refresh(self.patient1)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(self.patient1.chronic_conditions, "Diabetes")
        self.assertEqual(self.patient1.serious_hospitalization, "Prior stroke admission")
        self.assertEqual(self.patient1.long_term_medications, "Metformin")
        self.assertEqual(self.patient1.allergies, "Penicillin")
        self.assertEqual(pref.organ_donation, "UNSURE")
        self.assertEqual(pref.body_donation, "NO")
        self.assertEqual(self.patient1.phone, "+1 555 999 0000")
        self.assertEqual(self.patient1.address, "12 Test Street")

    @patch("requests.request")
    def test_health_endpoint(self, mock_req):
        """GET /api/ai/health returns healthy when microservice is up and degraded when down."""
        # 1. Microservice healthy
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "healthy", "service": "AHCP AI Service", "version": "1.0.0"}
        mock_req.return_value = mock_resp

        res = self.client.get("/api/ai/health")
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "healthy")
        self.assertTrue(data["backend_connected"])

        # 2. Microservice connection error
        mock_req.side_effect = requests.exceptions.ConnectionError("Connection refused")
        res2 = self.client.get("/api/ai/health")
        self.assertEqual(res2.status_code, 503)
        data2 = json.loads(res2.data)
        self.assertEqual(data2["status"], "degraded")
        self.assertFalse(data2["backend_connected"])

    def test_missing_and_invalid_authentication(self):
        """AI endpoints strictly reject missing or invalid auth tokens."""
        # Missing header
        res1 = self.client.post("/api/ai/session", data=json.dumps({"language": "en"}), content_type="application/json")
        self.assertEqual(res1.status_code, 401)

        # Invalid token
        res2 = self.client.post(
            "/api/ai/session",
            data=json.dumps({"language": "en"}),
            headers={"Authorization": "Bearer invalid.jwt.token", "Content-Type": "application/json"}
        )
        self.assertEqual(res2.status_code, 401)

        # Doctor cannot create a patient questionnaire session directly
        res3 = self.client.post(
            "/api/ai/session",
            data=json.dumps({"language": "en"}),
            headers=self.doc_headers
        )
        self.assertEqual(res3.status_code, 403)

    @patch("requests.request")
    def test_create_session_success_and_binding(self, mock_req):
        """POST /api/ai/session creates session in FastAPI and binds to authenticated patient."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "session_id": "session_test_12345",
            "language": "kn",
            "question_number": 1,
            "question": "ನಿಮ್ಮ ಪೂರ್ಣ ಹೆಸರು ಏನು?",
            "options": None
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/session",
            data=json.dumps({"language": "kn"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["session_id"], "session_test_12345")
        self.assertEqual(data["language"], "kn")

        # Verify DB binding
        ai_sess = AISession.query.filter_by(session_id="session_test_12345").first()
        self.assertIsNotNone(ai_sess)
        self.assertEqual(ai_sess.patient_id, self.patient1.patient_id)
        self.assertEqual(ai_sess.language, "kn")
        self.assertFalse(ai_sess.is_completed)
        self.assertEqual(mock_req.call_args.kwargs["json"]["known_answers"], {})

        # Verify patient preferred_language updated
        pat = Patient.query.get(self.patient1.patient_id)
        self.assertEqual(pat.preferred_language, "Kannada")

    @patch("requests.request")
    def test_session_pointer_controls_answer_mapping_and_invalid_dob_does_not_advance(self, mock_req):
        sess = AISession(session_id="sess_stable_qid", patient_id=self.patient1.patient_id, language="en", current_question=2)
        db.session.add(sess)
        db.session.commit()

        invalid = self.client.post(
            "/api/ai/chat", data=json.dumps({"session_id": sess.session_id, "message": "No"}), headers=self.p1_headers
        )
        self.assertEqual(invalid.status_code, 200)
        self.assertEqual(json.loads(invalid.data)["status"], "invalid")
        self.assertEqual(AISession.query.filter_by(session_id=sess.session_id).first().current_question, 2)
        mock_req.assert_not_called()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        # Simulate a stale/mismatched display number from the AI service.
        mock_resp.json.return_value = {
            "status": "saved", "message": "Saved", "question_number": 1,
            "answer": "Wrong model answer", "next_question": {"question_number": 9, "question": "Wrong next question"},
            "sources": None,
        }
        mock_req.return_value = mock_resp
        valid = self.client.post(
            "/api/ai/chat", data=json.dumps({"session_id": sess.session_id, "message": "12/10/2005"}), headers=self.p1_headers
        )
        self.assertEqual(valid.status_code, 200)
        db.session.refresh(self.patient1)
        self.assertEqual(str(self.patient1.date_of_birth), "2005-10-12")
        self.assertEqual(self.patient1.user.full_name, "Patient One")
        saved_session = AISession.query.filter_by(session_id=sess.session_id).first()
        self.assertEqual(saved_session.current_question, 3)
        self.assertEqual(json.loads(valid.data)["next_question"]["question_number"], 3)
        saved_turn = ChatHistory.query.filter_by(session_id=sess.session_id).first()
        self.assertEqual(saved_turn.question_number, 2)

    def test_question_specific_validation_rejects_unrelated_identity_answers(self):
        self.assertIsNotNone(AIService._validate_conversation_answer(1, "12/10/2005", "en"))
        self.assertIsNotNone(AIService._validate_conversation_answer(4, "No", "en"))
        self.assertIsNotNone(AIService._validate_conversation_answer(5, "Unsure", "en"))
        self.assertIsNotNone(AIService._validate_conversation_answer(2, "tomorrow", "en"))
        self.assertIsNone(AIService._validate_conversation_answer(2, "12/10/2005", "en"))

    @patch("backend.controllers.ai_controller.AIService.process_chat", side_effect=RuntimeError("private database detail"))
    def test_unexpected_chat_failure_returns_actionable_reference_without_leaking_details(self, _mock_chat):
        sess = AISession(session_id="sess_error_reference", patient_id=self.patient1.patient_id, language="en", current_question=1)
        db.session.add(sess)
        db.session.commit()

        response = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": sess.session_id, "message": "Manvitha"}),
            headers=self.p1_headers,
        )

        self.assertEqual(response.status_code, 500)
        body = json.loads(response.data)
        self.assertIn("Please retry", body["message"])
        self.assertIn(body["reference"], body["message"])
        self.assertNotIn("private database detail", body["message"])

    @patch("requests.request")
    def test_cross_patient_access_denial(self, mock_req):
        """A patient cannot submit messages or view records for another patient's session."""
        # Setup session owned by Patient 1
        sess = AISession(session_id="p1_secret_session", patient_id=self.patient1.patient_id, language="en")
        db.session.add(sess)
        db.session.commit()

        # Patient 2 attempts to chat in Patient 1's session
        chat_res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "p1_secret_session", "message": "Hacked message"}),
            headers=self.p2_headers
        )
        self.assertEqual(chat_res.status_code, 403)
        self.assertIn("permission", json.loads(chat_res.data)["message"].lower())

        # Patient 2 attempts to retrieve Patient 1's record
        rec_res = self.client.post(
            "/api/ai/patient-record?session_id=p1_secret_session",
            headers=self.p2_headers
        )
        self.assertEqual(rec_res.status_code, 403)

    @patch("requests.request")
    def test_chat_status_saved_and_persistence(self, mock_req):
        """Answer with status 'saved' updates preferences without completing ACP workflow."""
        sess = AISession(
            session_id="sess_treatment_cpr",
            patient_id=self.patient1.patient_id,
            language="en",
            current_question=10
        )
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "saved",
            "message": "Your answer has been saved.",
            "question_number": 10,
            "answer": "Yes",
            "next_question": {
                "question_number": 11,
                "question": "If you are unable to breathe, would you want a ventilator?",
                "options": ["Yes", "No", "Unsure"]
            },
            "sources": None
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_treatment_cpr", "message": "Yes"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)

        # Verify CPR preference persisted
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.cpr_preference, "WANT")

        # CRITICAL TEST: ACP workflow must NOT be marked complete merely because an answer was saved!
        self.assertFalse(pref.is_completed)

        # Verify next question updated in AISession
        updated_sess = AISession.query.filter_by(session_id="sess_treatment_cpr").first()
        self.assertEqual(updated_sess.current_question, 11)

        # Verify chat turn recorded in ChatHistory
        history = ChatHistory.query.filter_by(session_id="sess_treatment_cpr").all()
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].user_message, "Yes")

    @patch("requests.request")
    def test_chat_status_explanation_unsure_persists_unresolved_choice(self, mock_req):
        """An explicit Unsure answer is retained while the question remains available."""
        sess = AISession(
            session_id="sess_unsure_flow",
            patient_id=self.patient1.patient_id,
            language="en",
            current_question=10
        )
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "explanation",
            "message": "Cardiopulmonary resuscitation (CPR) is an emergency procedure...",
            "question_number": 10,
            "answer": None,
            "next_question": None,
            "sources": [{"source": "CPR Guide.pdf", "category": "knowledge", "score": 0.85}]
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_unsure_flow", "message": "Unsure"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "explanation")

        # Explicit Unsure is retained as a distinct answer for the dashboard and AMD.
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.cpr_preference, "UNSURE")

        # Explicit Unsure is a saved choice, so the conversation advances.
        sess_db = AISession.query.filter_by(session_id="sess_unsure_flow").first()
        self.assertEqual(sess_db.current_question, 11)

    @patch("requests.request")
    def test_chat_status_invalid_allows_retry(self, mock_req):
        """Status 'invalid' displays options again and does not record invalid preference."""
        sess = AISession(
            session_id="sess_invalid_flow",
            patient_id=self.patient1.patient_id,
            language="en",
            current_question=10
        )
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "invalid",
            "message": "Please select one of the available options.",
            "question_number": 10,
            "answer": None,
            "next_question": {
                "question_number": 10,
                "question": "Would you want CPR?",
                "options": ["Yes", "No", "Unsure"]
            },
            "sources": None
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_invalid_flow", "message": "maybe someday"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "invalid")

        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        if pref:
            self.assertEqual(pref.cpr_preference, "NOT SPECIFIED")

    @patch("requests.request")
    def test_chat_status_completed_preserves_acp_review_rules(self, mock_req):
        """Questionnaire completion marks AISession complete, but preserves ACP workflow review rules."""
        sess = AISession(
            session_id="sess_q20_completion",
            patient_id=self.patient1.patient_id,
            language="en",
            current_question=20
        )
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "completed",
            "message": "Thank you. The AHCP questionnaire has been completed.",
            "question_number": 20,
            "answer": "Comfort care with loved ones nearby.",
            "next_question": None,
            "sources": None
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_q20_completion", "message": "Comfort care with loved ones nearby."}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)

        # Remaining treatment preferences follow the primary questions (Q33).
        ai_sess = AISession.query.filter_by(session_id="sess_q20_completion").first()
        self.assertFalse(ai_sess.is_completed)
        self.assertEqual(ai_sess.current_question, 33)

        # Q20 = preferred_place_of_care in new canonical schema. The answer is persisted there.
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.preferred_place_of_care, "Comfort care with loved ones nearby.")

        # CRITICAL TEST: ACPPreference.is_completed must NOT be True!
        # Existing ACP workflow requires explicit Confirmation & Review action.
        self.assertFalse(pref.is_completed)
        self.assertEqual(pref.review_status, "Pending Review")

    @patch("requests.request")
    def test_chat_status_answer_rag_mode(self, mock_req):
        """Post-questionnaire RAG answers are not mistaken for saved ACP decisions."""
        sess = AISession(
            session_id="sess_rag_post_q",
            patient_id=self.patient1.patient_id,
            language="en",
            is_completed=True,
            current_question=None
        )
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "answer",
            "message": "Advance directives are legal documents recognized in India.",
            "question_number": None,
            "answer": "Advance directives are legal documents recognized in India.",
            "next_question": None,
            "sources": [{"source": "Legal Aspects.pdf", "score": 0.88}]
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_rag_post_q", "message": "Is a living will legally valid in India?"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "answer")

    @patch("requests.request")
    def test_ai_service_timeout_and_error_handling(self, mock_req):
        """AI service failures return suitable HTTP error codes without leaking keys."""
        sess = AISession(session_id="sess_err_test", patient_id=self.patient1.patient_id, language="en")
        db.session.add(sess)
        db.session.commit()

        # Timeout
        mock_req.side_effect = requests.exceptions.Timeout("Connection timed out")
        res_timeout = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_err_test", "message": "Hello"}),
            headers=self.p1_headers
        )
        self.assertEqual(res_timeout.status_code, 504)
        self.assertNotIn("test-secret-key-123", res_timeout.text)

        # Service unavailable
        mock_req.side_effect = requests.exceptions.ConnectionError("Service down")
        res_conn = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_err_test", "message": "Hello"}),
            headers=self.p1_headers
        )
        self.assertEqual(res_conn.status_code, 503)
        self.assertNotIn("test-secret-key-123", res_conn.text)

    @patch("requests.request")
    def test_proxy_unsure_treatment_explanation_saves_preference(self, mock_req):
        """When patient selects Unsure for treatment question Q10, retain that choice."""
        sess = AISession(session_id="sess_unsure_proxy", patient_id=self.patient1.patient_id, language="en", current_question=10)
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "explanation",
            "message": "Medical Information: Cardiopulmonary Resuscitation (CPR)...",
            "question_number": 10,
            "answer": None,
            "next_question": None,
            "sources": [{"source": "CPR _ Cardiopulmonary Resuscitation _ MedlinePlus.pdf", "score": 0.62}]
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_unsure_proxy", "message": "Unsure"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "explanation")
        self.assertEqual(data["question_number"], 10)
        self.assertTrue(len(data.get("sources", [])) > 0)

        # Unsure is a persisted choice and the conversation advances to the next question.
        reloaded_sess = AISession.query.filter_by(session_id="sess_unsure_proxy").first()
        self.assertEqual(reloaded_sess.current_question, 11)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.cpr_preference, "UNSURE")

        # Chat history contains the explanation turn
        history = ChatHistory.query.filter_by(patient_id=self.patient1.patient_id, conversation_id="sess_unsure_proxy").first()
        self.assertIsNotNone(history)
        self.assertEqual(history.user_message, "Unsure")
        self.assertIn("Cardiopulmonary Resuscitation", history.bot_response)

    @patch("requests.request")
    def test_proxy_final_choice_after_unsure_saves_preference(self, mock_req):
        """After reading Unsure explanation, patient selecting Yes saves canonical preference and advances question."""
        sess = AISession(session_id="sess_unsure_then_yes", patient_id=self.patient1.patient_id, language="en", current_question=10)
        db.session.add(sess)
        db.session.commit()

        # Step 1: Unsure
        mock_resp1 = MagicMock()
        mock_resp1.ok = True
        mock_resp1.status_code = 200
        mock_resp1.json.return_value = {
            "status": "explanation",
            "message": "Medical Information: Cardiopulmonary Resuscitation (CPR)...",
            "question_number": 10,
            "answer": None,
            "next_question": None,
            "sources": [{"source": "CPR _ Cardiopulmonary Resuscitation _ MedlinePlus.pdf", "score": 0.62}]
        }
        mock_req.return_value = mock_resp1

        res1 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_unsure_then_yes", "message": "Unsure"}),
            headers=self.p1_headers
        )
        self.assertEqual(res1.status_code, 200)

        # Step 2: Patient decides on "Yes"
        mock_resp2 = MagicMock()
        mock_resp2.ok = True
        mock_resp2.status_code = 200
        mock_resp2.json.return_value = {
            "status": "saved",
            "message": "Your answer has been saved.",
            "question_number": 10,
            "answer": "Yes",
            "next_question": {"question_number": 11, "question": "Would you want ventilator?", "options": ["Yes", "No", "Unsure"]},
            "sources": None
        }
        mock_req.return_value = mock_resp2

        res2 = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_unsure_then_yes", "message": "Yes"}),
            headers=self.p1_headers
        )
        self.assertEqual(res2.status_code, 200)
        data2 = json.loads(res2.data)
        self.assertEqual(data2["status"], "saved")

        # Unsure remains the CPR answer; the following Yes belongs to ventilation.
        reloaded_sess = AISession.query.filter_by(session_id="sess_unsure_then_yes").first()
        self.assertEqual(reloaded_sess.current_question, 12)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.cpr_preference, "UNSURE")
        self.assertEqual(pref.ventilator_preference, "WANT")

    @patch("requests.request")
    def test_doctor_dashboard_authorization(self, mock_req):
        """Doctor can view dashboard data for authorized patient, but unfiltered query is rejected."""
        sess = AISession(session_id="sess_doc_view", patient_id=self.patient1.patient_id, language="en")
        db.session.add(sess)
        db.session.commit()

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "patient_information": {"full_name": "Patient One"},
            "medical_background": {},
            "treatment_preferences": {"cpr": "Yes", "ventilator": "No", "dialysis": "Unsure"},
            "personal_values": {},
            "visualization": {
                "preference_summary": {"yes": 1, "no": 1, "unsure": 1},
                "unanswered_preferences": ["organ_donation"],
                "unresolved_preferences": ["dialysis"]
            }
        }
        mock_req.return_value = mock_resp

        # Doctor queries with patient_id
        doc_res = self.client.get(
            f"/api/ai/doctor-dashboard?patient_id={self.patient1.patient_id}",
            headers=self.doc_headers
        )
        self.assertEqual(doc_res.status_code, 200)
        data = json.loads(doc_res.data)
        self.assertEqual(data["visualization"]["preference_summary"]["yes"], 1)
        self.assertIn("dialysis", data["visualization"]["unresolved_preferences"])

        # Unfiltered request with no session_id and no patient_id must be rejected
        unfiltered_res = self.client.get("/api/ai/doctor-dashboard", headers=self.doc_headers)
        self.assertEqual(unfiltered_res.status_code, 400)

        # Patient cannot access another patient's dashboard data
        patient_cross_res = self.client.get(
            f"/api/ai/doctor-dashboard?patient_id={self.patient2.patient_id}",
            headers=self.p1_headers
        )
        self.assertEqual(patient_cross_res.status_code, 403)

    @patch("requests.request")
    def test_canonical_answer_mapping_across_sections(self, mock_req):
        """Chatbot answers across sections automatically persist into user, patient, DHR, and ACPPreference."""
        sess = AISession(session_id="sess_cross_section", patient_id=self.patient1.patient_id, language="en", current_question=1)
        db.session.add(sess)
        db.session.commit()

        # Helper to send message and mock FastAPI response
        def send_answer(q_num, answer_text, next_q):
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "status": "saved",
                "message": f"Answer for Q{q_num} recorded.",
                "question_number": q_num,
                "answer": answer_text,
                "next_question": {"question_number": next_q, "question": f"Q{next_q} prompt", "options": ["Yes", "No"]},
                "sources": None
            }
            mock_req.return_value = mock_resp
            res = self.client.post(
                "/api/ai/chat",
                data=json.dumps({"session_id": "sess_cross_section", "message": answer_text}),
                headers=self.p1_headers
            )
            self.assertEqual(res.status_code, 200)

        # 1. Personal Information (Q1: name, Q2: DOB, Q3: gender)
        send_answer(1, "Aarav Sharma", 2)
        pat = Patient.query.get(self.patient1.patient_id)
        self.assertEqual(pat.user.full_name, "Aarav Sharma")

        send_answer(2, "1985-06-20", 3)
        pat = Patient.query.get(self.patient1.patient_id)
        self.assertGreater(pat.age, 35)

        send_answer(3, "Male", 4)
        pat = Patient.query.get(self.patient1.patient_id)
        self.assertEqual(pat.gender, "Male")

        # 2. Designated Healthcare Representative (Q4: name, Q5: relationship)
        send_answer(4, "Priya Sharma", 5)
        dhr = DHR.query.filter_by(patient_id=self.patient1.patient_id, preference_order=1).first()
        self.assertIsNotNone(dhr)
        self.assertEqual(dhr.full_name, "Priya Sharma")

        send_answer(5, "Spouse", 6)
        dhr = DHR.query.filter_by(patient_id=self.patient1.patient_id, preference_order=1).first()
        self.assertEqual(dhr.relationship, "Spouse")

        # 3. Medical background precedes the treatment preference questions.
        send_answer(6, "Diabetes", 7)
        send_answer(7, "No serious hospitalization", 8)
        send_answer(8, "None", 9)
        send_answer(9, "No known allergies", 10)

        # 4. Medical Directives (Q10: CPR, Q11: Vent, Q12: Dialysis, Q13: Nutrition, Q14: Hydration)
        send_answer(10, "Yes", 11)
        send_answer(11, "No", 12)
        send_answer(12, "Yes", 13)
        send_answer(13, "Yes", 14)
        send_answer(14, "No", 15)

        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.cpr_preference, "WANT")
        self.assertEqual(pref.ventilator_preference, "DO NOT WANT")
        self.assertEqual(pref.dialysis_preference, "WANT")
        self.assertEqual(pref.nutrition_hydration_preference, "WANT")
        self.assertEqual(pref.iv_fluids_preference, "DO NOT WANT")

        # 5. Organ Donation (Q15)
        send_answer(15, "Yes", 16)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.organ_donation, "YES")

        # 6. End-of-Life Wishes and values follow the treatment questions.
        send_answer(16, "Comfort-focused care", 17)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertIn("comfort", pref.goals_of_care.lower())
        self.assertIsNone(pref.pain_management)

        send_answer(17, "Home", 18)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.preferred_place_of_care, "Home")

        send_answer(18, "Limited medical treatment", 19)
        send_answer(19, "Time with family", 20)

        send_answer(20, "Keep family close and play soft music.", 33)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.additional_wishes, "Keep family close and play soft music.")

    @patch("requests.request")
    def test_kannada_canonical_mapping(self, mock_req):
        """Kannada responses store identical canonical database values as English responses."""
        sess = AISession(session_id="sess_kannada_canon", patient_id=self.patient1.patient_id, language="kn", current_question=10)
        db.session.add(sess)
        db.session.commit()

        def send_kn_answer(q_num, answer_text, next_q):
            mock_resp = MagicMock()
            mock_resp.ok = True
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "status": "saved",
                "message": f"Answer for Q{q_num} recorded in Kannada.",
                "question_number": q_num,
                "answer": answer_text,
                "next_question": {"question_number": next_q, "question": "ಮುಂದಿನ ಪ್ರಶ್ನೆ", "options": ["ಹೌದು", "ಇಲ್ಲ"]},
                "sources": None
            }
            mock_req.return_value = mock_resp
            res = self.client.post(
                "/api/ai/chat",
                data=json.dumps({"session_id": "sess_kannada_canon", "message": answer_text}),
                headers=self.p1_headers
            )
            self.assertEqual(res.status_code, 200)

        # Q10 CPR: "ಹೌದು" -> WANT
        send_kn_answer(10, "ಹೌದು", 11)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.cpr_preference, "WANT")

        # Q11 Ventilator: "ಇಲ್ಲ" -> DO NOT WANT
        send_kn_answer(11, "ಇಲ್ಲ", 12)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.ventilator_preference, "DO NOT WANT")

        send_kn_answer(12, "ಹೌದು", 13)
        send_kn_answer(13, "ಇಲ್ಲ", 14)
        send_kn_answer(14, "ಖಚಿತವಿಲ್ಲ", 15)

        # Q15 Organ Donation: "ಹೌದು" -> YES
        send_kn_answer(15, "ಹೌದು", 16)
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.organ_donation, "YES")

    @patch("requests.request")
    def test_unsure_response_treatment_remains_unresolved_in_dashboard(self, mock_req):
        """Unsure response never commits a final treatment decision and flags as unresolved."""
        sess = AISession(session_id="sess_unsure_unresolved", patient_id=self.patient1.patient_id, language="en", current_question=10)
        db.session.add(sess)
        db.session.commit()

        # Send Unsure for CPR (Q10)
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "explanation",
            "message": "CPR is an emergency procedure used when the heart stops...",
            "question_number": 10,
            "answer": "Unsure",
            "next_question": None,
            "sources": [{"source": "clinical_kb", "category": "treatments"}]
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_unsure_unresolved", "message": "Unsure"}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "explanation")

        # Preserve the explicit Unsure choice without treating it as Yes or No.
        pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertEqual(pref.cpr_preference, "UNSURE")

        # When doctor queries dashboard, CPR must be in unresolved_preferences
        # Mocking FastAPI failure to test the database synthesis fallback
        mock_req.side_effect = requests.exceptions.ConnectionError("FastAPI down")
        doc_res = self.client.get(
            f"/api/ai/doctor-dashboard?patient_id={self.patient1.patient_id}",
            headers=self.doc_headers
        )
        self.assertEqual(doc_res.status_code, 200)
        dash_data = json.loads(doc_res.data)
        self.assertIn("cpr", dash_data["visualization"]["unresolved_preferences"])

    @patch("requests.request")
    def test_questionnaire_completion_does_not_mark_acp_complete(self, mock_req):
        """Completing the 20-question AI session sets session completion, NOT ACPPreference.is_completed."""
        sess = AISession(session_id="sess_completion_isolation", patient_id=self.patient1.patient_id, language="en", current_question=20)
        db.session.add(sess)
        # Ensure ACPPreference exists
        pref = ACPPreference(patient_id=self.patient1.patient_id, is_completed=False)
        db.session.add(pref)
        db.session.commit()

        # Send answer to Q20
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "completed",
            "message": "Thank you for completing the questionnaire.",
            "question_number": 20,
            "answer": "Soft music and close family.",
            "next_question": None,
            "sources": None
        }
        mock_req.return_value = mock_resp

        res = self.client.post(
            "/api/ai/chat",
            data=json.dumps({"session_id": "sess_completion_isolation", "message": "Soft music and close family."}),
            headers=self.p1_headers
        )
        self.assertEqual(res.status_code, 200)

        # AI session advances into follow-up flow
        reloaded_sess = AISession.query.filter_by(session_id="sess_completion_isolation").first()
        self.assertFalse(reloaded_sess.is_completed)
        self.assertIsNotNone(reloaded_sess.current_question)

        # But overall ACP record is STILL NOT completed
        reloaded_pref = ACPPreference.query.filter_by(patient_id=self.patient1.patient_id).first()
        self.assertFalse(reloaded_pref.is_completed)

    @patch("requests.request")
    def test_database_synthesis_fallback_when_fastapi_restarts(self, mock_req):
        """When FastAPI loses memory/restarts, patient record and doctor dashboard synthesize from DB without losing data."""
        # Seed rich data in PostgreSQL/SQLite
        self.patient1.user.full_name = "Kavya Murthy"
        self.patient1.age = 58
        self.patient1.gender = "Female"
        self.patient1.beliefs_values = "[Chronic Conditions: Diabetes] [Medications: Metformin]"
        pref = ACPPreference(
            patient_id=self.patient1.patient_id,
            cpr_preference="WANT",
            ventilator_preference="DO NOT WANT",
            dialysis_preference="WANT",
            nutrition_hydration_preference="WANT",
            iv_fluids_preference="WANT",
            organ_donation="YES",
            preferred_place_of_care="Home",
            pain_management="Comfort care prioritized",
            is_completed=False
        )
        dhr = DHR(
            patient_id=self.patient1.patient_id,
            full_name="Rajesh Murthy",
            relationship="Son",
            mobile_primary="+919876543210",
            email_primary="rajesh@example.com",
            preference_order=1
        )
        sess = AISession(session_id="sess_lost_restart", patient_id=self.patient1.patient_id, language="en", current_question=15)
        db.session.add_all([pref, dhr, sess])
        db.session.commit()

        # Simulate FastAPI returning 404 (session lost due to restart)
        mock_resp = MagicMock()
        mock_resp.ok = False
        mock_resp.status_code = 404
        mock_resp.json.return_value = {"detail": "Session not found"}
        mock_req.return_value = mock_resp

        # Request patient record
        rec_res = self.client.get(
            f"/api/ai/patient-record?patient_id={self.patient1.patient_id}",
            headers=self.p1_headers
        )
        self.assertEqual(rec_res.status_code, 200)
        rec_data = json.loads(rec_res.data)
        self.assertEqual(rec_data["patient_information"]["full_name"], "Kavya Murthy")
        self.assertEqual(rec_data["treatment_preferences"]["cpr"], "Yes")
        self.assertEqual(rec_data["treatment_preferences"]["ventilator"], "No")
        self.assertEqual(rec_data["personal_values"]["designated_representative_name"], "Rajesh Murthy")

        # Request doctor dashboard
        doc_res = self.client.get(
            f"/api/ai/doctor-dashboard?patient_id={self.patient1.patient_id}",
            headers=self.doc_headers
        )
        self.assertEqual(doc_res.status_code, 200)
        doc_data = json.loads(doc_res.data)
        self.assertEqual(doc_data["patient_information"]["full_name"], "Kavya Murthy")
        self.assertEqual(doc_data["visualization"]["preference_summary"]["yes"], 5)
        self.assertEqual(doc_data["visualization"]["preference_summary"]["no"], 1)

if __name__ == "__main__":
    unittest.main()
