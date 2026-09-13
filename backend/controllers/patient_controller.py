from flask import request, jsonify, g
from backend.services.patient_service import PatientService
from backend.schemas.patient import PatientSchema
from backend.utils.auth_helpers import token_required, role_required
from marshmallow import ValidationError

# Instantiate schemas
patient_schema = PatientSchema()
patient_list_schema = PatientSchema(many=True)

@token_required
@role_required(['patient', 'doctor', 'admin'])
def create_patient():
    """Create a new patient clinical profile."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No input data provided'}), 400
        
        # Validate data
        validated_data = patient_schema.load(json_data)
        
        # Enforce rule: A patient user can only create their own profile, 
        # whereas doctors/admins can create profiles for any user.
        if g.current_user.role == 'patient' and g.current_user.id != validated_data['user_id']:
            return jsonify({'error': 'Forbidden', 'message': 'Patients can only create their own profile.'}), 403

        patient = PatientService.create_patient(validated_data, performed_by_id=g.current_user.id)
        return jsonify(patient_schema.dump(patient)), 201

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except ValueError as err:
        return jsonify({'error': 'Bad Request', 'message': str(err)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_patient(id):
    """Retrieve detailed clinical profile metrics for a specific patient."""
    try:
        patient = PatientService.get_patient(id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {id} not found.'}), 404
        
        # Authorization check: patients can only access their own profile
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to access this profile.'}), 403

        return jsonify(patient_schema.dump(patient)), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def update_patient(id):
    """Update details of an existing patient profile."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No update data provided'}), 400
        
        # Fetch patient profile first to authorize
        patient = PatientService.get_patient(id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {id} not found.'}), 404
            
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to update this profile.'}), 403

        # We load partial because it's an update operation
        validated_data = patient_schema.load(json_data, partial=True)
        updated_patient = PatientService.update_patient(id, validated_data, performed_by_id=g.current_user.id)
        return jsonify(patient_schema.dump(updated_patient)), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_my_patient_profile():
    """Retrieve detailed clinical profile metrics for the logged-in patient."""
    try:
        patient = g.current_user.patient_profile
        if not patient:
            if g.current_user.role == 'patient':
                patient = PatientService.create_patient({'user_id': g.current_user.id}, performed_by_id=g.current_user.id)
            else:
                return jsonify({'error': 'Not Found', 'message': 'Patient profile not found for this user.'}), 404
        
        return jsonify(patient_schema.dump(patient)), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

