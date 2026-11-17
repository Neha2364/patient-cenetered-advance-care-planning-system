"""
Admin Portal Security & Functionality Test Suite

Tests:
 1.  Admin can log in
 2.  Patient cannot log in to Admin Portal
 3.  Doctor cannot log in to Admin Portal (separate from admin login guard)
 4.  Unauthenticated users cannot access Admin APIs (401)
 5.  Admin can create a doctor account
 6.  Patient cannot create a doctor account (403)
 7.  Doctor cannot create another doctor account (403)
 8.  Duplicate doctor email is rejected (409)
 9.  Admin can view the doctor list
10.  Admin can deactivate a doctor
11.  Deactivated doctor cannot log in
12.  Admin can reactivate a doctor
13.  Existing patient login still works
14.  Existing doctor login still works
15.  Patient registration still automatically assigns patient role
16.  Users cannot change their own role via profile update

Uses SQLite in-memory DB — no live database required.
"""

import unittest
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor_profile import DoctorProfile
from backend.utils.auth_helpers import generate_token


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-admin-secret'


class AdminPortalTestCase(unittest.TestCase):
    """Comprehensive tests for the Admin Portal and doctor management."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed: patient
        self.patient_user = User(full_name='Test Patient', email='patient@test.com', role='patient')
        self.patient_user.set_password('pass123')

        # Seed: doctor (active)
        self.doctor_user = User(full_name='Dr. Active', email='doctor@test.com', role='doctor')
        self.doctor_user.set_password('pass123')

        # Seed: admin
        self.admin_user = User(full_name='Admin User', email='admin@test.com', role='admin')
        self.admin_user.set_password('adminpass123')

        db.session.add_all([self.patient_user, self.doctor_user, self.admin_user])
        db.session.commit()

        # Doctor profile (active)
        self.doctor_profile = DoctorProfile(
            user_id=self.doctor_user.id,
            specialization='General Medicine',
            hospital='City Hospital',
            is_active=True,
        )
        # Patient profile
        self.patient_profile = Patient(
            user_id=self.patient_user.id,
            preferred_language='English',
        )
        db.session.add_all([self.doctor_profile, self.patient_profile])
        db.session.commit()

        # Tokens
        self.admin_token = generate_token(self.admin_user.id, self.admin_user.email, self.admin_user.role)
        self.doctor_token = generate_token(self.doctor_user.id, self.doctor_user.email, self.doctor_user.role)
        self.patient_token = generate_token(self.patient_user.id, self.patient_user.email, self.patient_user.role)

        self.admin_headers = {'Authorization': f'Bearer {self.admin_token}', 'Content-Type': 'application/json'}
        self.doctor_headers = {'Authorization': f'Bearer {self.doctor_token}', 'Content-Type': 'application/json'}
        self.patient_headers = {'Authorization': f'Bearer {self.patient_token}', 'Content-Type': 'application/json'}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self, email, password):
        return self.client.post('/api/auth/login', json={'email': email, 'password': password})

    def _create_doctor(self, headers, payload=None):
        payload = payload or {
            'full_name': 'Dr. New Doctor',
            'email': 'newdoctor@test.com',
            'specialization': 'Cardiology',
        }
        return self.client.post('/api/admin/doctors', json=payload, headers=headers)

    # ============================================================
    # Test 1 — Admin can log in
    # ============================================================
    def test_01_admin_can_login(self):
        resp = self._login('admin@test.com', 'adminpass123')
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data['role'], 'admin')
        self.assertIn('token', data)

    # ============================================================
    # Test 2 — Patient cannot access Admin APIs (403)
    # ============================================================
    def test_02_patient_cannot_access_admin_dashboard(self):
        resp = self.client.get('/api/admin/dashboard', headers=self.patient_headers)
        self.assertEqual(resp.status_code, 403, resp.data)

    # ============================================================
    # Test 3 — Doctor cannot access Admin APIs (403)
    # ============================================================
    def test_03_doctor_cannot_access_admin_dashboard(self):
        resp = self.client.get('/api/admin/dashboard', headers=self.doctor_headers)
        self.assertEqual(resp.status_code, 403, resp.data)

    # ============================================================
    # Test 4 — Unauthenticated request → 401
    # ============================================================
    def test_04_unauthenticated_cannot_access_admin_apis(self):
        resp = self.client.get('/api/admin/dashboard')
        self.assertEqual(resp.status_code, 401, resp.data)

    # ============================================================
    # Test 5 — Admin can create a doctor account
    # ============================================================
    def test_05_admin_can_create_doctor(self):
        resp = self._create_doctor(self.admin_headers)
        self.assertEqual(resp.status_code, 201, resp.data)
        data = resp.get_json()
        self.assertEqual(data['email'], 'newdoctor@test.com')
        self.assertIn('temporary_password', data)
        self.assertGreater(len(data['temporary_password']), 8)

    # ============================================================
    # Test 6 — Patient cannot create a doctor account (403)
    # ============================================================
    def test_06_patient_cannot_create_doctor(self):
        resp = self._create_doctor(self.patient_headers)
        self.assertEqual(resp.status_code, 403, resp.data)

    # ============================================================
    # Test 7 — Doctor cannot create another doctor account (403)
    # ============================================================
    def test_07_doctor_cannot_create_doctor(self):
        resp = self._create_doctor(self.doctor_headers)
        self.assertEqual(resp.status_code, 403, resp.data)

    # ============================================================
    # Test 8 — Duplicate doctor email is rejected (409)
    # ============================================================
    def test_08_duplicate_doctor_email_rejected(self):
        self._create_doctor(self.admin_headers)
        resp = self._create_doctor(self.admin_headers)  # same email
        self.assertEqual(resp.status_code, 409, resp.data)

    # ============================================================
    # Test 9 — Admin can view the doctor list
    # ============================================================
    def test_09_admin_can_list_doctors(self):
        resp = self.client.get('/api/admin/doctors', headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        emails = [d['email'] for d in data]
        self.assertIn('doctor@test.com', emails)

    # ============================================================
    # Test 10 — Admin can deactivate a doctor
    # ============================================================
    def test_10_admin_can_deactivate_doctor(self):
        resp = self.client.patch(
            f'/api/admin/doctors/{self.doctor_user.id}/status',
            json={'is_active': False},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertFalse(data['doctor']['is_active'])

    # ============================================================
    # Test 11 — Deactivated doctor cannot log in
    # ============================================================
    def test_11_deactivated_doctor_cannot_login(self):
        # Deactivate
        self.client.patch(
            f'/api/admin/doctors/{self.doctor_user.id}/status',
            json={'is_active': False},
            headers=self.admin_headers,
        )
        # Attempt login
        resp = self._login('doctor@test.com', 'pass123')
        self.assertEqual(resp.status_code, 401, resp.data)
        data = resp.get_json()
        self.assertIn('deactivated', data.get('message', '').lower())

    # ============================================================
    # Test 12 — Admin can reactivate a doctor
    # ============================================================
    def test_12_admin_can_reactivate_doctor(self):
        # Deactivate first
        self.client.patch(
            f'/api/admin/doctors/{self.doctor_user.id}/status',
            json={'is_active': False},
            headers=self.admin_headers,
        )
        # Reactivate
        resp = self.client.patch(
            f'/api/admin/doctors/{self.doctor_user.id}/status',
            json={'is_active': True},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertTrue(resp.get_json()['doctor']['is_active'])
        # Doctor can now log in again
        login_resp = self._login('doctor@test.com', 'pass123')
        self.assertEqual(login_resp.status_code, 200)

    # ============================================================
    # Test 13 — Existing patient login still works
    # ============================================================
    def test_13_existing_patient_still_logs_in(self):
        resp = self._login('patient@test.com', 'pass123')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.get_json()['role'], 'patient')

    # ============================================================
    # Test 14 — Existing doctor login still works
    # ============================================================
    def test_14_existing_doctor_still_logs_in(self):
        resp = self._login('doctor@test.com', 'pass123')
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.get_json()['role'], 'doctor')

    # ============================================================
    # Test 15 — Public registration still assigns 'patient' role
    # ============================================================
    def test_15_public_registration_assigns_patient_role(self):
        resp = self.client.post('/api/auth/register', json={
            'full_name': 'New Public User',
            'email': 'newpublic@test.com',
            'password': 'pass123',
            'role': 'admin',  # Should be ignored
        })
        self.assertEqual(resp.status_code, 201, resp.data)
        self.assertEqual(resp.get_json()['role'], 'patient')

    # ============================================================
    # Test 16 — Users cannot change their own role via profile update
    # ============================================================
    def test_16_patient_cannot_escalate_role_via_profile_update(self):
        resp = self.client.put(
            f'/api/patients/{self.patient_profile.patient_id}',
            json={'role': 'admin'},
            headers=self.patient_headers,
        )
        # The endpoint must not change the role — either it ignores it (200/role unchanged)
        # or it returns 400/403. Either way, the user must still be 'patient'.
        user = User.query.get(self.patient_user.id)
        self.assertEqual(user.role, 'patient',
                         'Patient role must not change to admin via profile update')

    # ============================================================
    # Test 17 — Admin dashboard returns correct stats shape
    # ============================================================
    def test_17_admin_dashboard_stats(self):
        resp = self.client.get('/api/admin/dashboard', headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        for key in ('total_patients', 'total_doctors', 'active_doctors', 'inactive_doctors'):
            self.assertIn(key, data, f'Missing key: {key}')

    # ============================================================
    # Test 18 — Admin can list patients
    # ============================================================
    def test_18_admin_can_list_patients(self):
        resp = self.client.get('/api/admin/patients', headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIsInstance(data, list)
        emails = [p['email'] for p in data]
        self.assertIn('patient@test.com', emails)

    # ============================================================
    # Test 19 — Admin can view individual doctor details
    # ============================================================
    def test_19_admin_can_get_doctor_details(self):
        resp = self.client.get(
            f'/api/admin/doctors/{self.doctor_user.id}',
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data['email'], 'doctor@test.com')

    # ============================================================
    # Test 20 — Admin can update a doctor profile
    # ============================================================
    def test_20_admin_can_update_doctor_profile(self):
        resp = self.client.put(
            f'/api/admin/doctors/{self.doctor_user.id}',
            json={'specialization': 'Neurology', 'hospital': 'New Hospital'},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data['doctor']['specialization'], 'Neurology')
        self.assertEqual(data['doctor']['hospital'], 'New Hospital')

    # ============================================================
    # Test 21 — Admin can update doctor full profile including email & status
    # ============================================================
    def test_21_admin_can_update_doctor_all_fields(self):
        resp = self.client.put(
            f'/api/admin/doctors/{self.doctor_user.id}',
            json={
                'full_name': 'Dr. Updated Name',
                'email': 'dr.updated@test.com',
                'mobile_number': '+91 9988776655',
                'specialization': 'Cardiology',
                'hospital': 'Apollo Hospital',
                'medical_registration_number': 'REG-998877',
                'is_active': False,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        doc = resp.get_json()['doctor']
        self.assertEqual(doc['full_name'], 'Dr. Updated Name')
        self.assertEqual(doc['email'], 'dr.updated@test.com')
        self.assertEqual(doc['mobile_number'], '+91 9988776655')
        self.assertEqual(doc['specialization'], 'Cardiology')
        self.assertEqual(doc['hospital'], 'Apollo Hospital')
        self.assertEqual(doc['medical_registration_number'], 'REG-998877')
        self.assertFalse(doc['is_active'])

        # Verify DB directly
        db_user = db.session.get(User, self.doctor_user.id)
        self.assertEqual(db_user.full_name, 'Dr. Updated Name')
        self.assertEqual(db_user.email, 'dr.updated@test.com')
        db_prof = DoctorProfile.query.filter_by(user_id=self.doctor_user.id).first()
        self.assertFalse(db_prof.is_active)
        self.assertEqual(db_prof.medical_registration_number, 'REG-998877')

    # ============================================================
    # Test 22 — Doctor email update with conflict is rejected (409)
    # ============================================================
    def test_22_doctor_email_conflict_rejected(self):
        resp = self.client.put(
            f'/api/admin/doctors/{self.doctor_user.id}',
            json={'email': 'patient@test.com'},  # patient@test.com already exists
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 409, resp.data)
        data = resp.get_json()
        self.assertIn('already in use', data['message'].lower())

    # ============================================================
    # Test 23 — Admin get profile
    # ============================================================
    def test_23_admin_get_profile(self):
        resp = self.client.get('/api/admin/profile', headers=self.admin_headers)
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data['email'], 'admin@test.com')
        self.assertEqual(data['role'], 'admin')

    # ============================================================
    # Test 24 — Admin change email success
    # ============================================================
    def test_24_admin_change_email_success(self):
        resp = self.client.post(
            '/api/admin/change-email',
            json={'new_email': 'new_admin@test.com', 'password': 'adminpass123'},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertEqual(data['email'], 'new_admin@test.com')
        self.assertIn('token', data)

        # Verify DB directly
        user = db.session.get(User, self.admin_user.id)
        self.assertEqual(user.email, 'new_admin@test.com')

    # ============================================================
    # Test 25 — Admin change email wrong password rejected (400)
    # ============================================================
    def test_25_admin_change_email_wrong_password_rejected(self):
        resp = self.client.post(
            '/api/admin/change-email',
            json={'new_email': 'another_admin@test.com', 'password': 'wrong_password'},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 400, resp.data)
        data = resp.get_json()
        self.assertIn('password verification failed', data['message'].lower())

    # ============================================================
    # Test 26 — Admin change email duplicate rejected (409)
    # ============================================================
    def test_26_admin_change_email_duplicate_rejected(self):
        resp = self.client.post(
            '/api/admin/change-email',
            json={'new_email': 'patient@test.com', 'password': 'adminpass123'},
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 409, resp.data)
        data = resp.get_json()
        self.assertIn('already in use', data['message'].lower())

    # ============================================================
    # Test 27 — Admin change password success
    # ============================================================
    def test_27_admin_change_password_success(self):
        resp = self.client.post(
            '/api/admin/change-password',
            json={
                'current_password': 'adminpass123',
                'new_password': 'new_admin_pass_123',
                'confirm_password': 'new_admin_pass_123',
            },
            headers=self.admin_headers,
        )
        self.assertEqual(resp.status_code, 200, resp.data)
        data = resp.get_json()
        self.assertIn('token', data)

        # Verify new password works and old fails
        user = db.session.get(User, self.admin_user.id)
        self.assertTrue(user.check_password('new_admin_pass_123'))
        self.assertFalse(user.check_password('adminpass123'))


if __name__ == '__main__':
    unittest.main()

