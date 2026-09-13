from datetime import datetime
from backend.extensions import db
from backend.models.acp_preference import ACPPreference
from backend.models.patient import Patient
from backend.services.audit_service import AuditService

class ACPService:
    """Service layer dealing with patient advance care preferences and clinical workflow states."""

    @staticmethod
    def get_preferences(patient_id):
        """Retrieve the ACP preferences of a specific patient."""
        return ACPPreference.query.filter_by(patient_id=patient_id).first()

    @staticmethod
    def save_preferences(patient_id, data, performed_by_id):
        """Create or update advance care preferences for a patient."""
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} does not exist.")

        preferences = ACPPreference.query.filter_by(patient_id=patient_id).first()
        is_new = False

        if not preferences:
            preferences = ACPPreference(patient_id=patient_id)
            db.session.add(preferences)
            is_new = True

        # Mapping fields from payload
        for field in [
            'cpr_preference', 'ventilator_preference', 'dialysis_preference',
            'chemotherapy_preference', 'radiotherapy_preference', 'surgery_preference',
            'iv_fluids_preference', 'nutrition_hydration_preference', 'pain_management',
            'preferred_place_of_care', 'preferred_hospital', 'preferred_physician_name',
            'preferred_physician_designation', 'preferred_physician_institution',
            'special_focus_priority', 'gender_identity_instructions', 'relationship_instructions',
            'organ_donation', 'body_donation', 'last_rites', 'forward_to_dhrs',
            'forward_to_physician', 'forward_to_custodian', 'additional_wishes'
        ]:
            if field in data:
                setattr(preferences, field, data[field])

        # Completion is an explicit Confirmation & Review action, not an inferred
        # side effect of saving individual sections.
        if data.get('is_completed') is not None:
            preferences.is_completed = data.get('is_completed')
            if preferences.is_completed and not preferences.completed_at:
                preferences.completed_at = datetime.utcnow()

        db.session.commit()

        # Audit logging
        action = "ACP Created" if is_new else "ACP Updated"
        AuditService.log_action(
            patient_id=patient_id,
            action=action,
            performed_by_id=performed_by_id,
            remarks=f"Saved care preferences. Completion state: {preferences.is_completed}."
        )

        return preferences

    @staticmethod
    def review_preferences(patient_id, status, doctor_user_id):
        """Allow a clinical doctor to review and verify preferences."""
        preferences = ACPPreference.query.filter_by(patient_id=patient_id).first()
        if not preferences:
            raise FileNotFoundError(f"No advance care planning preferences found for Patient ID {patient_id}.")

        if status not in ('Pending Review', 'Reviewed', 'Rejected'):
            raise ValueError("Invalid review status. Must be Pending Review, Reviewed, or Rejected.")

        preferences.review_status = status
        preferences.reviewed_by_doctor = doctor_user_id
        db.session.commit()

        # Audit logging
        AuditService.log_action(
            patient_id=patient_id,
            action="Doctor Reviewed",
            performed_by_id=doctor_user_id,
            remarks=f"Updated ACP clinical review status to: {status}."
        )

        return preferences
