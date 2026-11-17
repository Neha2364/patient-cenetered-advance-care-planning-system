import os
import unittest
import tempfile
from datetime import date
from pypdf import PdfReader
from backend.utils.pdf_generator import generate_amd_pdf, evaluate_treatment_preference, safe_display

class MockUser:
    def __init__(self, full_name="Rahul Sharma"):
        self.full_name = full_name

class MockPatient:
    def __init__(self, **kwargs):
        self.user = kwargs.get('user', MockUser())
        self.patient_id = kwargs.get('patient_id', 101)
        self.gender = kwargs.get('gender', 'Male')
        self.date_of_birth = kwargs.get('date_of_birth', date(1975, 5, 20))
        self.age = kwargs.get('age', 50)
        self.phone = kwargs.get('phone', '+919876543210')
        self.address = kwargs.get('address', '123 MG Road, Bengaluru, Karnataka')
        self.permanent_address = kwargs.get('permanent_address', '123 MG Road, Bengaluru, Karnataka')
        self.current_address = kwargs.get('current_address', '456 Indiranagar, Bengaluru, Karnataka')
        self.government_id_type = kwargs.get('government_id_type', 'Aadhaar')
        self.government_id_number = kwargs.get('government_id_number', '9876-5432-1098')
        self.municipality_panchayat = kwargs.get('municipality_panchayat', 'BBMP Bengaluru')
        self.beliefs_values = kwargs.get('beliefs_values', 'I value mental clarity and time with my family above prolonging pain.')
        self.personal_values = kwargs.get('personal_values')
        self.chronic_conditions = kwargs.get('chronic_conditions')
        self.serious_hospitalization = kwargs.get('serious_hospitalization')
        self.long_term_medications = kwargs.get('long_term_medications')
        self.allergies = kwargs.get('allergies')

class MockPreferences:
    def __init__(self, **kwargs):
        self.cpr_preference = kwargs.get('cpr_preference', 'DO NOT WANT')
        self.ventilator_preference = kwargs.get('ventilator_preference', 'DO NOT WANT')
        self.dialysis_preference = kwargs.get('dialysis_preference', 'DO NOT WANT')
        self.chemotherapy_preference = kwargs.get('chemotherapy_preference', 'DO NOT WANT')
        self.radiotherapy_preference = kwargs.get('radiotherapy_preference', 'DO NOT WANT')
        self.surgery_preference = kwargs.get('surgery_preference', 'DO NOT WANT')
        self.iv_fluids_preference = kwargs.get('iv_fluids_preference', 'DO NOT WANT')
        self.nutrition_hydration_preference = kwargs.get('nutrition_hydration_preference', 'DO NOT WANT')
        
        self.pain_management = kwargs.get('pain_management', 'Administer maximum palliative analgesia.')
        self.goals_of_care = kwargs.get('goals_of_care')
        self.preferred_place_of_care = kwargs.get('preferred_place_of_care', 'Home')
        self.preferred_hospital = kwargs.get('preferred_hospital', 'Manipal Hospital')
        self.preferred_physician_name = kwargs.get('preferred_physician_name', 'Dr. Ramesh Rao')
        self.preferred_physician_designation = kwargs.get('preferred_physician_designation', 'Chief of Palliative Medicine')
        self.preferred_physician_institution = kwargs.get('preferred_physician_institution', 'Manipal Hospital')
        self.special_focus_priority = kwargs.get('special_focus_priority', 'Spiritual peace and pain relief.')
        self.gender_identity_instructions = kwargs.get('gender_identity_instructions', 'Address with male pronouns (He/Him).')
        self.relationship_instructions = kwargs.get('relationship_instructions', 'Spouse is primary next-of-kin.')
        self.organ_donation = kwargs.get('organ_donation', 'YES')
        self.body_donation = kwargs.get('body_donation', 'NO')
        self.last_rites = kwargs.get('last_rites', 'Traditional Hindu rites, cremation.')
        self.forward_to_dhrs = kwargs.get('forward_to_dhrs', True)
        self.forward_to_physician = kwargs.get('forward_to_physician', True)
        self.forward_to_custodian = kwargs.get('forward_to_custodian', True)
        self.additional_wishes = kwargs.get('additional_wishes', 'Play soft instrumental music.')

class MockDHR:
    def __init__(self, **kwargs):
        self.full_name = kwargs.get('full_name', 'Priya Sharma')
        self.relationship = kwargs.get('relationship', 'Spouse')
        self.date_of_birth = kwargs.get('date_of_birth', date(1978, 8, 15))
        self.government_id_type = kwargs.get('government_id_type', 'Passport')
        self.government_id_number = kwargs.get('government_id_number', 'K1234567')
        self.mobile_primary = kwargs.get('mobile_primary', '+919876543211')
        self.mobile_secondary = kwargs.get('mobile_secondary', '+919876543212')
        self.email_primary = kwargs.get('email_primary', 'priya@example.com')
        self.email_secondary = kwargs.get('email_secondary', 'priya.work@example.com')
        self.permanent_address = kwargs.get('permanent_address', '123 MG Road, Bengaluru')
        self.signing_address = kwargs.get('signing_address', '123 MG Road, Bengaluru')
        self.preference_order = kwargs.get('preference_order', 1)


class TestAMDPDFGeneration(unittest.TestCase):
    """Rigorous tests auditing mapping, 6 ACP sections, alternate DHR, and formatting."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.sample_witnesses = [
            {
                "name": "Dr. Ananya Sen",
                "email": "ananya@hospital.org",
                "mobile": "+919876543299",
                "address": "45 Medical Enclave, Bengaluru",
                "government_id": "Aadhaar 1111-2222-3333"
            },
            {
                "name": "Vikram Patel",
                "email": "vikram@advocates.in",
                "mobile": "+919876543298",
                "address": "88 High Court Road, Bengaluru",
                "government_id": "Voter ID VTR998877"
            }
        ]

    def test_preference_evaluation_helper(self):
        """Audit preference evaluator for WANT, DO NOT WANT, UNSURE, and unrecorded."""
        # 1. CPR WANT
        expl, badge = evaluate_treatment_preference('WANT', 'cpr')
        self.assertIn("PROVIDE / CONTINUE", badge)
        self.assertIn("Desires cardiopulmonary resuscitation", expl)
        self.assertNotIn("withheld", expl)

        # 2. CPR DO NOT WANT
        expl, badge = evaluate_treatment_preference('DO NOT WANT', 'cpr')
        self.assertIn("WITHHOLD / WITHDRAW", badge)
        self.assertIn("withheld or withdrawn", expl)
        self.assertNotIn("Desires cardiopulmonary", expl)

        # 3. CPR UNSURE
        expl, badge = evaluate_treatment_preference('UNSURE', 'cpr')
        self.assertIn("UNSURE / UNDECIDED", badge)
        self.assertIn("Uncertain / Undecided", expl)

        # 4. CPR NOT SPECIFIED / None
        expl, badge = evaluate_treatment_preference(None, 'cpr')
        self.assertIn("NOT SPECIFIED", badge)
        self.assertIn("not specified", expl.lower())

    def test_all_eight_preferences_and_relevant_background_are_in_amd(self):
        output_pdf = os.path.join(self.temp_dir, "all_eight_and_background.pdf")
        patient = MockPatient(
            personal_values="Comfort and family time",
            chronic_conditions="Diabetes",
            serious_hospitalization="Previous stroke admission",
            long_term_medications="Metformin",
            allergies="Penicillin"
        )
        pref = MockPreferences(
            cpr_preference="UNSURE", ventilator_preference="WANT", dialysis_preference="DO NOT WANT",
            nutrition_hydration_preference="WANT", iv_fluids_preference="UNSURE",
            chemotherapy_preference="DO NOT WANT", radiotherapy_preference="WANT", surgery_preference="UNSURE",
            goals_of_care="Balance comfort with appropriate treatment"
        )
        generate_amd_pdf(patient, pref, [MockDHR()], self.sample_witnesses, None, None, None, output_pdf)
        reader = PdfReader(output_pdf)
        all_text = " ".join(page.extract_text() for page in reader.pages)
        treatment_text = reader.pages[1].extract_text()
        for label in ("CPR", "Mechanical Ventilation", "Dialysis", "Chemotherapy", "Radiotherapy", "Invasive Surgery", "Artificial Hydration", "Artificial Nutrition"):
            self.assertIn(label, treatment_text)
        self.assertIn("UNSURE / UNDECIDED", treatment_text)
        self.assertIn("Balance comfort with appropriate treatment", all_text)
        for value in ("Comfort and family time", "Diabetes", "Previous stroke admission", "Metformin", "Penicillin"):
            self.assertIn(value, all_text)

    def test_case_cpr_want_pdf(self):
        """Case 1: Patient selects WANT for CPR and Ventilator -> PDF must show PROVIDE / CONTINUE without contradiction."""
        output_pdf = os.path.join(self.temp_dir, "test_cpr_want.pdf")
        patient = MockPatient()
        pref = MockPreferences(
            cpr_preference="WANT",
            ventilator_preference="WANT",
            dialysis_preference="DO NOT WANT"
        )
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        self.assertTrue(os.path.exists(output_pdf))
        reader = PdfReader(output_pdf)
        self.assertEqual(len(reader.pages), 5)

        # Read page 2 text (Treatment Preferences)
        page2_text = reader.pages[1].extract_text()
        self.assertIn("PROVIDE / CONTINUE", page2_text)
        self.assertIn("Desires cardiopulmonary resuscitation", page2_text)
        # CRITICAL: Verify NO contradiction where WANT is accompanied by "DO NOT WANT CPR"
        self.assertNotIn("DO NOT WANT CPR if heartbeat stops", page2_text)

    def test_case_cpr_do_not_want_pdf(self):
        """Case 2: Patient selects DO NOT WANT for all interventions -> PDF accurately reflects WITHHOLD / WITHDRAW."""
        output_pdf = os.path.join(self.temp_dir, "test_cpr_do_not_want.pdf")
        patient = MockPatient()
        pref = MockPreferences(cpr_preference="DO NOT WANT", ventilator_preference="DO NOT WANT")
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        page2_text = reader.pages[1].extract_text()
        self.assertIn("WITHHOLD / WITHDRAW", page2_text)
        self.assertIn("withheld or withdrawn; permit natural death", page2_text)

    def test_case_unsure_preference_pdf(self):
        """Case 3: Patient selects UNSURE for CPR -> PDF accurately reflects UNSURE / UNDECIDED."""
        output_pdf = os.path.join(self.temp_dir, "test_cpr_unsure.pdf")
        patient = MockPatient()
        pref = MockPreferences(cpr_preference="UNSURE", ventilator_preference="DO NOT WANT")
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        page2_text = reader.pages[1].extract_text()
        self.assertIn("UNSURE / UNDECIDED", page2_text)
        self.assertIn("Uncertain / Undecided", page2_text)

    def test_case_missing_and_unanswered_preferences(self):
        """Case 4: Patient has missing/unanswered preferences -> PDF handles cleanly with NOT SPECIFIED, no 'N/A' cascades."""
        output_pdf = os.path.join(self.temp_dir, "test_missing_prefs.pdf")
        patient = MockPatient(
            gender=None,
            date_of_birth=None,
            government_id_type=None,
            government_id_number=None,
            permanent_address=None,
            current_address=None,
            municipality_panchayat=None,
            beliefs_values=None
        )
        pref = MockPreferences(
            cpr_preference="NOT SPECIFIED",
            ventilator_preference=None,
            dialysis_preference="",
            pain_management=None,
            preferred_place_of_care=None,
            preferred_hospital=None,
            preferred_physician_name=None,
            special_focus_priority=None,
            gender_identity_instructions=None,
            relationship_instructions=None,
            organ_donation="NOT SPECIFIED",
            body_donation="NOT SPECIFIED",
            last_rites=None
        )
        dhrs = [MockDHR(
            government_id_type=None,
            government_id_number=None,
            mobile_secondary=None,
            email_secondary=None
        )]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name=None,
            notary_place=None,
            executor_place=None,
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        full_text = " ".join([page.extract_text() for page in reader.pages])

        # Verify NOT SPECIFIED appears
        self.assertIn("NOT SPECIFIED", full_text)
        # Verify repeated 'N/A' is not present
        self.assertNotIn("N/A", full_text)

    def test_alternate_dhr_presence_and_absence(self):
        """Case 5: Check Alternate DHR rendering when present vs absent."""
        # 5A: Absent Alternate DHR
        out_absent = os.path.join(self.temp_dir, "test_alt_absent.pdf")
        patient = MockPatient()
        pref = MockPreferences()
        dhrs_only_primary = [MockDHR(preference_order=1, full_name="Priya Sharma")]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs_only_primary,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=out_absent
        )

        reader_a = PdfReader(out_absent)
        page4_text_a = reader_a.pages[3].extract_text()
        self.assertIn("No secondary or alternate designated healthcare representative has been appointed", page4_text_a)
        self.assertNotIn("Alternate DHR #1", page4_text_a)

        # 5B: Present Alternate DHR
        out_present = os.path.join(self.temp_dir, "test_alt_present.pdf")
        alt_dhr = MockDHR(
            preference_order=2,
            full_name="Kavita Sharma",
            relationship="Sister",
            mobile_primary="+919876543222",
            email_primary="kavita@example.com"
        )
        dhrs_with_alt = [dhrs_only_primary[0], alt_dhr]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs_with_alt,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=out_present
        )

        reader_b = PdfReader(out_present)
        page4_text_b = reader_b.pages[3].extract_text()
        self.assertIn("Alternate DHR #1", page4_text_b)
        self.assertIn("Kavita Sharma", page4_text_b)
        self.assertIn("Sister", page4_text_b)

    def test_vidhi_legal_provisions_and_signatures(self):
        """Case 6: Verify Hon'ble Supreme Court order reference, validity, revocation, and notarisation."""
        output_pdf = os.path.join(self.temp_dir, "test_legal_provisions.pdf")
        patient = MockPatient()
        pref = MockPreferences()
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. Suresh Babu",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        self.assertEqual(len(reader.pages), 5)

        # Page 4: Legal declarations & Supreme Court reference
        page4_text = " ".join(reader.pages[3].extract_text().split())
        self.assertIn("MA No. 1699/ 2019 in WP (C) No. 215/ 2005", page4_text)
        self.assertIn("Validity, Modification & Revocation", page4_text)
        self.assertIn("Vidhi Centre for Legal Policy", page4_text)

        # Page 5: Signatures and Notarisation
        page5_text = " ".join(reader.pages[4].extract_text().split())
        self.assertIn("Execution, Witness Attestations & Notarisation", page5_text)
        self.assertIn("Signature of the Executor", page5_text)
        self.assertIn("Rahul Sharma", page5_text)
        self.assertIn("Dr. Ananya Sen", page5_text)
        self.assertIn("Vikram Patel", page5_text)
        self.assertIn("SIGNED BEFORE ME", page5_text)
        self.assertIn("Adv. Suresh Babu", page5_text)
        self.assertIn("OFFICIAL NOTARIAL STAMP & SEAL", page5_text)

    def test_case_all_three_want_treatment(self):
        """Scenario 1: All three preferences (Chemotherapy, Radiotherapy, Surgery) set to WANT -> PDF reflects PROVIDE / CONTINUE."""
        output_pdf = os.path.join(self.temp_dir, "test_three_want.pdf")
        patient = MockPatient()
        pref = MockPreferences(
            chemotherapy_preference="WANT",
            radiotherapy_preference="WANT",
            surgery_preference="WANT"
        )
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        page2_text = " ".join(reader.pages[1].extract_text().split())
        self.assertIn("Chemotherapy (Cancer Therapy)", page2_text)
        self.assertIn("Desires chemotherapy to be administered if recommended by treating oncologist", page2_text)
        self.assertIn("Radiotherapy (Radiation Therapy)", page2_text)
        self.assertIn("Desires radiation therapy to be administered if recommended by treating clinical team", page2_text)
        self.assertIn("Invasive Surgery (Major Operations)", page2_text)
        self.assertIn("Desires surgical intervention if deemed necessary by treating surgical team", page2_text)
        self.assertEqual(page2_text.count("PROVIDE / CONTINUE"), 3)

    def test_case_all_three_do_not_want_treatment(self):
        """Scenario 2: All three preferences set to DO NOT WANT -> PDF reflects WITHHOLD / WITHDRAW."""
        output_pdf = os.path.join(self.temp_dir, "test_three_do_not_want.pdf")
        patient = MockPatient()
        pref = MockPreferences(
            cpr_preference="WANT",  # Keep CPR want to isolate the 3 treatments
            chemotherapy_preference="DO NOT WANT",
            radiotherapy_preference="DO NOT WANT",
            surgery_preference="DO NOT WANT"
        )
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        page2_text = " ".join(reader.pages[1].extract_text().split())
        self.assertIn("Directs withholding or cessation of chemotherapy aimed solely at prolonging active dying", page2_text)
        self.assertIn("Directs withholding of radiation therapy, unless required for palliative symptom control", page2_text)
        self.assertIn("Directs withholding of invasive surgeries, unless strictly for comfort or pain alleviation", page2_text)

    def test_case_mixture_yes_no_unsure(self):
        """Scenario 3: Mixture of Yes (WANT), No (DO NOT WANT), and Unsure (UNSURE)."""
        output_pdf = os.path.join(self.temp_dir, "test_three_mixture.pdf")
        patient = MockPatient()
        pref = MockPreferences(
            chemotherapy_preference="WANT",
            radiotherapy_preference="DO NOT WANT",
            surgery_preference="UNSURE"
        )
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        page2_text = " ".join(reader.pages[1].extract_text().split())
        # Chemotherapy: PROVIDE / CONTINUE
        self.assertIn("Desires chemotherapy to be administered if recommended by treating oncologist", page2_text)
        # Radiotherapy: WITHHOLD / WITHDRAW
        self.assertIn("Directs withholding of radiation therapy, unless required for palliative symptom control", page2_text)
        # Surgery: UNSURE / UNDECIDED
        self.assertIn("Uncertain / Undecided; to be determined by DHR in consultation with treating medical team", page2_text)
        self.assertIn("UNSURE / UNDECIDED", page2_text)

    def test_case_one_or_more_unanswered(self):
        """Scenario 4: One or more preferences unanswered (NOT SPECIFIED) -> accurately reflects NOT SPECIFIED."""
        output_pdf = os.path.join(self.temp_dir, "test_three_unanswered.pdf")
        patient = MockPatient()
        pref = MockPreferences(
            chemotherapy_preference="WANT",
            radiotherapy_preference="NOT SPECIFIED",
            surgery_preference=None
        )
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        reader = PdfReader(output_pdf)
        page2_text = " ".join(reader.pages[1].extract_text().split())
        self.assertIn("Desires chemotherapy to be administered", page2_text)
        self.assertIn("NOT SPECIFIED", page2_text)
        self.assertIn("Preference not specified by patient in advance care record", page2_text)

    def test_case_existing_patient_preserved_answers(self):
        """Scenario 5: Existing patient with prior answers -> preferences must remain unchanged during AMD generation."""
        output_pdf = os.path.join(self.temp_dir, "test_preserved_patient.pdf")
        patient = MockPatient(patient_id=777)
        pref = MockPreferences(
            cpr_preference="DO NOT WANT",
            ventilator_preference="DO NOT WANT",
            dialysis_preference="DO NOT WANT",
            chemotherapy_preference="DO NOT WANT",
            radiotherapy_preference="WANT",
            surgery_preference="UNSURE",
            iv_fluids_preference="WANT",
            nutrition_hydration_preference="DO NOT WANT"
        )
        dhrs = [MockDHR(preference_order=1)]

        generate_amd_pdf(
            patient=patient,
            preferences=pref,
            dhrs=dhrs,
            witnesses=self.sample_witnesses,
            notary_name="Adv. K. Swamy",
            notary_place="Bengaluru",
            executor_place="Bengaluru",
            output_path=output_pdf
        )

        # Verify that original patient preferences are completely untouched
        self.assertEqual(pref.chemotherapy_preference, "DO NOT WANT")
        self.assertEqual(pref.radiotherapy_preference, "WANT")
        self.assertEqual(pref.surgery_preference, "UNSURE")
        self.assertEqual(pref.iv_fluids_preference, "WANT")
        self.assertEqual(pref.nutrition_hydration_preference, "DO NOT WANT")

        reader = PdfReader(output_pdf)
        page2_text = " ".join(reader.pages[1].extract_text().split())
        self.assertIn("Directs withholding or cessation of chemotherapy", page2_text)
        self.assertIn("Desires radiation therapy to be administered", page2_text)
        self.assertIn("Uncertain / Undecided; to be determined by DHR in consultation with treating medical team", page2_text)


if __name__ == '__main__':
    unittest.main()
