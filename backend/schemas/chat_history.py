from backend.extensions import ma
from backend.models.chat_history import ChatHistory
from marshmallow import fields

class ChatHistorySchema(ma.SQLAlchemyAutoSchema):
    class Meta:
        model = ChatHistory
        load_instance = True
        include_fk = True

    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True)
    patient_id = fields.Int(required=True)
    conversation_id = fields.Str(required=True)
    session_id = fields.Str(required=True)
    user_message = fields.Str(required=True)
    bot_response = fields.Str(required=True)
