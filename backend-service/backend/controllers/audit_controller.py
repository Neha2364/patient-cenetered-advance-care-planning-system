from flask import jsonify, g
from backend.services.audit_service import AuditService
from backend.services.patient_service import PatientService
from backend.schemas.audit_log import AuditLogSchema
from backend.utils.auth_helpers import token_required, role_required

audit_schema = AuditLogSchema(many=True)

@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_patient_audit_logs(patient_id):
    """Retrieve audit logs associated with a specific patient."""
    try:
        # Verify patient exists
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to access these logs.'}), 403

        logs = AuditService.get_logs_by_patient(patient_id)
        return jsonify(audit_schema.dump(logs)), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
