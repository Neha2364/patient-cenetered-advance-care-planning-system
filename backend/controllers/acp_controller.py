from flask import request, jsonify, g
from backend.services.acp_service import ACPService
from backend.services.patient_service import PatientService
from backend.schemas.acp_preference import ACPPreferenceSchema
from backend.utils.auth_helpers import token_required, role_required
from marshmallow import ValidationError

acp_schema = ACPPreferenceSchema()

@token_required
@role_required(['patient', 'doctor', 'admin'])
def save_acp():
    """Create or update advance care planning preferences (POST /api/acp)."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No input data provided'}), 400

        validated_data = acp_schema.load(json_data)
        patient_id = validated_data['patient_id']
        
        # Verify ownership for patients
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404
            
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You can only manage your own preferences.'}), 403

        preferences = ACPService.save_preferences(patient_id, validated_data, performed_by_id=g.current_user.id)
        return jsonify(acp_schema.dump(preferences)), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_acp(patient_id):
    """Retrieve advance care planning preferences for a specific patient."""
    try:
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404
            
        # Verify ownership for patients
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to view these preferences.'}), 403

        preferences = ACPService.get_preferences(patient_id)
        if not preferences:
            return jsonify({'error': 'Not Found', 'message': 'No preferences registered for this patient.'}), 404

        return jsonify(acp_schema.dump(preferences)), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def update_acp(patient_id):
    """Update advance care planning preferences for a specific patient (PUT /api/acp/<patient_id>)."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No update data provided'}), 400

        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        # Verify ownership for patients
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to update these preferences.'}), 403

        validated_data = acp_schema.load(json_data, partial=True)
        preferences = ACPService.save_preferences(patient_id, validated_data, performed_by_id=g.current_user.id)
        return jsonify(acp_schema.dump(preferences)), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
