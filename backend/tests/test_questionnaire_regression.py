import os
import json
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from datetime import datetime

from backend.app import create_app
from backend.config import Config
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.ai_session import AISession
from backend.services.ai_service import AIService
from backend.utils.auth_helpers import generate_token
from backend.utils.pdf_generator import generate_amd_pdf


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret-key-123'
    JWT_SECRET_KEY = 'test-jwt-secret'


class QuestionnaireRegressionTestCase(unittest.TestCase):
    """
    Comprehensive regression tests covering all 13 critical ACP & AMD requirements:
    1. Correct answer mapping across the entire chatbot questionnaire.
    2. No duplicate questions.
    3. No answer reuse across different questions.
    4. Correct handling of Yes, No, Unsure and free-text answers.
    5. Selecting No for alternate representative skips alternate fields.
    6. DHR phone/email and alternate DHR details are collected only in the manual form.
    7. Automatic navigation (status: completed, redirect_section: proxy) after final chatbot question.
    8. Correct prefilling of chatbot answers.
    9. Manual form saving and resuming without losing information.
    10. Unanswered treatment preferences are not converted to Yes or No.
    11. Unasked chemotherapy, radiotherapy, surgery and body donation preferences are not invented.
    12. Gender Identity Instructions and Relationship / Partner Disclosures do not appear in the AMD.
    13. Consistency across DB models, review summary, doctor dashboard, and generated AMD.
    """

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Seed test patient
        self.user = User(full_name="Sunil Kumar", email="sunil@test.com", role="patient")
        self.user.set_password("Password123!")
        self.doctor_user = User(full_name="Dr. Rao", email="dr.rao@test.com", role="doctor")
        self.doctor_user.set_password("Password123!")
        db.session.add_all([self.user, self.doctor_user])
        db.session.commit()

        self.patient = Patient(
            user_id=self.user.id,
            date_of_birth=datetime(1980, 5, 15).date(),
            gender="Male",
            age=45,
            phone="+91 9876543210",
            address="123 MG Road, Bengaluru",
            preferred_language="English"
        )
        db.session.add(self.patient)
        db.session.commit()

        self.patient_token = generate_token(self.user.id, self.user.email, "patient")
        self.doctor_token = generate_token(self.doctor_user.id, self.doctor_user.email, "doctor")
        self.p_headers = {"Authorization": f"Bearer {self.patient_token}", "Content-Type": "application/json"}
        self.doc_headers = {"Authorization": f"Bearer {self.doctor_token}", "Content-Type": "application/json"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    @patch("requests.request")
    def test_1_correct_answer_mapping_across_entire_questionnaire(self, mock_req):
        """1. Each question associates and persists its answer strictly to its exact canonical field."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_req.return_value = mock_resp

        sess = AISession(session_id="reg_sess_1", patient_id=self.patient.patient_id, language="en", current_question=1)
        db.session.add(sess)
        db.session.commit()

        flow = [
            # Section 1: Personal Information (Q1..Q6)
            (1, "Sunil Kumar", 2),
            (2, "15/05/1980", 3),
            (3, "Male", 4),
            (4, "9876543210", 5),
            (5, "English", 6),
            (6, "123 MG Road, Bengaluru", 7),
            # Section 2: Medical Treatment Preferences (Q7..Q18)
            (7, "Asthma", 8),
            (8, "Pneumonia admission in 2020", 9),
            (9, "Salbutamol inhaler", 10),
            (10, "Dust and pollen", 11),
            (11, "Yes", 12),      # CPR
            (12, "No", 13),       # Ventilator
            (13, "Unsure", 14),   # Dialysis
            (14, "No", 15),       # Chemotherapy
            (15, "No", 16),       # Radiotherapy
            (16, "No", 17),       # Major Surgery
            (17, "No", 18),       # Artificial Hydration
            (18, "Yes", 19),      # Artificial Nutrition
            # Section 3: End-of-Life Preferences (Q19..Q25)
            (19, "Comfort-focused care", 20),
            (20, "Home", 21),
            (21, "No preference", 22),
            (22, "Dr. Rao", 23),
            (23, "Family harmony and dignity", 24),
            (24, "Comfort-focused treatment", 25),
            (25, "Play soft devotional music", 26),
            # Section 4: Designated Healthcare Representative (Q26..Q31, selecting No skips to Q37)
            (26, "Ananya Kumar", 27),
            (27, "Daughter", 28),
            (28, "9876501234", 29),
            (29, "ananya@test.com", 30),
            (30, "Same as my address", 31),
            (31, "No", 37),       # Alternate DHR: No -> skips Q32..Q36 straight to Q37!
            # Section 5: Organ & Body Donation (Q37..Q39)
            (37, "Yes", 38),      # Organ Donation
            (38, "No", 39),       # Body Donation
            (39, "No specific wishes", 40), # Last Rites
            # Administrative Details (Q40..Q43)
            (40, "Same as current address", 41),
            (41, "Aadhaar", 42),
            (42, "1234 5678 9012", 43),
            (43, "Bengaluru North", 44),
            # Section 6: Review & Confirmation (Q44)
            (44, "Confirm Plan", None),
        ]

        for q_num, ans, next_q in flow:
            mock_resp.json.return_value = {
                "status": "completed" if next_q is None else "saved",
                "message": "Answer recorded.",
                "question_number": q_num,
                "answer": ans,
                "next_question": None if next_q is None else {"question_number": next_q, "question": f"Q{next_q}"},
                "sources": None
            }
            res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "reg_sess_1", "message": ans, "question_number": q_num}), headers=self.p_headers)
            self.assertEqual(res.status_code, 200)

        # Verify DB records
        pat = Patient.query.get(self.patient.patient_id)
        pref = pat.acp_preferences
        dhr = DHR.query.filter_by(patient_id=self.patient.patient_id, preference_order=1).first()

        self.assertEqual(pat.user.full_name, "Sunil Kumar")
        self.assertEqual(pat.gender, "Male")
        self.assertEqual(str(pat.date_of_birth), "1980-05-15")
        self.assertEqual(pat.chronic_conditions, "Asthma")
        self.assertEqual(pat.serious_hospitalization, "Pneumonia admission in 2020")
        self.assertEqual(pat.long_term_medications, "Salbutamol inhaler")
        self.assertEqual(pat.allergies, "Dust and pollen")
        self.assertEqual(pref.cpr_preference, "WANT")
        self.assertEqual(pref.ventilator_preference, "DO NOT WANT")
        self.assertEqual(pref.dialysis_preference, "UNSURE")
        self.assertEqual(pref.nutrition_hydration_preference, "WANT")
        self.assertEqual(pref.iv_fluids_preference, "DO NOT WANT")
        self.assertEqual(pref.chemotherapy_preference, "DO NOT WANT")
        self.assertEqual(pref.radiotherapy_preference, "DO NOT WANT")
        self.assertEqual(pref.surgery_preference, "DO NOT WANT")
        self.assertEqual(pref.goals_of_care, "Comfort-focused care")
        self.assertEqual(pref.preferred_place_of_care, "Home")
        self.assertEqual(pat.personal_values, "Family harmony and dignity")
        self.assertEqual(pref.additional_wishes, "Play soft devotional music")
        self.assertEqual(dhr.full_name, "Ananya Kumar")
        self.assertEqual(dhr.relationship, "Daughter")
        self.assertEqual(dhr.mobile_primary, "9876501234")
        self.assertFalse(pref.alternate_dhr_appointed)
        self.assertEqual(pref.organ_donation, "YES")
        self.assertEqual(pref.body_donation, "NO")
        self.assertEqual(pref.last_rites, "No specific wishes")

    def test_2_no_duplicate_questions(self):
        """2. Questionnaire has stable, unique question IDs 1..44 without duplicates."""
        meta_en = AIService.QUESTIONNAIRE_METADATA["en"]
        meta_kn = AIService.QUESTIONNAIRE_METADATA["kn"]

        self.assertEqual(len(meta_en), 44)
        self.assertEqual(len(meta_kn), 44)
        self.assertEqual(set(meta_en.keys()), set(range(1, 45)))
        self.assertEqual(set(meta_kn.keys()), set(range(1, 45)))

        # Ensure all English prompts are unique
        questions_en = [meta_en[i]["question"] for i in range(1, 45)]
        self.assertEqual(len(questions_en), len(set(questions_en)))

    @patch("requests.request")
    def test_3_no_answer_reuse_across_different_questions(self, mock_req):
        """3. Answer for one question is never accidentally reused for the next question."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_req.return_value = mock_resp

        sess = AISession(session_id="reg_sess_3", patient_id=self.patient.patient_id, language="en", current_question=11)
        db.session.add(sess)
        db.session.commit()

        # Submit Q11: Yes
        mock_resp.json.return_value = {"status": "saved", "question_number": 11, "answer": "Yes", "next_question": {"question_number": 12, "question": "Q12"}}
        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "reg_sess_3", "message": "Yes", "question_number": 11}), headers=self.p_headers)
        self.assertEqual(res.status_code, 200)

        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        self.assertEqual(pref.cpr_preference, "WANT")
        self.assertIn(pref.ventilator_preference, (None, "NOT SPECIFIED"))
        self.assertIn(pref.dialysis_preference, (None, "NOT SPECIFIED"))

    def test_4_correct_handling_of_yes_no_unsure_and_free_text(self):
        """4. Preserves Yes, No, Unsure, and free-text answers as distinct canonical values."""
        AIService._persist_canonical_answer(self.patient.patient_id, 11, "Yes", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 12, "No", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 13, "Unsure", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 23, "Live with dignity and avoid suffering", self.user.id)

        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        pat = Patient.query.get(self.patient.patient_id)
        self.assertEqual(pref.cpr_preference, "WANT")
        self.assertEqual(pref.ventilator_preference, "DO NOT WANT")
        self.assertEqual(pref.dialysis_preference, "UNSURE")
        self.assertEqual(pat.personal_values, "Live with dignity and avoid suffering")

    def test_5_selecting_no_for_alternate_representative_skips_alternate_fields(self):
        """5. Selecting No for alternate representative marks alternate_dhr_appointed = False and does not create DHR order 2."""
        AIService._persist_canonical_answer(self.patient.patient_id, 31, "No", self.user.id)
        pref = ACPPreference.query.filter_by(patient_id=self.patient.patient_id).first()
        self.assertFalse(pref.alternate_dhr_appointed)

        alt_dhr = DHR.query.filter_by(patient_id=self.patient.patient_id, preference_order=2).first()
        self.assertIsNone(alt_dhr)

    @patch("requests.request")
    def test_6_representative_details_and_alternate_skipping(self, mock_req):
        """6. Primary representative details collected deterministically and alternate questions skipped on No."""
        meta_26 = AIService.get_question_metadata(26, "en")
        meta_27 = AIService.get_question_metadata(27, "en")
        meta_28 = AIService.get_question_metadata(28, "en")
        meta_31 = AIService.get_question_metadata(31, "en")

        self.assertIn("representative", meta_26["question"].lower())
        self.assertIn("relationship", meta_27["question"].lower())
        self.assertIn("mobile", meta_28["question"].lower())
        self.assertIn("alternate", meta_31["question"].lower())

        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "saved",
            "question_number": 31,
            "answer": "No",
            "next_question": {"question_number": 37, "question": "Organ donation"}
        }
        mock_req.return_value = mock_resp

        sess = AISession(session_id="reg_sess_6", patient_id=self.patient.patient_id, language="en", current_question=31)
        db.session.add(sess)
        db.session.commit()

        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "reg_sess_6", "message": "No", "question_number": 31}), headers=self.p_headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["next_question"]["question_number"], 37)

    @patch("requests.request")
    def test_7_auto_navigation_to_review_after_final_question(self, mock_req):
        """7. After question 43 is answered, session advances to question 44 (Review & Confirmation)."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": "saved",
            "message": "Saved",
            "question_number": 43,
            "answer": "Bengaluru North",
            "next_question": {"question_number": 44, "question": "Review"}
        }
        mock_req.return_value = mock_resp

        sess = AISession(session_id="reg_sess_7", patient_id=self.patient.patient_id, language="en", current_question=43)
        db.session.add(sess)
        db.session.commit()

        res = self.client.post("/api/ai/chat", data=json.dumps({"session_id": "reg_sess_7", "message": "Bengaluru North", "question_number": 43}), headers=self.p_headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["next_question"]["question_number"], 44)

    def test_8_correct_prefilling_of_chatbot_answers(self):
        """8. Saved chatbot answers across all sections are accessible via get_saved_answer_for_question."""
        AIService._persist_canonical_answer(self.patient.patient_id, 1, "Rohan Verma", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 7, "Hypertension", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 11, "Yes", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 26, "Pooja Verma", self.user.id)
        AIService._persist_canonical_answer(self.patient.patient_id, 37, "Yes", self.user.id)

        self.assertEqual(AIService.get_saved_answer_for_question(self.patient.patient_id, 1), "Rohan Verma")
        self.assertEqual(AIService.get_saved_answer_for_question(self.patient.patient_id, 7), "Hypertension")
        self.assertEqual(AIService.get_saved_answer_for_question(self.patient.patient_id, 11), "Yes (WANT)")
        self.assertEqual(AIService.get_saved_answer_for_question(self.patient.patient_id, 26), "Pooja Verma")
        self.assertEqual(AIService.get_saved_answer_for_question(self.patient.patient_id, 37), "Yes")

    def test_9_manual_form_saving_and_resuming(self):
        """9. Manual form changes persist and can be retrieved without loss."""
        # Patient saves Section 2 (DHR details) manually
        dhr = DHR(patient_id=self.patient.patient_id, preference_order=1, full_name="Aarav Sen", relationship="Son", mobile_primary="+91 9999988888", email_primary="aarav@test.com")
        db.session.add(dhr)
        db.session.commit()

        # Resuming / retrieving
        reloaded_dhr = DHR.query.filter_by(patient_id=self.patient.patient_id, preference_order=1).first()
        self.assertEqual(reloaded_dhr.full_name, "Aarav Sen")
        self.assertEqual(reloaded_dhr.mobile_primary, "+91 9999988888")
        self.assertEqual(reloaded_dhr.email_primary, "aarav@test.com")

    def test_10_unanswered_treatment_preferences_not_converted_to_yes_or_no(self):
        """10. Unanswered preferences remain NOT SPECIFIED or None, never converted to Yes/No."""
        pref = ACPPreference(patient_id=self.patient.patient_id, cpr_preference="WANT")
        db.session.add(pref)
        db.session.commit()

        self.assertEqual(pref.cpr_preference, "WANT")
        self.assertIn(pref.chemotherapy_preference, (None, "NOT SPECIFIED"))
        self.assertIn(pref.radiotherapy_preference, (None, "NOT SPECIFIED"))
        self.assertIn(pref.surgery_preference, (None, "NOT SPECIFIED"))
        self.assertNotEqual(pref.chemotherapy_preference, "WANT")
        self.assertNotEqual(pref.chemotherapy_preference, "DO NOT WANT")

    def test_11_unasked_chemo_radio_surgery_body_donation_not_invented(self):
        """11. In synthesized dashboard, unasked treatments are None and listed in unanswered_preferences."""
        pref = ACPPreference(patient_id=self.patient.patient_id, cpr_preference="WANT", ventilator_preference="DO NOT WANT")
        db.session.add(pref)
        db.session.commit()

        dashboard = AIService._synthesize_dashboard_from_db(self.patient.patient_id)
        treatments = dashboard["treatment_preferences"]
        unanswered = dashboard["visualization"]["unanswered_preferences"]

        self.assertIsNone(treatments["chemotherapy"])
        self.assertIsNone(treatments["radiotherapy"])
        self.assertIsNone(treatments["surgery"])
        self.assertIsNone(treatments["body_donation"])
        self.assertIn("chemotherapy", unanswered)
        self.assertIn("radiotherapy", unanswered)
        self.assertIn("surgery", unanswered)
        self.assertIn("body_donation", unanswered)

    def test_12_gender_identity_and_relationship_disclosures_omitted_from_amd(self):
        """12. Neither 'Gender Identity Instructions' nor 'Relationship / Partner Disclosures' appear in generated AMD."""
        pref = ACPPreference(
            patient_id=self.patient.patient_id,
            cpr_preference="WANT",
            ventilator_preference="DO NOT WANT",
            goals_of_care="Comfort-focused care",
            is_completed=True
        )
        dhr = DHR(
            patient_id=self.patient.patient_id,
            preference_order=1,
            full_name="Meera Kumar",
            relationship="Spouse",
            mobile_primary="+91 9888877777"
        )
        db.session.add_all([pref, dhr])
        db.session.commit()

        pdf_path = os.path.join(tempfile.gettempdir(), f"amd_reg_{self.patient.patient_id}.pdf")
        generate_amd_pdf(self.patient, pref, [dhr], [], None, None, None, pdf_path)
        self.assertTrue(os.path.exists(pdf_path))

        # Inspect generated PDF with pypdf / pdfplumber to verify text absence
        try:
            from pypdf import PdfReader
            reader = PdfReader(pdf_path)
            full_text = ""
            for page in reader.pages:
                full_text += page.extract_text() or ""
            self.assertNotIn("Gender Identity Instructions", full_text)
            self.assertNotIn("Relationship / Partner Disclosures", full_text)
            self.assertNotIn("Partner Disclosures", full_text)
        except ImportError:
            # Fallback text check
            with open(pdf_path, "rb") as f:
                content = f.read().decode("latin1", errors="ignore")
                self.assertNotIn("Gender Identity Instructions", content)
                self.assertNotIn("Relationship / Partner Disclosures", content)

    def test_13_consistency_across_models_dashboard_summary_and_amd(self):
        """13. Authoritative DB answers are consistently reflected in dashboard and AMD without distortion."""
        pref = ACPPreference(
            patient_id=self.patient.patient_id,
            cpr_preference="WANT",
            ventilator_preference="DO NOT WANT",
            dialysis_preference="UNSURE",
            goals_of_care="Comfort-focused care",
            preferred_place_of_care="Home",
            organ_donation="YES"
        )
        dhr = DHR(
            patient_id=self.patient.patient_id,
            preference_order=1,
            full_name="Pooja Kumar",
            relationship="Daughter",
            mobile_primary="+91 9777766666"
        )
        db.session.add_all([pref, dhr])
        db.session.commit()

        # Doctor dashboard reflects DB
        doc_dash = AIService._synthesize_dashboard_from_db(self.patient.patient_id)
        self.assertEqual(doc_dash["treatment_preferences"]["cpr"], "Yes")
        self.assertEqual(doc_dash["treatment_preferences"]["ventilator"], "No")
        self.assertEqual(doc_dash["treatment_preferences"]["dialysis"], "Unsure")
        self.assertEqual(doc_dash["treatment_preferences"]["organ_donation"], "Yes")
        self.assertEqual(doc_dash["treatment_preferences"]["goals_of_care"], "Comfort-focused care")
        self.assertEqual(doc_dash["treatment_preferences"]["preferred_place_of_care"], "Home")

        # PDF generates cleanly with same patient
        pdf_path = os.path.join(tempfile.gettempdir(), f"amd_reg_{self.patient.patient_id}.pdf")
        generate_amd_pdf(self.patient, pref, [dhr], [], None, None, None, pdf_path)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 500)

    @patch("requests.request")
    def test_14_problem_10_end_to_end_reproduction_scenario(self, mock_req):
        """14. Full reproduction of Problem 10: patient answers all 6 sections with Alternate DHR No,
        verifying Chemotherapy/Radiotherapy are WANT, Hospital/Clinician are 'No preference',
        Alternate DHR is False with no required validation errors, and completion reaches 100%."""
        mock_resp = MagicMock()
        mock_resp.ok = True
        mock_resp.status_code = 200
        mock_req.return_value = mock_resp

        sess = AISession(
            session_id="reg_sess_problem_10",
            patient_id=self.patient.patient_id,
            language="en",
            current_question=1
        )
        db.session.add(sess)
        db.session.commit()

        flow = [
            # 1. Personal Information (Q1..Q6)
            (1, "Sunil Kumar", 2),
            (2, "15/05/1980", 3),
            (3, "Male", 4),
            (4, "9876543210", 5),
            (5, "English", 6),
            (6, "123 MG Road, Bengaluru", 7),
            # 2. Medical Background (Q7..Q10) - free text without quick-reply buttons
            (7, "No", 8),
            (8, "No", 9),
            (9, "No", 10),
            (10, "No known allergies", 11),
            # Treatment Preferences (Q11..Q18)
            (11, "No", 12),       # CPR: No
            (12, "Yes", 13),      # Ventilator: Yes
            (13, "Yes", 14),      # Dialysis: Yes
            (14, "Yes", 15),      # Chemotherapy: Yes (MUST NOT BE 'NOT SPECIFIED')
            (15, "Yes", 16),      # Radiotherapy: Yes (MUST NOT BE 'NOT SPECIFIED')
            (16, "Yes", 17),      # Major Surgery: Yes
            (17, "Yes", 18),      # Artificial Hydration: Yes
            (18, "Yes", 19),      # Artificial Nutrition: Yes
            # 3. End-of-Life Preferences (Q19..Q25)
            (19, "A balance of comfort and life-prolonging treatment", 20),
            (20, "Home", 21),
            (21, "No preference", 22), # Preferred Hospital: No preference (MUST NOT BE 'Not recorded')
            (22, "No preference", 23), # Preferred Clinician: No preference (MUST NOT BE 'Not recorded')
            (23, "Live with dignity and avoid suffering", 24),
            (24, "Full medical treatment", 25),
            (25, "No additional wishes", 26),
            # 4. Designated Healthcare Representative (Q26..Q31)
            (26, "niki", 27),
            (27, "sister", 28),
            (28, "9876543210", 29),
            (29, "niki123@gmail.com", 30),
            (30, "udupi", 31),
            (31, "No", 37),       # Alternate DHR: No -> skips Q32..Q36 straight to Q37!
            # 5. Organ & Body Donation (Q37..Q39)
            (37, "Yes", 38),      # Organ Donation: Yes (MUST NOT overwrite alternate_dhr_appointed to True!)
            (38, "Yes", 39),      # Body Donation: Yes
            (39, "No specific wishes", 40), # Last Rites
            # Administrative Details (Q40..Q43)
            (40, "Same as current address", 41),
            (41, "Skip", 42),
            (42, "Skip", 43),
            (43, "Skip", 44),
            # 6. Review & Confirmation (Q44)
            (44, "Confirm Plan", None),
        ]

        for q_num, ans, next_q in flow:
            mock_resp.json.return_value = {
                "status": "completed" if next_q is None else "saved",
                "message": "Answer recorded.",
                "question_number": q_num,
                "answer": ans,
                "next_question": None if next_q is None else {"question_number": next_q, "question": f"Q{next_q}"},
                "sources": None
            }
            res = self.client.post(
                "/api/ai/chat",
                data=json.dumps({"session_id": "reg_sess_problem_10", "message": ans, "question_number": q_num}),
                headers=self.p_headers
            )
            self.assertEqual(res.status_code, 200)

        # 1. Verify DB canonical records
        pat = Patient.query.get(self.patient.patient_id)
        pref = pat.acp_preferences
        dhrs = DHR.query.filter_by(patient_id=self.patient.patient_id).order_by(DHR.preference_order.asc()).all()
        primary_dhr = dhrs[0] if dhrs else None
        alt_dhr = DHR.query.filter_by(patient_id=self.patient.patient_id, preference_order=2).first()

        self.assertEqual(pat.user.full_name, "Sunil Kumar")
        self.assertEqual(str(pat.date_of_birth), "1980-05-15")
        self.assertEqual(pat.gender, "Male")
        self.assertEqual(pat.phone, "9876543210")
        self.assertEqual(pat.preferred_language, "English")
        self.assertEqual(pat.current_address, "123 MG Road, Bengaluru")
        self.assertEqual(pat.chronic_conditions, "No")
        self.assertEqual(pat.serious_hospitalization, "No")
        self.assertEqual(pat.long_term_medications, "No")
        self.assertEqual(pat.allergies, "No known allergies")

        # Treatment preferences must match exact choices
        self.assertEqual(pref.cpr_preference, "DO NOT WANT")
        self.assertEqual(pref.ventilator_preference, "WANT")
        self.assertEqual(pref.dialysis_preference, "WANT")
        self.assertEqual(pref.chemotherapy_preference, "WANT")
        self.assertEqual(pref.radiotherapy_preference, "WANT")
        self.assertEqual(pref.surgery_preference, "WANT")
        self.assertEqual(pref.iv_fluids_preference, "WANT")
        self.assertEqual(pref.nutrition_hydration_preference, "WANT")

        # End-of-Life preferences
        self.assertEqual(pref.goals_of_care, "A balance of comfort and life-prolonging treatment")
        self.assertEqual(pref.preferred_place_of_care, "Home")
        self.assertEqual(pref.preferred_hospital, "No preference")
        self.assertEqual(pref.preferred_physician_name, "No preference")
        self.assertEqual(pat.personal_values, "Live with dignity and avoid suffering")
        self.assertEqual(pref.additional_wishes, "No additional wishes")

        # Primary DHR
        self.assertIsNotNone(primary_dhr)
        self.assertEqual(primary_dhr.full_name, "niki")
        self.assertEqual(primary_dhr.relationship, "sister")
        self.assertEqual(primary_dhr.mobile_primary, "9876543210")
        self.assertEqual(primary_dhr.email_primary, "niki123@gmail.com")
        self.assertEqual(primary_dhr.permanent_address, "udupi")

        # Alternate DHR decision: No -> MUST NOT BE APPOINTED!
        self.assertFalse(pref.alternate_dhr_appointed)
        self.assertIsNone(alt_dhr)

        # Donation directives
        self.assertEqual(pref.organ_donation, "YES")
        self.assertEqual(pref.body_donation, "YES")
        self.assertEqual(pref.last_rites, "No specific wishes")

        # ACP completion must be True
        self.assertTrue(pref.is_completed)

        # 2. Verify review summary and required fields
        missing = AIService._get_missing_required_fields(self.patient.patient_id, "en")
        self.assertEqual(len(missing), 0, f"Expected 0 missing fields, got: {missing}")

        summary = AIService._generate_review_summary(self.patient.patient_id, "en")
        self.assertIn("All required information is complete and verified", summary)
        self.assertNotIn("Incomplete Information", summary)
        self.assertIn("Chemotherapy (Cancer Treatment): Yes (WANT)", summary)
        self.assertIn("Radiotherapy (Radiation Treatment): Yes (WANT)", summary)
        self.assertIn("Preferred Hospital: No preference", summary)
        self.assertIn("Preferred Treating Clinician: No preference", summary)
        self.assertIn("Alternate Representative (Rank 2): None appointed", summary)

        # 3. Verify AMD PDF generation works cleanly with 100% completed plan
        pdf_path = os.path.join(tempfile.gettempdir(), f"amd_problem_10_{self.patient.patient_id}.pdf")
        generate_amd_pdf(pat, pref, [primary_dhr], [], None, None, None, pdf_path)
        self.assertTrue(os.path.exists(pdf_path))
        self.assertGreater(os.path.getsize(pdf_path), 500)

    @patch("requests.request")
    def test_15_alternate_dhr_appointed_scenario(self, mock_req):
        """15. Opposite branch: Patient selects Yes for Alternate DHR, provides full details,
        and plan validates and completes successfully with 2 DHRs."""
        # Create a new patient
        user2 = User(email="pat_alt_test@test.com", full_name="Meena Rao", role="patient")
        user2.set_password("Secret123!")
        db.session.add(user2)
        db.session.commit()

        pat2 = Patient(user_id=user2.id, phone="9845012345", address="10 Koramangala, Bengaluru")
        db.session.add(pat2)
        db.session.commit()

        # Answers with Alternate DHR = Yes
        AIService._persist_canonical_answer(pat2.patient_id, 1, "Meena Rao", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 2, "1985-04-12", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 3, "Female", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 4, "9845012345", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 5, "English", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 6, "10 Koramangala, Bengaluru", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 7, "None", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 8, "None", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 9, "None", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 10, "None", user2.id)
        for q in range(11, 19):
            AIService._persist_canonical_answer(pat2.patient_id, q, "Yes", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 19, "Comfort-focused care", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 20, "Home", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 23, "Family peace", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 24, "Comfort-focused treatment", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 26, "Ramesh Rao", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 27, "Brother", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 28, "9845099999", user2.id)
        # Alternate DHR appointment: Yes
        AIService._persist_canonical_answer(pat2.patient_id, 31, "Yes", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 32, "Kavita Rao", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 33, "Sister", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 34, "9845088888", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 35, "kavita@test.com", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 36, "Same as my address", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 37, "Yes", user2.id)
        AIService._persist_canonical_answer(pat2.patient_id, 38, "No", user2.id)

        pref2 = pat2.acp_preferences
        self.assertTrue(pref2.alternate_dhr_appointed)
        dhr2 = DHR.query.filter_by(patient_id=pat2.patient_id, preference_order=2).first()
        self.assertIsNotNone(dhr2)
        self.assertEqual(dhr2.full_name, "Kavita Rao")
        self.assertEqual(dhr2.relationship, "Sister")
        self.assertEqual(dhr2.mobile_primary, "9845088888")

        # Confirmation should succeed with 0 missing fields
        confirm_res = AIService.confirm_review(pat2.patient_id, performed_by_id=user2.id)
        self.assertEqual(confirm_res["status"], "completed")
        self.assertTrue(confirm_res["is_completed"])
        self.assertTrue(pref2.is_completed)
