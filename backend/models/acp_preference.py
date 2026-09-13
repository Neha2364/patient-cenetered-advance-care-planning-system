from datetime import datetime
from backend.extensions import db

class ACPPreference(db.Model):
    """ACP Preferences clinical and workflow details."""
    __tablename__ = 'acp_preferences'

    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), primary_key=True)
    
    # Life-Sustaining Treatment Preferences
    cpr_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    ventilator_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    dialysis_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    chemotherapy_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    radiotherapy_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    surgery_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    iv_fluids_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    nutrition_hydration_preference = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # WANT, DO NOT WANT, NOT SPECIFIED
    
    # Care Details
    pain_management = db.Column(db.Text, nullable=True)  # Comfort Care/description
    preferred_place_of_care = db.Column(db.String(50), nullable=True)  # Home, Hospital, Hospice
    preferred_hospital = db.Column(db.String(150), nullable=True)
    preferred_physician_name = db.Column(db.String(100), nullable=True)
    preferred_physician_designation = db.Column(db.String(100), nullable=True)
    preferred_physician_institution = db.Column(db.String(150), nullable=True)
    
    # Special focus and optional wishes
    special_focus_priority = db.Column(db.Text, nullable=True)
    gender_identity_instructions = db.Column(db.Text, nullable=True)
    relationship_instructions = db.Column(db.Text, nullable=True)
    
    # Directions upon death
    organ_donation = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # YES, NO, NOT SPECIFIED
    body_donation = db.Column(db.String(50), nullable=False, default='NOT SPECIFIED')  # YES, NO, NOT SPECIFIED
    last_rites = db.Column(db.Text, nullable=True)
    
    # Forwarding directives
    forward_to_dhrs = db.Column(db.Boolean, default=False, nullable=False)
    forward_to_physician = db.Column(db.Boolean, default=False, nullable=False)
    forward_to_custodian = db.Column(db.Boolean, default=False, nullable=False)
    
    additional_wishes = db.Column(db.Text, nullable=True)
    
    # Workflow tracking fields
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    completed_at = db.Column(db.DateTime, nullable=True)
    review_status = db.Column(db.String(50), default='Pending Review', nullable=False)  # Pending Review, Reviewed, Rejected
    reviewed_by_doctor = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    amd_generated = db.Column(db.Boolean, default=False, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    patient = db.relationship('Patient', back_populates='acp_preferences')
    doctor = db.relationship('User', foreign_keys=[reviewed_by_doctor])

    def __repr__(self):
        return f"<ACPPreference Patient ID {self.patient_id}>"
