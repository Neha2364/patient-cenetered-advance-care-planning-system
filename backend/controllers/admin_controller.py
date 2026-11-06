"""
Admin Controller — HTTP handlers for all admin-only API endpoints.

Every function here is decorated with @token_required @role_required(['admin']).
No patient or doctor token can access these endpoints.
"""
from flask import request, jsonify, g
from backend.services.admin_service import AdminService
from backend.utils.auth_helpers import token_required, role_required
from marshmallow import ValidationError


# ------------------------------------------------------------------ #
# Dashboard
# ------------------------------------------------------------------ #

@token_required
@role_required(['admin'])
def admin_get_dashboard():
    """GET /api/admin/dashboard — Admin headline statistics."""
    try:
        stats = AdminService.get_dashboard_stats()
        return jsonify(stats), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


# ------------------------------------------------------------------ #
# Doctor management
# ------------------------------------------------------------------ #

@token_required
@role_required(['admin'])
def admin_list_doctors():
    """GET /api/admin/doctors — List all doctors with optional ?search=."""
    try:
        search = request.args.get('search')
        doctors = AdminService.list_doctors(search=search)
        return jsonify(doctors), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@token_required
@role_required(['admin'])
def admin_create_doctor():
    """POST /api/admin/doctors — Create a new doctor account."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Bad Request', 'message': 'No input data provided.'}), 400

        # Required fields
        full_name = (data.get('full_name') or '').strip()
        email = (data.get('email') or '').strip().lower()
        if not full_name:
            return jsonify({'error': 'Validation Error', 'message': 'full_name is required.'}), 400
        if not email:
            return jsonify({'error': 'Validation Error', 'message': 'email is required.'}), 400

        # Optional profile fields
        mobile_number = (data.get('mobile_number') or '').strip() or None
        specialization = (data.get('specialization') or '').strip() or None
        hospital = (data.get('hospital') or '').strip() or None
        medical_registration_number = (data.get('medical_registration_number') or '').strip() or None

        user, temp_password = AdminService.create_doctor(
            full_name=full_name,
            email=email,
            mobile_number=mobile_number,
            specialization=specialization,
            hospital=hospital,
            medical_registration_number=medical_registration_number,
            performed_by_id=g.current_user.id,
        )

        return jsonify({
            'message': f'Doctor account created for {email}.',
            'user_id': user.id,
            'email': user.email,
            'full_name': user.full_name,
            # Temporary password returned once — admin must share out-of-band
            'temporary_password': temp_password,
            'note': (
                'Share this temporary password with the doctor securely. '
                'They must change it after first login. '
                'This password is not stored in plain text and will not be shown again.'
            ),
        }), 201

    except ValueError as e:
        return jsonify({'error': 'Conflict', 'message': str(e)}), 409
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@token_required
@role_required(['admin'])
def admin_get_doctor(user_id: int):
    """GET /api/admin/doctors/<user_id> — Get a single doctor's details."""
    try:
        doctor = AdminService.get_doctor(user_id)
        if not doctor:
            return jsonify({'error': 'Not Found', 'message': f'Doctor with user_id={user_id} not found.'}), 404
        return jsonify(doctor), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@token_required
@role_required(['admin'])
def admin_update_doctor(user_id: int):
    """PUT /api/admin/doctors/<user_id> — Update doctor name and profile."""
    try:
        data = request.get_json() or {}
        doctor = AdminService.update_doctor(
            user_id=user_id,
            full_name=data.get('full_name'),
            mobile_number=data.get('mobile_number'),
            specialization=data.get('specialization'),
            hospital=data.get('hospital'),
            medical_registration_number=data.get('medical_registration_number'),
            performed_by_id=g.current_user.id,
        )
        return jsonify({'message': 'Doctor profile updated.', 'doctor': doctor}), 200
    except FileNotFoundError as e:
        return jsonify({'error': 'Not Found', 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


@token_required
@role_required(['admin'])
def admin_set_doctor_status(user_id: int):
    """PATCH /api/admin/doctors/<user_id>/status — Activate or deactivate a doctor."""
    try:
        data = request.get_json() or {}
        if 'is_active' not in data:
            return jsonify({'error': 'Bad Request', 'message': 'is_active (boolean) is required.'}), 400

        is_active = bool(data['is_active'])
        doctor = AdminService.set_doctor_status(
            user_id=user_id,
            is_active=is_active,
            performed_by_id=g.current_user.id,
        )
        action = 'activated' if is_active else 'deactivated'
        return jsonify({'message': f'Doctor account {action}.', 'doctor': doctor}), 200
    except FileNotFoundError as e:
        return jsonify({'error': 'Not Found', 'message': str(e)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500


# ------------------------------------------------------------------ #
# Patient management (read-only)
# ------------------------------------------------------------------ #

@token_required
@role_required(['admin'])
def admin_list_patients():
    """GET /api/admin/patients — List basic patient account info."""
    try:
        search = request.args.get('search')
        patients = AdminService.list_patients(search=search)
        return jsonify(patients), 200
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

