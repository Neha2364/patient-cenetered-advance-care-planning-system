"""
Admin Service — authoritative business logic for admin-only operations.

All doctor creation, activation and deactivation must go through this service.
No other code path should modify doctor accounts.
"""
import secrets
import string
from datetime import datetime

from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.doctor_profile import DoctorProfile
from backend.services.audit_service import AuditService


class AdminService:
    """Business logic for the Admin Portal."""

    # ------------------------------------------------------------------ #
    # Statistics
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_dashboard_stats() -> dict:
        """Return headline counts for the admin dashboard."""
        total_patients = User.query.filter_by(role='patient').count()
        total_doctors = User.query.filter_by(role='doctor').count()

        active_doctors = (
            db.session.query(User)
            .join(DoctorProfile, DoctorProfile.user_id == User.id)
            .filter(User.role == 'doctor', DoctorProfile.is_active == True)
            .count()
        )
        inactive_doctors = total_doctors - active_doctors

        return {
            'total_patients': total_patients,
            'total_doctors': total_doctors,
            'active_doctors': active_doctors,
            'inactive_doctors': inactive_doctors,
        }

    # ------------------------------------------------------------------ #
    # Doctor management
    # ------------------------------------------------------------------ #

    @staticmethod
    def list_doctors(search: str = None) -> list:
        """Return all doctor accounts with their profiles."""
        query = (
            db.session.query(User, DoctorProfile)
            .outerjoin(DoctorProfile, DoctorProfile.user_id == User.id)
            .filter(User.role == 'doctor')
        )
        if search:
            pattern = f'%{search}%'
            query = query.filter(
                User.full_name.ilike(pattern) | User.email.ilike(pattern)
            )
        rows = query.order_by(User.created_at.desc()).all()

        result = []
        for user, profile in rows:
            result.append({
                'user_id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'created_at': user.created_at.isoformat(),
                'must_change_password': getattr(user, 'must_change_password', False),
                'mobile_number': profile.mobile_number if profile else None,
                'specialization': profile.specialization if profile else None,
                'hospital': profile.hospital if profile else None,
                'medical_registration_number': profile.medical_registration_number if profile else None,
                'is_active': profile.is_active if profile else True,
                'profile_id': profile.id if profile else None,
            })
        return result

    @staticmethod
    def get_doctor(user_id: int) -> dict | None:
        """Return a single doctor's full details."""
        user = User.query.filter_by(id=user_id, role='doctor').first()
        if not user:
            return None
        profile = DoctorProfile.query.filter_by(user_id=user_id).first()
        return {
            'user_id': user.id,
            'full_name': user.full_name,
            'email': user.email,
            'created_at': user.created_at.isoformat(),
            'must_change_password': getattr(user, 'must_change_password', False),
            'mobile_number': profile.mobile_number if profile else None,
            'specialization': profile.specialization if profile else None,
            'hospital': profile.hospital if profile else None,
            'medical_registration_number': profile.medical_registration_number if profile else None,
            'is_active': profile.is_active if profile else True,
            'profile_id': profile.id if profile else None,
        }

    @staticmethod
    def create_doctor(
        full_name: str,
        email: str,
        mobile_number: str = None,
        specialization: str = None,
        hospital: str = None,
        medical_registration_number: str = None,
        performed_by_id: int = None,
    ) -> tuple:
        """
        Create a new doctor account and profile.

        Returns (user, temp_password) where temp_password is a secure
        one-time password the admin shares with the doctor out-of-band.

        Raises ValueError on duplicate email.
        """
        if User.query.filter_by(email=email).first():
            raise ValueError(f"A user with email '{email}' already exists.")

        # Generate a secure temporary password
        alphabet = string.ascii_letters + string.digits + '!@#$%'
        temp_password = ''.join(secrets.choice(alphabet) for _ in range(16))

        # Create the user account with mandatory first-login password change
        user = User(
            full_name=full_name,
            email=email,
            role='doctor',
            must_change_password=True,
        )
        user.set_password(temp_password)
        db.session.add(user)
        db.session.flush()  # populate user.id before creating profile

        # Create the doctor profile
        profile = DoctorProfile(
            user_id=user.id,
            mobile_number=mobile_number,
            specialization=specialization,
            hospital=hospital,
            medical_registration_number=medical_registration_number,
            is_active=True,
        )
        db.session.add(profile)
        db.session.commit()

        # Audit log (no patient_id for admin actions)
        AuditService.log_action(
            patient_id=None,
            action='Admin: Doctor account created',
            performed_by_id=performed_by_id,
            remarks=f'Doctor account created for {email}',
        )

        return user, temp_password

    @staticmethod
    def update_doctor(
        user_id: int,
        full_name: str = None,
        email: str = None,
        mobile_number: str = None,
        specialization: str = None,
        hospital: str = None,
        medical_registration_number: str = None,
        is_active: bool = None,
        performed_by_id: int = None,
    ) -> dict:
        """Update a doctor's name, email, profile fields, and status. Role is never changed here."""
        user = User.query.filter_by(id=user_id, role='doctor').first()
        if not user:
            raise FileNotFoundError(f'Doctor with user_id={user_id} not found.')

        if full_name:
            user.full_name = full_name.strip()

        if email:
            email_clean = email.strip().lower()
            existing = User.query.filter(User.email == email_clean, User.id != user_id).first()
            if existing:
                raise ValueError(f"Email '{email_clean}' is already in use by another user.")
            user.email = email_clean

        profile = DoctorProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = DoctorProfile(user_id=user_id)
            db.session.add(profile)

        if mobile_number is not None:
            profile.mobile_number = mobile_number.strip() if mobile_number else None
        if specialization is not None:
            profile.specialization = specialization.strip() if specialization else None
        if hospital is not None:
            profile.hospital = hospital.strip() if hospital else None
        if medical_registration_number is not None:
            profile.medical_registration_number = (
                medical_registration_number.strip() if medical_registration_number else None
            )
        if is_active is not None:
            profile.is_active = bool(is_active)

        profile.updated_at = datetime.utcnow()
        db.session.commit()

        AuditService.log_action(
            patient_id=None,
            action='Admin: Doctor profile updated',
            performed_by_id=performed_by_id,
            remarks=f'Doctor profile updated for user_id={user_id}',
        )
        return AdminService.get_doctor(user_id)

    @staticmethod
    def set_doctor_status(user_id: int, is_active: bool, performed_by_id: int = None) -> dict:
        """Activate or deactivate a doctor account."""
        user = User.query.filter_by(id=user_id, role='doctor').first()
        if not user:
            raise FileNotFoundError(f'Doctor with user_id={user_id} not found.')

        profile = DoctorProfile.query.filter_by(user_id=user_id).first()
        if not profile:
            profile = DoctorProfile(user_id=user_id)
            db.session.add(profile)

        profile.is_active = is_active
        profile.updated_at = datetime.utcnow()
        db.session.commit()

        action_label = 'activated' if is_active else 'deactivated'
        AuditService.log_action(
            patient_id=None,
            action=f'Admin: Doctor account {action_label}',
            performed_by_id=performed_by_id,
            remarks=f'Doctor user_id={user_id} {action_label}',
        )
        return AdminService.get_doctor(user_id)

    # ------------------------------------------------------------------ #
    # Patient management (read-only view for admin)
    # ------------------------------------------------------------------ #

    @staticmethod
    def list_patients(search: str = None) -> list:
        """Return basic patient account info (no clinical data)."""
        query = (
            db.session.query(User, Patient)
            .outerjoin(Patient, Patient.user_id == User.id)
            .filter(User.role == 'patient')
        )
        if search:
            pattern = f'%{search}%'
            query = query.filter(
                User.full_name.ilike(pattern) | User.email.ilike(pattern)
            )
        rows = query.order_by(User.created_at.desc()).all()

        result = []
        for user, patient in rows:
            result.append({
                'user_id': user.id,
                'full_name': user.full_name,
                'email': user.email,
                'created_at': user.created_at.isoformat(),
                'patient_id': patient.patient_id if patient else None,
            })
        return result

    # ------------------------------------------------------------------ #
    # Login gate: deactivated doctors must not log in
    # ------------------------------------------------------------------ #

    @staticmethod
    def is_doctor_active(user_id: int) -> bool:
        """Return True if the doctor account is active (or has no profile yet = active by default)."""
        profile = DoctorProfile.query.filter_by(user_id=user_id).first()
        if profile is None:
            return True  # No profile → not deactivated
        return profile.is_active

