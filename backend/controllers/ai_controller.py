import logging
import uuid
from flask import request, jsonify, g
from backend.services.ai_service import (
    AIService,
    AIServiceException,
    AIServiceUnavailableException,
    AIServiceTimeoutException,
    AISessionNotFoundException,
    AISessionForbiddenException,
    AIServiceConfigException
)
from backend.services.patient_service import PatientService
from backend.utils.auth_helpers import token_required, role_required

logger = logging.getLogger("ahcp_ai_controller")

def _handle_ai_exception(e):
    if isinstance(e, (AIServiceUnavailableException, AIServiceTimeoutException, AISessionNotFoundException, AISessionForbiddenException, AIServiceConfigException)):
        return jsonify({"error": type(e).__name__, "message": e.message}), e.status_code
    elif isinstance(e, AIServiceException):
        return jsonify({"error": "AIServiceError", "message": e.message}), e.status_code
    elif isinstance(e, FileNotFoundError):
        return jsonify({"error": "NotFound", "message": str(e)}), 404
    else:
        reference = uuid.uuid4().hex[:8].upper()
        logger.exception("Unexpected error in AI controller (reference=%s)", reference)
        return jsonify({
            "error": "Internal Server Error",
            "message": f"We couldn't process your answer. Please retry. If the problem continues, contact support with reference {reference}.",
            "reference": reference,
        }), 500


@token_required
@role_required(['patient'])
def create_ai_session():
    """Create a new AHCP questionnaire session bound to the authenticated patient (POST /api/ai/session)."""
    try:
        # Resolve authenticated patient identity strictly server-side
        patient = g.current_user.patient_profile
        if not patient:
            patient = PatientService.create_patient({'user_id': g.current_user.id}, performed_by_id=g.current_user.id)

        json_data = request.get_json(silent=True) or {}
        language = json_data.get("language")
        if not language:
            if patient.preferred_language and "kannada" in patient.preferred_language.lower():
                language = "kn"
            else:
                language = "en"

        result = AIService.create_session(
            patient_id=patient.patient_id,
            language=language,
            performed_by_id=g.current_user.id
        )
        return jsonify(result), 200

    except Exception as e:
        return _handle_ai_exception(e)


@token_required
@role_required(['patient'])
def chat_ai():
    """Submit a patient message to their active questionnaire session (POST /api/ai/chat)."""
    try:
        patient = g.current_user.patient_profile
        if not patient:
            return jsonify({"error": "Forbidden", "message": "No patient profile associated with this account."}), 403

        json_data = request.get_json()
        if not json_data:
            return jsonify({"error": "Bad Request", "message": "Missing request body."}), 400

        session_id = json_data.get("session_id")
        message = json_data.get("message")
        question_number = json_data.get("question_number")
        if question_number is not None:
            try:
                question_number = int(question_number)
            except (ValueError, TypeError):
                question_number = None

        if not session_id or not isinstance(session_id, str):
            return jsonify({"error": "Bad Request", "message": "Field 'session_id' is required."}), 400
        if message is None or not isinstance(message, str):
            return jsonify({"error": "Bad Request", "message": "Field 'message' is required."}), 400

        # Session ownership is strictly enforced in AIService.process_chat
        result = AIService.process_chat(
            session_id=session_id.strip(),
            message=message.strip(),
            patient_id=patient.patient_id,
            performed_by_id=g.current_user.id,
            question_number=question_number
        )
        return jsonify(result), 200

    except Exception as e:
        return _handle_ai_exception(e)


@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_ai_patient_record():
    """Retrieve structured patient record for a session (POST /api/ai/patient-record or GET)."""
    try:
        session_id = request.args.get("session_id")
        patient_id_arg = request.args.get("patient_id")
        if request.is_json:
            data = request.get_json(silent=True) or {}
            session_id = session_id or data.get("session_id")
            patient_id_arg = patient_id_arg or data.get("patient_id")

        patient_id = None
        if patient_id_arg:
            try:
                patient_id = int(patient_id_arg)
            except ValueError:
                return jsonify({"error": "Bad Request", "message": "Invalid patient_id parameter."}), 400

        # Enforce patient ownership: patients can only access their own session
        authenticated_patient_id = None
        if g.current_user.role == "patient":
            patient_profile = g.current_user.patient_profile
            if not patient_profile:
                return jsonify({"error": "Forbidden", "message": "Patient profile not found."}), 403
            authenticated_patient_id = patient_profile.patient_id
            if patient_id is not None and patient_id != authenticated_patient_id:
                return jsonify({"error": "Forbidden", "message": "You cannot access another patient's data."}), 403
            patient_id = authenticated_patient_id

        if not session_id and patient_id:
            from backend.models.ai_session import AISession
            ai_sess = AISession.query.filter_by(patient_id=patient_id).order_by(AISession.created_at.desc()).first()
            if ai_sess:
                session_id = ai_sess.session_id
            else:
                return jsonify(AIService._synthesize_record_from_db(patient_id)), 200

        if not session_id:
            return jsonify({"error": "Bad Request", "message": "Parameter 'session_id' or 'patient_id' is required."}), 400

        result = AIService.get_patient_record(session_id.strip(), authenticated_patient_id=authenticated_patient_id)
        return jsonify(result), 200

    except Exception as e:
        return _handle_ai_exception(e)


@token_required
@role_required(['patient', 'doctor', 'admin'])
def get_ai_doctor_dashboard():
    """Retrieve AI doctor-dashboard data (POST /api/ai/doctor-dashboard or GET)."""
    try:
        session_id = request.args.get("session_id")
        patient_id_arg = request.args.get("patient_id")

        if not session_id and request.is_json:
            data = request.get_json(silent=True) or {}
            session_id = data.get("session_id")
            patient_id_arg = data.get("patient_id") or patient_id_arg

        patient_id = None
        if patient_id_arg:
            try:
                patient_id = int(patient_id_arg)
            except ValueError:
                return jsonify({"error": "Bad Request", "message": "Invalid patient_id parameter."}), 400

        authenticated_patient_id = None
        if g.current_user.role == "patient":
            patient_profile = g.current_user.patient_profile
            if not patient_profile:
                return jsonify({"error": "Forbidden", "message": "Patient profile not found."}), 403
            authenticated_patient_id = patient_profile.patient_id
            if patient_id is not None and patient_id != authenticated_patient_id:
                return jsonify({"error": "Forbidden", "message": "You cannot access another patient's data."}), 403
            patient_id = authenticated_patient_id

        if not session_id and not patient_id:
            return jsonify({"error": "Bad Request", "message": "Either 'session_id' or 'patient_id' must be specified."}), 400

        result = AIService.get_doctor_dashboard_data(
            session_id=session_id.strip() if session_id else None,
            patient_id=patient_id,
            authenticated_patient_id=authenticated_patient_id
        )
        return jsonify(result), 200

    except Exception as e:
        return _handle_ai_exception(e)


@token_required
@role_required(['patient'])
def get_active_patient_session():
    """Fetch the active or latest AI questionnaire session for the logged-in patient (GET /api/ai/session/active)."""
    try:
        patient = g.current_user.patient_profile
        if not patient:
            return jsonify({"session": None}), 200

        session_data = AIService.get_active_session_data(patient.patient_id)
        return jsonify({"session": session_data}), 200
    except Exception as e:
        return _handle_ai_exception(e)


@token_required
@role_required(['patient'])
def update_ai_session_language():
    """Update language of the active session (POST/PUT /api/ai/session/language)."""
    try:
        patient = g.current_user.patient_profile
        if not patient:
            return jsonify({"error": "Forbidden", "message": "No patient profile associated with this account."}), 403

        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        language = data.get("language")

        if not session_id or not isinstance(session_id, str):
            return jsonify({"error": "Bad Request", "message": "Field 'session_id' is required."}), 400
        if not language or language not in ("en", "kn"):
            return jsonify({"error": "Bad Request", "message": "Valid 'language' ('en' or 'kn') is required."}), 400

        result = AIService.update_session_language(
            session_id=session_id.strip(),
            language=language,
            patient_id=patient.patient_id
        )
        return jsonify(result), 200
    except Exception as e:
        return _handle_ai_exception(e)


@token_required
@role_required(['patient'])
def confirm_ai_review():
    """Confirm review and finalize ACP plan (POST /api/ai/confirm-review)."""
    try:
        patient = g.current_user.patient_profile
        if not patient:
            return jsonify({"error": "Forbidden", "message": "No patient profile associated with this account."}), 403

        data = request.get_json(silent=True) or {}
        session_id = data.get("session_id")
        if not session_id or not isinstance(session_id, str):
            from backend.models.ai_session import AISession
            ai_sess = AISession.query.filter_by(patient_id=patient.patient_id).order_by(AISession.created_at.desc()).first()
            if ai_sess:
                session_id = ai_sess.session_id
            else:
                return jsonify({"error": "Bad Request", "message": "No active session found to confirm."}), 400

        result = AIService.confirm_review(
            patient_id=patient.patient_id,
            performed_by_id=g.current_user.id,
            session_id=session_id.strip() if session_id else None
        )
        return jsonify(result), 200
    except Exception as e:
        return _handle_ai_exception(e)


def check_ai_health():
    """Safe public health check for the AI service integration (GET /api/ai/health)."""
    result = AIService.health_check()
    status_code = 200 if result.get("backend_connected") else 503
    return jsonify(result), status_code

