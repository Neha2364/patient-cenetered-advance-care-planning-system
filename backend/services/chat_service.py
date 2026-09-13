from datetime import datetime
from backend.extensions import db
from backend.models.acp_preference import ACPPreference
from backend.models.chat_history import ChatHistory
from backend.models.patient import Patient
from backend.services.audit_service import AuditService

class ChatService:
    """Service to process structured data sent by the AI module and log conversational history."""

    @staticmethod
    def map_ai_value(value):
        """Helper to map conversational AI responses (e.g. Yes/No) to database enums."""
        if not value:
            return 'NOT SPECIFIED'
        val = str(value).strip().upper()
        if val in ('NO', 'DO NOT WANT', 'FALSE', 'WITHDRAW', 'WITHHOLD'):
            return 'DO NOT WANT'
        elif val in ('YES', 'WANT', 'TRUE', 'CONTINUE', 'PROVIDE'):
            return 'WANT'
        return 'NOT SPECIFIED'

    @staticmethod
    def _assistant_reply(message):
        """Provide a safe acknowledgement while the ACP assistant records the conversation."""
        normalized = message.strip().lower()
        if any(word in normalized for word in ('help', 'what', 'how')):
            return "I can help you record your care preferences. Please share your wishes in your own words, and your care team can review them with you."
        return "Thank you for sharing that. I have recorded your response. You can continue when you are ready, or discuss any important decisions with your doctor and loved ones."

    @classmethod
    def process_patient_message(cls, patient_id, message, performed_by_id):
        """Store a patient chat turn and return the assistant response for the web client."""
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} does not exist.")
        response = cls._assistant_reply(message)
        chat_log = ChatHistory(patient_id=patient_id, conversation_id='PATIENT-WEB', session_id='PATIENT-WEB', user_message=message.strip(), bot_response=response)
        db.session.add(chat_log)
        db.session.commit()
        AuditService.log_action(patient_id=patient_id, action='ACP Chat Updated', performed_by_id=performed_by_id, remarks='Patient sent a message to the ACP assistant.')
        return {'id': chat_log.id, 'user_message': chat_log.user_message, 'bot_response': chat_log.bot_response, 'created_at': chat_log.created_at.isoformat()}
    @classmethod
    def process_ai_preferences(cls, data, performed_by_id):
        """Parse preferences received from the AI module, validate, and update records."""
        patient_id = data.get('patient_id')
        
        # Verify patient exists
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} does not exist.")

        # Find or create preferences
        preferences = ACPPreference.query.filter_by(patient_id=patient_id).first()
        is_new = False
        if not preferences:
            preferences = ACPPreference(patient_id=patient_id)
            db.session.add(preferences)
            is_new = True

        # Map AI fields to database preferences
        if 'cpr' in data:
            preferences.cpr_preference = cls.map_ai_value(data['cpr'])
        if 'ventilator' in data:
            preferences.ventilator_preference = cls.map_ai_value(data['ventilator'])
        if 'dialysis' in data:
            preferences.dialysis_preference = cls.map_ai_value(data['dialysis'])
        if 'chemotherapy' in data:
            preferences.chemotherapy_preference = cls.map_ai_value(data['chemotherapy'])
        if 'radiotherapy' in data:
            preferences.radiotherapy_preference = cls.map_ai_value(data['radiotherapy'])
        if 'surgery' in data:
            preferences.surgery_preference = cls.map_ai_value(data['surgery'])
        if 'iv_fluids' in data:
            preferences.iv_fluids_preference = cls.map_ai_value(data['iv_fluids'])
        if 'nutrition_hydration' in data:
            preferences.nutrition_hydration_preference = cls.map_ai_value(data['nutrition_hydration'])
        
        # Care details
        if 'pain_management' in data:
            preferences.pain_management = data['pain_management']
        if 'preferred_place' in data:
            preferences.preferred_place_of_care = data['preferred_place']
        if 'preferred_hospital' in data:
            preferences.preferred_hospital = data['preferred_hospital']
        if 'additional_wishes' in data:
            preferences.additional_wishes = data['additional_wishes']

        # Perform auto-completion check if basic clinical directives are set
        critical_vals = [
            preferences.cpr_preference,
            preferences.ventilator_preference,
            preferences.dialysis_preference
        ]
        if all(val != 'NOT SPECIFIED' for val in critical_vals):
            preferences.is_completed = True
            if not preferences.completed_at:
                preferences.completed_at = datetime.utcnow()

        db.session.commit()

        # Log to chat history if conversation metadata is provided
        conversation_id = data.get('conversation_id', 'AI-AUTO')
        session_id = data.get('session_id', 'AI-SESSION')
        user_message = data.get('user_message', 'Conversational preferences submission.')
        bot_response = data.get('bot_response', 'Preferences mapped and saved successfully.')

        chat_log = ChatHistory(
            patient_id=patient_id,
            conversation_id=conversation_id,
            session_id=session_id,
            user_message=user_message,
            bot_response=bot_response
        )
        db.session.add(chat_log)
        db.session.commit()

        # Log audit trail
        action = "ACP Created" if is_new else "ACP Updated"
        AuditService.log_action(
            patient_id=patient_id,
            action=action,
            performed_by_id=performed_by_id,
            remarks=f"AI module processed and synchronized clinical preferences. Chat ID: {conversation_id}."
        )

        return preferences
