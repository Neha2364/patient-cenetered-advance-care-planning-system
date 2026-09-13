from flask import request, jsonify, g
from backend.services.dhr_service import DHRService
from backend.services.patient_service import PatientService
from backend.schemas.dhr import DHRSchema
from backend.utils.auth_helpers import token_required, role_required
from marshmallow import ValidationError

dhr_schema = DHRSchema()
dhr_list_schema = DHRSchema(many=True)

@token_required
@role_required(['patient', 'doctor', 'admin'])
def create_dhr():
    """Appoint a new Designated Healthcare Representative (DHR)."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No input data provided'}), 400

        validated_data = dhr_schema.load(json_data)
        patient_id = validated_data['patient_id']

        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        # Enforce patient ownership
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You cannot appoint DHRs for other patients.'}), 403

        dhr = DHRService.create_dhr(validated_data, performed_by_id=g.current_user.id)
        return jsonify(dhr_schema.dump(dhr)), 201

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_patient_dhrs(patient_id):
    """Retrieve all DHRs appointed by a specific patient, ordered by preference."""
    try:
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        # Enforce patient ownership
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to view this patient\'s DHR details.'}), 403

        dhrs = DHRService.get_patient_dhrs(patient_id)
        return jsonify(dhr_list_schema.dump(dhrs)), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def update_dhr(id):
    """Modify details of an existing DHR appointment."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No update data provided'}), 400

        # Retrieve DHR first to perform ownership validation
        dhr = DHRService.get_dhr_by_id(id)
        if not dhr:
            return jsonify({'error': 'Not Found', 'message': f'DHR appointment with ID {id} not found.'}), 404

        patient = PatientService.get_patient(dhr.patient_id)
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to update this DHR.'}), 403

        validated_data = dhr_schema.load(json_data, partial=True)
        updated_dhr = DHRService.update_dhr(id, validated_data, performed_by_id=g.current_user.id)
        return jsonify(dhr_schema.dump(updated_dhr)), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def delete_dhr(id):
    """Revoke a DHR appointment."""
    try:
        # Retrieve DHR first to validate ownership
        dhr = DHRService.get_dhr_by_id(id)
        if not dhr:
            return jsonify({'error': 'Not Found', 'message': f'DHR appointment with ID {id} not found.'}), 404

        patient = PatientService.get_patient(dhr.patient_id)
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to delete this DHR.'}), 403

        DHRService.delete_dhr(id, performed_by_id=g.current_user.id)
        return jsonify({'message': f'DHR appointment {id} successfully removed.'}), 200

    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
