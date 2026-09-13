from flask import request, jsonify, g
from backend.services.dashboard_service import DashboardService
from backend.services.patient_service import PatientService
from backend.services.acp_service import ACPService
from backend.services.dhr_service import DHRService
from backend.services.amd_service import AMDService
from backend.schemas.patient import PatientSchema
from backend.schemas.acp_preference import ACPPreferenceSchema
from backend.schemas.dhr import DHRSchema
from backend.schemas.amd import GeneratedAMDSchema
from backend.utils.auth_helpers import token_required, role_required

patient_schema = PatientSchema()
patient_list_schema = PatientSchema(many=True)
acp_schema = ACPPreferenceSchema()
dhr_list_schema = DHRSchema(many=True)
amd_list_schema = GeneratedAMDSchema(many=True)

@token_required
@role_required(['doctor', 'admin'])
def doctor_get_patients():
    """Retrieve lists of patients with support for full-text search and filters (GET /doctor/patients)."""
    try:
        search_query = request.args.get('search')
        language = request.args.get('language')
        
        is_completed = request.args.get('is_completed')
        if is_completed is not None:
            is_completed = is_completed.lower() in ('true', '1')

        review_status = request.args.get('review_status')
        
        amd_generated = request.args.get('amd_generated')
        if amd_generated is not None:
            amd_generated = amd_generated.lower() in ('true', '1')

        patients = DashboardService.search_and_filter_patients(
            search_query=search_query,
            language=language,
            is_completed=is_completed,
            review_status=review_status,
            amd_generated=amd_generated
        )
        
        # Serialize list of patient details
        results = []
        for pat in patients:
            pref = pat.acp_preferences
            results.append({
                'patient_id': pat.patient_id,
                'full_name': pat.user.full_name,
                'email': pat.user.email,
                'phone': pat.phone,
                'age': pat.age,
                'preferred_language': pat.preferred_language,
                'is_completed': pref.is_completed if pref else False,
                'review_status': pref.review_status if pref else 'Pending Review',
                'amd_generated': pref.amd_generated if pref else False
            })
            
        return jsonify(results), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['doctor', 'admin'])
def doctor_get_patient_details(id):
    """Retrieve the full clinical dossier (personal details, DHRs, and ACP preferences) of a patient (GET /doctor/patient/<id>)."""
    try:
        patient = PatientService.get_patient(id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {id} not found.'}), 404

        acp = ACPService.get_preferences(id)
        dhrs = DHRService.get_patient_dhrs(id)

        response_data = {
            'patient': patient_schema.dump(patient),
            'acp_preferences': acp_schema.dump(acp) if acp else None,
            'dhrs': dhr_list_schema.dump(dhrs)
        }
        return jsonify(response_data), 200

    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def doctor_get_patient_amd_history(patient_id):
    """Retrieve the complete generated AMD document history for a patient (GET /doctor/amd/<patient_id>)."""
    try:
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to view this history.'}), 403

        history = AMDService.get_amd_history(patient_id)
        return jsonify(amd_list_schema.dump(history)), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['doctor'])
def doctor_review_patient_acp(patient_id):
    """Perform a medical review of a patient's preferences (PUT /doctor/review/<patient_id>)."""
    try:
        json_data = request.get_json()
        if not json_data or 'review_status' not in json_data:
            return jsonify({'error': 'Bad Request', 'message': 'Missing review_status in request body.'}), 400

        status = json_data['review_status']
        preferences = ACPService.review_preferences(
            patient_id=patient_id,
            status=status,
            doctor_user_id=g.current_user.id
        )

        return jsonify({
            'message': f'Patient preferences review status updated to {status} successfully.',
            'preferences': acp_schema.dump(preferences)
        }), 200

    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except ValueError as err:
        return jsonify({'error': 'Bad Request', 'message': str(err)}), 400
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


