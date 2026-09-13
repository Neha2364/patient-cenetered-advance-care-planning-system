from flask import request, jsonify, g
from backend.services.chat_service import ChatService
from backend.utils.auth_helpers import token_required
from marshmallow import Schema, fields, ValidationError

class AIProcessPayloadSchema(Schema):
    """Schema to validate payloads received from the AI chatbot module."""
    patient_id = fields.Int(required=True)
    cpr = fields.Str(allow_none=True)
    ventilator = fields.Str(allow_none=True)
    dialysis = fields.Str(allow_none=True)
    chemotherapy = fields.Str(allow_none=True)
    radiotherapy = fields.Str(allow_none=True)
    surgery = fields.Str(allow_none=True)
    iv_fluids = fields.Str(allow_none=True)
    nutrition_hydration = fields.Str(allow_none=True)
    pain_management = fields.Str(allow_none=True)
    preferred_place = fields.Str(allow_none=True)
    preferred_hospital = fields.Str(allow_none=True)
    additional_wishes = fields.Str(allow_none=True)
    
    # Conversational Metadata
    conversation_id = fields.Str(allow_none=True)
    session_id = fields.Str(allow_none=True)
    user_message = fields.Str(allow_none=True)
    bot_response = fields.Str(allow_none=True)
    message = fields.Str(allow_none=True)

ai_payload_schema = AIProcessPayloadSchema()

@token_required
def process_chat_data():
    """Ingest preferences parsed by the AI chatbot and synchronize them with Supabase (POST /chat/process)."""
    try:
        json_data = request.get_json()
        if not json_data:
            return jsonify({'error': 'Bad Request', 'message': 'No chatbot data payload provided.'}), 400

        # Validate structured input from AI module
        validated_data = ai_payload_schema.load(json_data)
        
        # Security check: Patients can only push their own AI logs. 
        # Doctors and admins can invoke it for any patient.
        if g.current_user.role == 'patient':
            # We must verify if the patient_id matches the logged-in user's patient profile.
            patient_profile = g.current_user.patient_profile
            if not patient_profile or patient_profile.patient_id != validated_data['patient_id']:
                return jsonify({'error': 'Forbidden', 'message': 'Patients can only process chat logs for their own profile.'}), 403

        if validated_data.get('message'):
            result = ChatService.process_patient_message(
                patient_id=validated_data['patient_id'],
                message=validated_data['message'],
                performed_by_id=g.current_user.id,
            )
            return jsonify({'status': 'success', 'message': 'Message saved successfully.', 'chat': result}), 200

        preferences = ChatService.process_ai_preferences(validated_data, performed_by_id=g.current_user.id)
        
        return jsonify({
            'status': 'success',
            'message': 'Conversational ACP preferences processed and synchronized successfully.',
            'preferences': {
                'patient_id': preferences.patient_id,
                'is_completed': preferences.is_completed,
                'review_status': preferences.review_status
            }
        }), 200

    except ValidationError as err:
        return jsonify({'error': 'Validation Error', 'message': err.messages}), 400
    except FileNotFoundError as err:
        return jsonify({'error': 'Not Found', 'message': str(err)}), 404
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500

@token_required
def get_chat_history(patient_id):
    """Retrieve all chat messages (conversational history) for a specific patient."""
    try:
        from backend.models.chat_history import ChatHistory
        from backend.schemas.chat_history import ChatHistorySchema
        
        # Security check: Patients can only fetch their own logs.
        if g.current_user.role == 'patient':
            patient_profile = g.current_user.patient_profile
            if not patient_profile or patient_profile.patient_id != patient_id:
                return jsonify({'error': 'Forbidden', 'message': 'Patients can only retrieve chat logs for their own profile.'}), 403

        # Retrieve logs ordered by created_at ascending
        logs = ChatHistory.query.filter_by(patient_id=patient_id).order_by(ChatHistory.created_at.asc()).all()
        schema = ChatHistorySchema(many=True)
        return jsonify(schema.dump(logs)), 200
        
    except Exception as e:
        return jsonify({'error': 'Internal Server Error', 'message': str(e)}), 500
