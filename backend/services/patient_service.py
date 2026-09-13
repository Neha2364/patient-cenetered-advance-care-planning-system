from backend.extensions import db
from backend.models.patient import Patient
from backend.models.user import User
from backend.services.audit_service import AuditService

class PatientService:
    """Service layer containing patient registration and profile management logic."""

    @staticmethod
    def create_patient(data, performed_by_id):
        """Register a new patient and verify constraints."""
        user_id = data.get('user_id')
        
        # Verify user exists
        user = User.query.get(user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} does not exist.")

        # Check for duplicate profiles
        existing = Patient.query.filter_by(user_id=user_id).first()
        if existing:
            raise ValueError(f"Patient profile already exists for User ID {user_id}.")

        patient = Patient(
            user_id=user_id,
            age=data.get('age'),
            gender=data.get('gender'),
            date_of_birth=data.get('date_of_birth'),
            phone=data.get('phone'),
            address=data.get('address'),
            preferred_language=data.get('preferred_language', 'English'),
            government_id_type=data.get('government_id_type'),
            government_id_number=data.get('government_id_number'),
            permanent_address=data.get('permanent_address'),
            current_address=data.get('current_address'),
            municipality_panchayat=data.get('municipality_panchayat'),
            beliefs_values=data.get('beliefs_values')
        )

        db.session.add(patient)
        db.session.commit()

        # Audit log creation
        AuditService.log_action(
            patient_id=patient.patient_id,
            action="Patient Created",
            performed_by_id=performed_by_id,
            remarks=f"Created clinical profile for patient {user.full_name}"
        )

        return patient

    @staticmethod
    def get_patient(patient_id):
        """Retrieve a specific patient by their primary key ID."""
        return Patient.query.get(patient_id)

    @staticmethod
    def list_all_patients():
        """Retrieve all registered patients."""
        return Patient.query.all()

    @staticmethod
    def update_patient(patient_id, data, performed_by_id):
        """Modify an existing patient profile."""
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} not found.")

        # Update fields
        for field in [
            'age', 'gender', 'date_of_birth', 'phone', 'address', 
            'preferred_language', 'government_id_type', 'government_id_number', 
            'permanent_address', 'current_address', 'municipality_panchayat', 'beliefs_values'
        ]:
            if field in data:
                setattr(patient, field, data[field])

        db.session.commit()

        # Audit log update
        AuditService.log_action(
            patient_id=patient_id,
            action="Patient Updated",
            performed_by_id=performed_by_id,
            remarks="Updated personal information and clinical profile metrics."
        )

        return patient

    @staticmethod
    def delete_patient(patient_id, performed_by_id):
        """Remove a patient profile and cascade delete dependent structures."""
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} not found.")

        # Log audit log before removing (using a backup of patient details)
        AuditService.log_action(
            patient_id=None,
            action="Patient Deleted",
            performed_by_id=performed_by_id,
            remarks=f"Permanently removed patient ID {patient_id} from registers."
        )

        db.session.delete(patient)
        db.session.commit()
        return True
