from backend.extensions import db
from backend.models.dhr import DHR
from backend.models.patient import Patient
from backend.services.audit_service import AuditService

class DHRService:
    """Service layer managing Designated Healthcare Representative (DHR) roles."""

    @staticmethod
    def get_dhr_by_id(dhr_id):
        """Retrieve a specific DHR record."""
        return DHR.query.get(dhr_id)

    @staticmethod
    def get_patient_dhrs(patient_id):
        """Retrieve all DHRs appointed by a patient, ordered by preference_order."""
        return DHR.query.filter_by(patient_id=patient_id).order_by(DHR.preference_order.asc()).all()

    @staticmethod
    def create_dhr(data, performed_by_id):
        """Register a new DHR and set order sequence."""
        patient_id = data.get('patient_id')
        
        # Verify patient exists
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} does not exist.")

        # Default preference order calculation
        existing_dhrs_count = DHR.query.filter_by(patient_id=patient_id).count()
        pref_order = data.get('preference_order', existing_dhrs_count + 1)

        dhr = DHR(
            patient_id=patient_id,
            full_name=data.get('full_name'),
            relationship=data.get('relationship'),
            date_of_birth=data.get('date_of_birth'),
            government_id_type=data.get('government_id_type'),
            government_id_number=data.get('government_id_number'),
            mobile_primary=data.get('mobile_primary'),
            mobile_secondary=data.get('mobile_secondary'),
            email_primary=data.get('email_primary'),
            email_secondary=data.get('email_secondary'),
            permanent_address=data.get('permanent_address'),
            signing_address=data.get('signing_address'),
            preference_order=pref_order
        )

        db.session.add(dhr)
        db.session.commit()

        # Audit logging
        AuditService.log_action(
            patient_id=patient_id,
            action="DHR Updated",
            performed_by_id=performed_by_id,
            remarks=f"Appointed DHR '{dhr.full_name}' with preference order {pref_order}."
        )

        return dhr

    @staticmethod
    def update_dhr(dhr_id, data, performed_by_id):
        """Modify details of an appointed DHR."""
        dhr = DHR.query.get(dhr_id)
        if not dhr:
            raise FileNotFoundError(f"DHR with ID {dhr_id} not found.")

        # Update fields
        for field in [
            'full_name', 'relationship', 'date_of_birth', 'government_id_type',
            'government_id_number', 'mobile_primary', 'mobile_secondary',
            'email_primary', 'email_secondary', 'permanent_address', 
            'signing_address', 'preference_order'
        ]:
            if field in data:
                setattr(dhr, field, data[field])

        db.session.commit()

        # Audit logging
        AuditService.log_action(
            patient_id=dhr.patient_id,
            action="DHR Updated",
            performed_by_id=performed_by_id,
            remarks=f"Updated details for DHR '{dhr.full_name}'."
        )

        return dhr

    @staticmethod
    def delete_dhr(dhr_id, performed_by_id):
        """Remove a DHR assignment."""
        dhr = DHR.query.get(dhr_id)
        if not dhr:
            raise FileNotFoundError(f"DHR with ID {dhr_id} not found.")

        patient_id = dhr.patient_id
        dhr_name = dhr.full_name

        db.session.delete(dhr)
        db.session.commit()

        # Re-index remaining DHRs' preference orders
        remaining = DHR.query.filter_by(patient_id=patient_id).order_by(DHR.preference_order.asc()).all()
        for idx, r_dhr in enumerate(remaining, start=1):
            r_dhr.preference_order = idx
        db.session.commit()

        # Audit logging
        AuditService.log_action(
            patient_id=patient_id,
            action="DHR Updated",
            performed_by_id=performed_by_id,
            remarks=f"Removed DHR '{dhr_name}'."
        )

        return True
