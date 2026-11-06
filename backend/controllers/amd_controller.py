from flask import request, jsonify, g, redirect, send_file
from io import BytesIO
from backend.services.amd_service import AMDService
from backend.services.patient_service import PatientService
from backend.services.audit_service import AuditService
from backend.services.storage_service import StorageService
from backend.schemas.amd import AMDGenerateRequestSchema, GeneratedAMDSchema
from backend.utils.auth_helpers import token_required, role_required
from marshmallow import ValidationError

generate_request_schema = AMDGenerateRequestSchema()
amd_metadata_schema = GeneratedAMDSchema()
amd_metadata_list_schema = GeneratedAMDSchema(many=True)

@token_required
@role_required(['patient', 'doctor', 'admin'])
def generate_amd():
    """Extract clinical preferences and compile them into a signed, legal ReportLab PDF (POST /api/amd/generate)."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No input arguments provided.'}), 400

        # Validate request payload
        validated_data = generate_request_schema.load(json_data)
        patient_id = validated_data['patient_id']

        # Patient ownership check
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You can only generate Advance Care Plans for yourself.'}), 403

        # Call service to build, upload, and commit metadata
        amd, created = AMDService.generate_patient_amd(validated_data, performed_by_id=g.current_user.id)
        return jsonify(amd_metadata_schema.dump(amd)), 201 if created else 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except ValueError as err:
        return jsonify({'error': 'Bad Request', 'message': str(err)}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
@role_required(['patient', 'doctor', 'admin'])
def download_amd(patient_id, amd_id=None):
    """Download or stream the generated AMD PDF (GET /api/amd/download/<patient_id>)."""
    try:
        patient = PatientService.get_patient(patient_id)
        if not patient:
            return jsonify({'error': 'Not Found', 'message': f'Patient profile with ID {patient_id} not found.'}), 404

        # Ownership check
        if g.current_user.role == 'patient' and g.current_user.id != patient.user_id:
            return jsonify({'error': 'Forbidden', 'message': 'You are not authorized to download this document.'}), 403

        latest_amd = AMDService.get_amd(patient_id, amd_id) if amd_id is not None else AMDService.get_latest_amd(patient_id)
        if not latest_amd:
            return jsonify({'error': 'Not Found', 'message': 'Advance Medical Directive document not found.'}), 404

        # Log audit trail for downloading
        AuditService.log_action(
            patient_id=patient_id,
            action="AMD Downloaded",
            performed_by_id=g.current_user.id,
            remarks=f"Downloaded/Accessed PDF document '{latest_amd.pdf_name}'."
        )

        # If client explicitly requests JSON metadata, return it with a fresh signed URL
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            data = amd_metadata_schema.dump(latest_amd)
            try:
                data['pdf_url'] = StorageService.create_signed_url(latest_amd.storage_path, expires_in=3600)
            except Exception:
                pass
            return jsonify(data), 200

        # Stream binary PDF directly to the client (avoids public bucket / CORS issues)
        try:
            pdf_bytes = StorageService.download_pdf(latest_amd.storage_path)
            return send_file(
                BytesIO(pdf_bytes),
                mimetype='application/pdf',
                as_attachment=True,
                download_name=latest_amd.pdf_name
            )
        except Exception:
            # Fallback to redirecting to a fresh signed URL
            signed_url = StorageService.create_signed_url(latest_amd.storage_path, expires_in=3600)
            return redirect(signed_url)

    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
