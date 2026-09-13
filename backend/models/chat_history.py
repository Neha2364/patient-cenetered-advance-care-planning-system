from datetime import datetime
from backend.extensions import db

class ChatHistory(db.Model):
    """AI chatbot session chat histories."""
    __tablename__ = 'chat_histories'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    conversation_id = db.Column(db.String(100), nullable=False, index=True)
    session_id = db.Column(db.String(100), nullable=False, index=True)
    user_message = db.Column(db.Text, nullable=False)
    bot_response = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    patient = db.relationship('Patient', back_populates='chat_histories')

    def __repr__(self):
        return f"<ChatHistory {self.id} (Patient {self.patient_id})>"
