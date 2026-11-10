"""
Comprehensive test suite for Doctor Portal Dashboard, ACP Reviews, and Analytics Improvements.
Validates all required business scenarios:
1. Patient with 0% completion (status: 'Not Started').
2. Patient with partially completed ACP (status: 'In Progress').
3. Patient with 100% completion but not submitted (status: 'Completed – Not Submitted').
4. Patient with 100% completion and submitted for review (status: 'Pending Review').
5. Patient whose ACP has been acknowledged (status: 'Reviewed').
6. Guard check: Doctor cannot review or acknowledge incomplete or unsubmitted ACP drafts (returns 400).
7. Doctor with no assigned patients.
8. Doctor with no pending reviews.
9. Patient updates ACP information after initial draft (completion percentage recalculates dynamically).
10. Doctor acknowledges an eligible ACP: DB updates, stats refresh, and patient moves out of pending review queue.
"""
import unittest
import json
from datetime import datetime, timedelta
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.doctor_profile import DoctorProfile
from backend.utils.auth_helpers import generate_token
from backend.utils.acp_calculator import calculate_patient_acp_progress, resolve_acp_status
from backend.services.dashboard_service import DashboardService

class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-doctor-portal-secret'

class DoctorPortalImprovementsTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Create doctor account
        self.doctor_user = User(
            full_name="Dr. Rajeev Kumar",
            email="dr.rajeev@hospital.org",
            role="doctor"
        )
        self.doctor_user.set_password("SecureDocPass123!")
        db.session.add(self.doctor_user)
        db.session.commit()

        self.doctor_profile = DoctorProfile(
            user_id=self.doctor_user.id,
            specialization="Palliative Medicine",
            hospital="Metro General Hospital",
            is_active=True
        )
        db.session.add(self.doctor_profile)
        db.session.commit()

        self.doctor_token = generate_token(
            self.doctor_user.id,
            self.doctor_user.email,
            self.doctor_user.role,
            must_change_password=False
        )
        self.doctor_headers = {"Authorization": f"Bearer {self.doctor_token}"}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def test_01_patient_with_0_percent_completion(self):
        """Scenario 1: Patient with 0% completion must show status 'Not Started' and not hardcoded 20%."""
        user = User(full_name="Zero Patient", email="zero@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id)
        db.session.add(pat)
        db.session.commit()

        metrics = calculate_patient_acp_progress(pat)
        self.assertEqual(metrics['completion_percentage'], 0, "Patient with no ACP data must be 0%")
        self.assertFalse(metrics['is_completed'])
        self.assertEqual(metrics['status'], "Not Started", "Unstarted patient must have status 'Not Started'")
        self.assertEqual(metrics['section_progress']['personal'], 0)
        self.assertEqual(metrics['section_progress']['medical'], 0)
        self.assertEqual(metrics['section_progress']['review'], 0)
        self.assertNotIn('priority', metrics, "Priority feature must be removed")

        # Check API response
        res = self.client.get('/api/doctor/patients', headers=self.doctor_headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['completion_percentage'], 0)
        self.assertEqual(data[0]['status'], "Not Started")
        self.assertNotIn('priority', data[0], "Priority must not be returned in API response")

    def test_02_patient_with_partially_completed_acp(self):
        """Scenario 2: Patient with partially completed ACP information shows genuine partial %, not 20%, and status 'In Progress'."""
        user = User(full_name="Partial Patient", email="partial@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(
            user_id=user.id,
            age=45,
            gender="Male",
            phone="9876543210",
            address="123 Park Lane"
        )
        db.session.add(pat)
        db.session.commit()

        # Fill medical treatments partially (4 of 8 answered)
        pref = ACPPreference(
            patient_id=pat.patient_id,
            cpr_preference="WANT",
            ventilator_preference="WANT",
            dialysis_preference="DO NOT WANT",
            chemotherapy_preference="WANT",
            # other 4 NOT SPECIFIED
            goals_of_care="Balance comfort and life",
            preferred_place_of_care="Home",
            organ_donation="YES",
            body_donation="NO",
            is_completed=False,
            completed_at=None,
            review_status="Pending Review"
        )
        db.session.add(pref)
        db.session.commit()

        metrics = calculate_patient_acp_progress(pat)
        self.assertGreater(metrics['completion_percentage'], 0)
        self.assertLess(metrics['completion_percentage'], 100)
        self.assertNotEqual(metrics['completion_percentage'], 20, "Should not hardcode 20%")
        self.assertFalse(metrics['is_completed'])
        self.assertEqual(metrics['status'], "In Progress", "Incomplete draft must be 'In Progress', NOT 'Pending Review'")
        self.assertEqual(metrics['section_progress']['personal'], 100)
        self.assertEqual(metrics['section_progress']['medical'], 50)  # 4/8 = 50%
        self.assertEqual(metrics['section_progress']['donation'], 100)
        self.assertNotIn('priority', metrics, "Priority feature must be removed")

    def test_03_patient_with_100_percent_not_submitted(self):
        """Scenario 3: Patient with 100% completion but not submitted shows 'Completed – Not Submitted'."""
        user = User(full_name="Unsubmitted Patient", email="unsubmitted@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id, age=50, phone="9988776655", address="45 Green Rd", gender="Female")
        db.session.add(pat)
        db.session.commit()

        pref = ACPPreference(
            patient_id=pat.patient_id,
            cpr_preference="DO NOT WANT",
            ventilator_preference="DO NOT WANT",
            dialysis_preference="DO NOT WANT",
            chemotherapy_preference="DO NOT WANT",
            radiotherapy_preference="DO NOT WANT",
            surgery_preference="DO NOT WANT",
            iv_fluids_preference="WANT",
            nutrition_hydration_preference="WANT",
            goals_of_care="Comfort care only",
            preferred_place_of_care="Home",
            special_focus_priority="Pain relief",
            pain_management="Full pain relief medications",
            organ_donation="YES",
            body_donation="YES",
            is_completed=False,    # NOT SUBMITTED
            completed_at=None,     # NO SUBMISSION TIMESTAMP
            review_status="Pending Review"
        )
        db.session.add(pref)

        dhr = DHR(
            patient_id=pat.patient_id,
            full_name="Jane Doe",
            relationship="Daughter",
            mobile_primary="9876543210",
            preference_order=1
        )
        db.session.add(dhr)
        db.session.commit()

        metrics = calculate_patient_acp_progress(pat)
        self.assertEqual(metrics['completion_percentage'], 100)
        self.assertFalse(metrics['is_completed'])
        self.assertEqual(metrics['status'], "Completed – Not Submitted", "100% without submission must be 'Completed – Not Submitted'")

        # In doctor patients list
        res = self.client.get('/api/doctor/patients', headers=self.doctor_headers)
        data = json.loads(res.data)
        self.assertEqual(data[0]['status'], "Completed – Not Submitted")

        # Doctor cannot acknowledge an unsubmitted ACP even if sections are 100% complete
        review_res = self.client.put(
            f'/api/doctor/review/{pat.patient_id}',
            headers=self.doctor_headers,
            json={'review_status': 'Reviewed'}
        )
        self.assertEqual(review_res.status_code, 400, "Unsubmitted ACP cannot be reviewed/acknowledged")

    def test_04_patient_with_100_percent_and_submitted_for_review(self):
        """Scenario 4: Patient with 100% completion and submitted for review shows 'Pending Review'."""
        user = User(full_name="Submitted Patient", email="submitted@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id, age=60, phone="9123456780", address="10 High St", gender="Female")
        db.session.add(pat)
        db.session.commit()

        pref = ACPPreference(
            patient_id=pat.patient_id,
            cpr_preference="WANT",
            ventilator_preference="WANT",
            dialysis_preference="WANT",
            chemotherapy_preference="WANT",
            radiotherapy_preference="WANT",
            surgery_preference="WANT",
            iv_fluids_preference="WANT",
            nutrition_hydration_preference="WANT",
            goals_of_care="Prolong life",
            preferred_place_of_care="Hospital",
            special_focus_priority="Full treatment",
            organ_donation="YES",
            body_donation="NO",
            is_completed=True,
            completed_at=datetime.utcnow(),
            review_status="Pending Review"
        )
        db.session.add(pref)
        db.session.commit()

        metrics = calculate_patient_acp_progress(pat)
        self.assertEqual(metrics['completion_percentage'], 100)
        self.assertTrue(metrics['is_completed'])
        self.assertEqual(metrics['status'], "Pending Review", "Submitted ACP awaiting review must be 'Pending Review'")

        # Verify through analytics
        analytics = DashboardService.get_doctor_dashboard_analytics()
        self.assertEqual(analytics['summary']['completed_acps'], 1)
        self.assertEqual(analytics['summary']['in_progress_acps'], 0)
        self.assertEqual(analytics['summary']['pending_reviews'], 1)
        self.assertEqual(analytics['status_counts']['Pending Review'], 1)
        self.assertNotIn('priority_dist', analytics, "Priority distribution must be removed")

    def test_05_patient_whose_acp_has_been_acknowledged(self):
        """Scenario 5: Patient whose ACP has been acknowledged shows 'Reviewed' status."""
        user = User(full_name="Reviewed Patient", email="reviewed@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id, age=55, phone="9988112233", address="88 Elm St", gender="Male")
        db.session.add(pat)
        db.session.commit()

        pref = ACPPreference(
            patient_id=pat.patient_id,
            is_completed=True,
            completed_at=datetime.utcnow(),
            review_status="Reviewed",
            reviewed_by_doctor=self.doctor_user.id
        )
        db.session.add(pref)
        db.session.commit()

        metrics = calculate_patient_acp_progress(pat)
        self.assertEqual(metrics['completion_percentage'], 100)
        self.assertEqual(metrics['review_status'], "Reviewed")
        self.assertEqual(metrics['status'], "Reviewed", "Acknowledged ACP must have status 'Reviewed'")

        analytics = DashboardService.get_doctor_dashboard_analytics()
        self.assertEqual(analytics['summary']['reviewed_acps'], 1)
        self.assertEqual(analytics['summary']['pending_reviews'], 0)
        self.assertEqual(analytics['status_counts']['Reviewed'], 1)

    def test_06_unsubmitted_acp_cannot_be_reviewed(self):
        """Requirement: Do not allow doctors to acknowledge incomplete or unsubmitted ACPs."""
        user = User(full_name="Draft Patient", email="draft@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id, age=40)
        db.session.add(pat)
        db.session.commit()

        pref = ACPPreference(
            patient_id=pat.patient_id,
            cpr_preference="WANT",
            is_completed=False,  # Still in draft
            completed_at=None,
            review_status="Pending Review"
        )
        db.session.add(pref)
        db.session.commit()

        # Doctor attempts to mark unsubmitted draft as Reviewed
        res = self.client.put(
            f'/api/doctor/review/{pat.patient_id}',
            headers=self.doctor_headers,
            json={'review_status': 'Reviewed'}
        )
        self.assertEqual(res.status_code, 400, "Must reject review of unsubmitted ACP with 400 Bad Request")
        data = json.loads(res.data)
        self.assertIn("Cannot review or acknowledge an unsubmitted or incomplete Advance Care Plan", data['message'])

    def test_07_doctor_with_no_assigned_patients(self):
        """Scenario 7: Doctor with no assigned patients returns 0 counts and empty arrays safely."""
        analytics = DashboardService.get_doctor_dashboard_analytics()
        self.assertEqual(analytics['summary']['total_patients'], 0)
        self.assertEqual(analytics['summary']['completed_acps'], 0)
        self.assertEqual(analytics['summary']['pending_reviews'], 0)
        self.assertEqual(analytics['summary']['reviewed_acps'], 0)
        self.assertEqual(len(analytics['recent_activities']), 0)

        res = self.client.get('/api/doctor/patients', headers=self.doctor_headers)
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(len(data), 0)

    def test_08_doctor_with_no_pending_reviews(self):
        """Scenario 8: Doctor with only reviewed and incomplete patients has 0 pending reviews."""
        user = User(full_name="Patient One", email="p1@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id)
        db.session.add(pat)
        db.session.commit()

        pref = ACPPreference(
            patient_id=pat.patient_id,
            is_completed=True,
            completed_at=datetime.utcnow(),
            review_status="Reviewed",
            reviewed_by_doctor=self.doctor_user.id
        )
        db.session.add(pref)
        db.session.commit()

        analytics = DashboardService.get_doctor_dashboard_analytics()
        self.assertEqual(analytics['summary']['pending_reviews'], 0)
        self.assertEqual(analytics['summary']['reviewed_acps'], 1)

    def test_09_patient_updates_acp_information_after_initial_submission(self):
        """Scenario 9: Patient updates ACP information after initial draft; timestamp and metrics update."""
        user = User(full_name="Updating Patient", email="upd@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id, phone="9111222333")
        db.session.add(pat)
        db.session.commit()

        initial_time = datetime.utcnow() - timedelta(hours=2)
        pref = ACPPreference(
            patient_id=pat.patient_id,
            cpr_preference="WANT",
            ventilator_preference="WANT",
            is_completed=False,
            updated_at=initial_time
        )
        db.session.add(pref)
        db.session.commit()

        initial_metrics = calculate_patient_acp_progress(pat)

        # Patient now answers organ and body donation
        pref.organ_donation = "YES"
        pref.body_donation = "YES"
        pref.updated_at = datetime.utcnow()
        db.session.commit()

        updated_metrics = calculate_patient_acp_progress(pat)
        self.assertGreater(updated_metrics['completion_percentage'], initial_metrics['completion_percentage'])
        self.assertGreater(updated_metrics['section_progress']['donation'], initial_metrics['section_progress']['donation'])

    def test_10_doctor_reviews_acp_and_statistics_update_correctly(self):
        """Scenario 10: Doctor reviews an eligible ACP and statistics update correctly in DB and API without duplicates."""
        user = User(full_name="Pending Submission Patient", email="sub@example.com", role="patient")
        user.set_password("Pass123!")
        db.session.add(user)
        db.session.commit()

        pat = Patient(user_id=user.id, age=50, phone="9888777666", address="Main Road")
        db.session.add(pat)
        db.session.commit()

        pref = ACPPreference(
            patient_id=pat.patient_id,
            cpr_preference="WANT",
            ventilator_preference="WANT",
            dialysis_preference="WANT",
            chemotherapy_preference="WANT",
            radiotherapy_preference="WANT",
            surgery_preference="WANT",
            iv_fluids_preference="WANT",
            nutrition_hydration_preference="WANT",
            is_completed=True,
            completed_at=datetime.utcnow(),
            review_status="Pending Review"
        )
        db.session.add(pref)
        db.session.commit()

        # Before review: pending_reviews == 1, reviewed_acps == 0
        analytics_before = DashboardService.get_doctor_dashboard_analytics()
        self.assertEqual(analytics_before['summary']['pending_reviews'], 1)
        self.assertEqual(analytics_before['summary']['reviewed_acps'], 0)

        # Doctor performs review via API
        review_res = self.client.put(
            f'/api/doctor/review/{pat.patient_id}',
            headers=self.doctor_headers,
            json={'review_status': 'Reviewed'}
        )
        self.assertEqual(review_res.status_code, 200)

        # Verify DB update
        updated_pref = db.session.get(ACPPreference, pat.patient_id)
        self.assertEqual(updated_pref.review_status, "Reviewed")
        self.assertEqual(updated_pref.reviewed_by_doctor, self.doctor_user.id)

        # After review: pending_reviews == 0, reviewed_acps == 1, completed_acps == 1
        analytics_after = DashboardService.get_doctor_dashboard_analytics()
        self.assertEqual(analytics_after['summary']['pending_reviews'], 0)
        self.assertEqual(analytics_after['summary']['reviewed_acps'], 1)
        self.assertEqual(analytics_after['summary']['completed_acps'], 1)
        self.assertEqual(analytics_after['status_counts']['Reviewed'], 1)
        self.assertEqual(analytics_after['status_counts']['Pending Review'], 0)

if __name__ == '__main__':
    unittest.main()
