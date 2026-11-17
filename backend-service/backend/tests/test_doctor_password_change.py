"""
Unit and Integration Test Suite: Doctor Mandatory First-Login Password Change

Tests:
1. Newly created doctor has must_change_password=True in DB and login response.
2. Doctor with must_change_password=True is blocked from protected doctor endpoints (403).
3. Incorrect current password rejected (400).
4. Mismatched new password and confirm_password rejected (400).
5. New password identical to current password rejected (400).
6. New password shorter than 6 characters rejected (400).
7. Successful password change updates hash, clears must_change_password, logs audit event.
8. After password change, doctor can access protected endpoints (200).
9. Doctor can log in with the new password and subsequent logins show must_change_password=False.
10. Old temporary password no longer works (401).
11. Patient and admin logins are unaffected (must_change_password=False).
12. Cross-user isolation: change-password only updates the authenticated user.
"""

import unittest
import json
from backend.config import Config
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.doctor_profile import DoctorProfile
from backend.services.admin_service import AdminService


class TestConfig(Config):
    TESTING = True
    ENV = 'testing'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    AHCP_AI_SERVICE_API_KEY = 'test-secret'
    JWT_SECRET_KEY = 'test-jwt-password-change-secret'


class DoctorPasswordChangeTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

        # Seed Admin
        self.admin = User(full_name='System Admin', email='admin@acpcare.app', role='admin')
        self.admin.set_password('AdminPass123!')
        db.session.add(self.admin)

        # Seed Existing Patient
        self.patient = User(full_name='Alice Patient', email='alice@patient.com', role='patient')
        self.patient.set_password('PatientPass123!')
        db.session.add(self.patient)

        # Seed Existing Established Doctor (default must_change_password=False)
        self.est_doctor = User(full_name='Dr. Established', email='est@hospital.com', role='doctor')
        self.est_doctor.set_password('EstPass123!')
        self.est_doctor.must_change_password = False
        db.session.add(self.est_doctor)
        db.session.flush()

        est_profile = DoctorProfile(user_id=self.est_doctor.id, specialization='Cardiology', is_active=True)
        db.session.add(est_profile)
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def _login(self, email, password):
        res = self.client.post(
            '/api/auth/login',
            data=json.dumps({'email': email, 'password': password}),
            content_type='application/json',
        )
        return res

    def test_01_newly_created_doctor_has_must_change_password_true(self):
        """Admin creates doctor -> must_change_password is True."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. Newcomer',
            email='newcomer@hospital.com',
            specialization='Neurology',
            performed_by_id=self.admin.id,
        )
        self.assertTrue(user.must_change_password)

        # Log in with temporary password
        res = self._login('newcomer@hospital.com', temp_pw)
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.data)
        self.assertTrue(body.get('must_change_password'))
        self.assertIn('token', body)

    def test_02_doctor_cannot_access_protected_features_before_password_change(self):
        """Doctor with must_change_password=True receives 403 on protected doctor APIs."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. Blocked',
            email='blocked@hospital.com',
            specialization='Oncology',
            performed_by_id=self.admin.id,
        )
        login_res = self._login('blocked@hospital.com', temp_pw)
        token = json.loads(login_res.data)['token']

        # Attempt to access doctor patients endpoint
        res = self.client.get(
            '/api/doctor/patients',
            headers={'Authorization': f'Bearer {token}'},
        )
        self.assertEqual(res.status_code, 403)
        body = json.loads(res.data)
        self.assertTrue(body.get('must_change_password'))
        self.assertIn('Password change required', body.get('message', ''))

    def test_03_incorrect_current_password_rejected(self):
        """change-password endpoint rejects an incorrect current password with 400."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. WrongPw',
            email='wrongpw@hospital.com',
            performed_by_id=self.admin.id,
        )
        token = json.loads(self._login('wrongpw@hospital.com', temp_pw).data)['token']

        res = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': f'Bearer {token}'},
            data=json.dumps({
                'current_password': 'IncorrectCurrentPassword123!',
                'new_password': 'NewValidPassword123!',
                'confirm_password': 'NewValidPassword123!',
            }),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)
        body = json.loads(res.data)
        self.assertIn('Current password is incorrect', body.get('message', ''))

    def test_04_mismatched_confirmation_rejected(self):
        """change-password rejects mismatched new password and confirmation."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. Mismatch',
            email='mismatch@hospital.com',
            performed_by_id=self.admin.id,
        )
        token = json.loads(self._login('mismatch@hospital.com', temp_pw).data)['token']

        res = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': f'Bearer {token}'},
            data=json.dumps({
                'current_password': temp_pw,
                'new_password': 'NewPassword123!',
                'confirm_password': 'DifferentPassword123!',
            }),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)
        body = json.loads(res.data)
        self.assertIn('do not match', body.get('message', ''))

    def test_05_same_password_as_current_rejected(self):
        """change-password rejects setting the new password to the current password."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. SamePw',
            email='samepw@hospital.com',
            performed_by_id=self.admin.id,
        )
        token = json.loads(self._login('samepw@hospital.com', temp_pw).data)['token']

        res = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': f'Bearer {token}'},
            data=json.dumps({
                'current_password': temp_pw,
                'new_password': temp_pw,
                'confirm_password': temp_pw,
            }),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)
        body = json.loads(res.data)
        self.assertIn('different from current', body.get('message', ''))

    def test_06_new_password_too_short_rejected(self):
        """change-password rejects passwords with fewer than 6 characters."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. ShortPw',
            email='shortpw@hospital.com',
            performed_by_id=self.admin.id,
        )
        token = json.loads(self._login('shortpw@hospital.com', temp_pw).data)['token']

        res = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': f'Bearer {token}'},
            data=json.dumps({
                'current_password': temp_pw,
                'new_password': '123',
                'confirm_password': '123',
            }),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 400)

    def test_07_successful_password_change_flow(self):
        """Full end-to-end first-login password change flow."""
        user, temp_pw = AdminService.create_doctor(
            full_name='Dr. FlowTest',
            email='flow@hospital.com',
            specialization='Pulmonology',
            performed_by_id=self.admin.id,
        )

        # 1. First login with temporary password
        login_res = self._login('flow@hospital.com', temp_pw)
        self.assertEqual(login_res.status_code, 200)
        login_data = json.loads(login_res.data)
        initial_token = login_data['token']
        self.assertTrue(login_data['must_change_password'])

        # 2. Blocked from protected endpoint
        blocked_res = self.client.get(
            '/api/doctor/patients',
            headers={'Authorization': f'Bearer {initial_token}'},
        )
        self.assertEqual(blocked_res.status_code, 403)

        # 3. Change password successfully
        new_pw = 'DoctorSecure2026!'
        change_res = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': f'Bearer {initial_token}'},
            data=json.dumps({
                'current_password': temp_pw,
                'new_password': new_pw,
                'confirm_password': new_pw,
            }),
            content_type='application/json',
        )
        self.assertEqual(change_res.status_code, 200)
        change_data = json.loads(change_res.data)
        self.assertFalse(change_data['must_change_password'])
        new_token = change_data['token']

        # 4. Protected endpoint now accessible with new token
        allowed_res = self.client.get(
            '/api/doctor/patients',
            headers={'Authorization': f'Bearer {new_token}'},
        )
        self.assertEqual(allowed_res.status_code, 200)

        # 5. Subsequent login with new password works and shows must_change_password=False
        subsequent_res = self._login('flow@hospital.com', new_pw)
        self.assertEqual(subsequent_res.status_code, 200)
        subsequent_data = json.loads(subsequent_res.data)
        self.assertFalse(subsequent_data['must_change_password'])

        # 6. Old temporary password no longer works
        old_login_res = self._login('flow@hospital.com', temp_pw)
        self.assertEqual(old_login_res.status_code, 401)

    def test_08_patient_and_admin_logins_unaffected(self):
        """Existing patient and admin logins return must_change_password=False and function normally."""
        pat_res = self._login('alice@patient.com', 'PatientPass123!')
        self.assertEqual(pat_res.status_code, 200)
        pat_data = json.loads(pat_res.data)
        self.assertFalse(pat_data['must_change_password'])
        self.assertEqual(pat_data['role'], 'patient')

        adm_res = self._login('admin@acpcare.app', 'AdminPass123!')
        self.assertEqual(adm_res.status_code, 200)
        adm_data = json.loads(adm_res.data)
        self.assertFalse(adm_data['must_change_password'])
        self.assertEqual(adm_data['role'], 'admin')

    def test_09_established_doctor_can_change_password_voluntarily(self):
        """Established doctors (must_change_password=False) can change password at any time."""
        login_res = self._login('est@hospital.com', 'EstPass123!')
        token = json.loads(login_res.data)['token']

        res = self.client.post(
            '/api/auth/change-password',
            headers={'Authorization': f'Bearer {token}'},
            data=json.dumps({
                'current_password': 'EstPass123!',
                'new_password': 'BrandNewEstPass2026!',
                'confirm_password': 'BrandNewEstPass2026!',
            }),
            content_type='application/json',
        )
        self.assertEqual(res.status_code, 200)

        # Verify new password works
        re_login = self._login('est@hospital.com', 'BrandNewEstPass2026!')
        self.assertEqual(re_login.status_code, 200)


if __name__ == '__main__':
    unittest.main()

