import sys
import os
import unittest
from unittest.mock import patch

_backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
_root_dir = os.path.abspath(os.path.join(_backend_dir, ".."))
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from backend.app import create_app
from backend.config import Config
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.ai_session import AISession
from backend.models.chat_history import ChatHistory
from backend.services.ai_service import AIService


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key-123'
    JWT_SECRET_KEY = 'test-jwt-secret'


class TestNaturalLanguageNormalization(unittest.TestCase):
    """Test unit normalization of typed natural language phrases across questions."""

    def test_yes_no_unsure_english_variations(self):
        # Q11: CPR
        self.assertEqual(AIService.normalize_answer_to_canonical("Yes, I need it", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("yes i want it", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("I need this", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("Yes please", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("Definitely yes", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("I agree", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("provide it", 11), "Yes")

        self.assertEqual(AIService.normalize_answer_to_canonical("No, I don't need it", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("No, I don't want it", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("no i dont want it", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("I do not want this treatment", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("don't want", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("do not want", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("not needed", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("withhold", 11), "No")

        self.assertEqual(AIService.normalize_answer_to_canonical("Unsure", 11), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("not sure", 11), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("I am unsure", 11), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("I'm not sure", 11), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("undecided", 11), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("don't know", 11), "Unsure")

    def test_yes_no_unsure_kannada_variations(self):
        self.assertEqual(AIService.normalize_answer_to_canonical("ಹೌದು, ನನಗೆ ಬೇಕು", 11), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("ನನಗೆ ಇದು ಬೇಕು", 12), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("ಖಂಡಿತ ಹೌದು", 13), "Yes")
        self.assertEqual(AIService.normalize_answer_to_canonical("ಬಯಸುತ್ತೇನೆ", 14), "Yes")

        self.assertEqual(AIService.normalize_answer_to_canonical("ಇಲ್ಲ, ನನಗೆ ಬೇಡ", 11), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("ನನಗೆ ಇದು ಬೇಡ", 12), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("ಖಂಡಿತ ಇಲ್ಲ", 13), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("ಬೇಡವೇ ಬೇಡ", 14), "No")
        self.assertEqual(AIService.normalize_answer_to_canonical("ಬಯಸುವುದಿಲ್ಲ", 15), "No")

        self.assertEqual(AIService.normalize_answer_to_canonical("ಖಚಿತವಿಲ್ಲ", 11), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("ಗೊತ್ತಿಲ್ಲ", 12), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("ತಿಳಿದಿಲ್ಲ", 13), "Unsure")
        self.assertEqual(AIService.normalize_answer_to_canonical("ತೀರ್ಮಾನಿಸಿಲ್ಲ", 14), "Unsure")

    def test_goals_and_place_of_care(self):
        # Q19: Goals of care
        self.assertEqual(AIService.normalize_answer_to_canonical("Comfort-focused care", 19), "Comfort-focused care")
        self.assertEqual(AIService.normalize_answer_to_canonical("I prefer comfort care", 19), "Comfort-focused care")
        self.assertEqual(AIService.normalize_answer_to_canonical("focus on comfort and pain relief", 19), "Comfort-focused care")
        self.assertEqual(AIService.normalize_answer_to_canonical("Life-prolonging treatment", 19), "Life-prolonging treatment")
        self.assertEqual(AIService.normalize_answer_to_canonical("A balance of comfort and life-prolonging treatment", 19), "A balance of comfort and life-prolonging treatment")
        self.assertEqual(AIService.normalize_answer_to_canonical("balance of both", 19), "A balance of comfort and life-prolonging treatment")

        # Q20: Place of care
        self.assertEqual(AIService.normalize_answer_to_canonical("Home", 20), "Home")
        self.assertEqual(AIService.normalize_answer_to_canonical("At home", 20), "Home")
        self.assertEqual(AIService.normalize_answer_to_canonical("I prefer to be at home", 20), "Home")
        self.assertEqual(AIService.normalize_answer_to_canonical("Hospital", 20), "Hospital")
        self.assertEqual(AIService.normalize_answer_to_canonical("In a hospital", 20), "Hospital")
        self.assertEqual(AIService.normalize_answer_to_canonical("No preference", 20), "No preference")
        self.assertEqual(AIService.normalize_answer_to_canonical("I don't have any preference", 20), "No preference")

    def test_validation_rejects_genuinely_invalid_input(self):
        # Q11 CPR: 'banana' should be invalid
        err = AIService._validate_conversation_answer(11, "banana", language="en")
        self.assertEqual(err, "Choose Yes, No, or Unsure.")

        # Q11 CPR: '12345' should be invalid
        err_num = AIService._validate_conversation_answer(11, "12345", language="en")
        self.assertEqual(err_num, "Choose Yes, No, or Unsure.")

        # Kannada validation message
        err_kn = AIService._validate_conversation_answer(11, "banana", language="kn")
        self.assertIn("ಹೌದು, ಇಲ್ಲ ಅಥವಾ ಖಚಿತವಿಲ್ಲ", err_kn)

        # Empty input
        err_empty = AIService._validate_conversation_answer(11, "", language="en")
        self.assertEqual(err_empty, "Please enter an answer to this question.")

    def test_open_text_questions_preserve_wishes(self):
        # Q25: Additional wishes should NOT be coerced to Yes/No
        wishes = "I want to be surrounded by family and listen to classical music"
        norm = AIService.normalize_answer_to_canonical(wishes, 25)
        self.assertEqual(norm, wishes)


class TestProcessChatNaturalLanguage(unittest.TestCase):
    """End-to-end process_chat tests with typed natural language."""

    @classmethod
    def setUpClass(cls):
        cls.app = create_app(TestConfig)
        cls.app.config["TESTING"] = True
        cls.client = cls.app.test_client()

    def setUp(self):
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        user = User(
            email="test_nlp_patient@example.com",
            role="patient",
            full_name="Natural Language Patient"
        )
        user.set_password("SecurePass123!")
        db.session.add(user)
        db.session.flush()

        self.patient = Patient(
            user_id=user.id,
            current_address="123 Test Road, Bengaluru"
        )
        db.session.add(self.patient)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch("backend.services.ai_service.AIService._request")
    def test_process_chat_typed_yes_and_no(self, mock_request):
        mock_request.return_value = {"status": "saved", "message": "Answer recorded"}

        session = AISession(
            session_id="test_nlp_sess_1",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=11
        )
        db.session.add(session)
        db.session.commit()

        # 1. Patient types "Yes, I need it" for CPR (Q11) without clicking an option
        resp1 = AIService.process_chat(
            patient_id=self.patient.patient_id,
            session_id=session.session_id,
            message="Yes, I need it",
            question_number=11,
            performed_by_id=self.patient.user_id
        )

        self.assertEqual(resp1["status"], "saved")
        self.assertEqual(resp1["answer"], "Yes, I need it")
        self.assertEqual(resp1["next_question"]["question_number"], 12)

        # Check DB persistence: CPR preference should be WANT
        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        self.assertIsNotNone(pref)
        self.assertEqual(pref.cpr_preference, "WANT")

        # Check chat history displays typed message
        history = ChatHistory.query.filter_by(session_id=session.session_id).order_by(ChatHistory.id.desc()).first()
        self.assertIsNotNone(history)
        self.assertEqual(history.user_message, "Yes, I need it")

        # 2. Patient types "No, I don't need it" for Mechanical Ventilation (Q12)
        resp2 = AIService.process_chat(
            patient_id=self.patient.patient_id,
            session_id=session.session_id,
            message="No, I don't need it",
            question_number=12,
            performed_by_id=self.patient.user_id
        )

        self.assertEqual(resp2["status"], "saved")
        self.assertEqual(resp2["answer"], "No, I don't need it")
        self.assertEqual(resp2["next_question"]["question_number"], 13)

        # Check DB persistence: Ventilator preference should be DO NOT WANT
        db.session.refresh(pref)
        self.assertEqual(pref.ventilator_preference, "DO NOT WANT")

        history2 = ChatHistory.query.filter_by(session_id=session.session_id).order_by(ChatHistory.id.desc()).first()
        self.assertEqual(history2.user_message, "No, I don't need it")

    @patch("backend.services.ai_service.AIService._request")
    def test_process_chat_kannada_typed_answers(self, mock_request):
        mock_request.return_value = {"status": "saved", "message": "ನಿಮ್ಮ ಉತ್ತರವನ್ನು ಉಳಿಸಲಾಗಿದೆ."}

        session = AISession(
            session_id="test_nlp_sess_kn",
            patient_id=self.patient.patient_id,
            language="kn",
            current_question=11
        )
        db.session.add(session)
        db.session.commit()

        # Patient types "ಹೌದು, ನನಗೆ ಬೇಕು"
        resp = AIService.process_chat(
            patient_id=self.patient.patient_id,
            session_id=session.session_id,
            message="ಹೌದು, ನನಗೆ ಬೇಕು",
            question_number=11,
            performed_by_id=self.patient.user_id
        )

        self.assertEqual(resp["status"], "saved")
        self.assertEqual(resp["answer"], "ಹೌದು, ನನಗೆ ಬೇಕು")
        self.assertEqual(resp["next_question"]["question_number"], 12)

        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        self.assertEqual(pref.cpr_preference, "WANT")

        history = ChatHistory.query.filter_by(session_id=session.session_id).order_by(ChatHistory.id.desc()).first()
        self.assertEqual(history.user_message, "ಹೌದು, ನನಗೆ ಬೇಕು")

    @patch("backend.services.ai_service.AIService._request")
    def test_process_chat_invalid_typed_input_rejected(self, mock_request):
        session = AISession(
            session_id="test_nlp_sess_invalid",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=11
        )
        db.session.add(session)
        db.session.commit()

        # Patient types "banana" on Q11
        resp = AIService.process_chat(
            patient_id=self.patient.patient_id,
            session_id=session.session_id,
            message="banana",
            question_number=11,
            performed_by_id=self.patient.user_id
        )

        self.assertEqual(resp["status"], "invalid")
        self.assertEqual(resp["message"], "Choose Yes, No, or Unsure.")
        self.assertEqual(session.current_question, 11)

        # Check DB: no preference saved
        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        if pref:
            self.assertNotIn(pref.cpr_preference, ("WANT", "DO NOT WANT"))

    @patch("backend.services.ai_service.AIService._request")
    def test_option_click_still_works(self, mock_request):
        mock_request.return_value = {"status": "saved", "message": "Answer recorded"}

        session = AISession(
            session_id="test_nlp_sess_opt",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=11
        )
        db.session.add(session)
        db.session.commit()

        # Patient clicks "Yes" option button
        resp = AIService.process_chat(
            patient_id=self.patient.patient_id,
            session_id=session.session_id,
            message="Yes",
            question_number=11,
            performed_by_id=self.patient.user_id
        )

        self.assertEqual(resp["status"], "saved")
        self.assertEqual(resp["answer"], "Yes")
        self.assertEqual(resp["next_question"]["question_number"], 12)

        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        self.assertEqual(pref.cpr_preference, "WANT")


if __name__ == "__main__":
    unittest.main()
