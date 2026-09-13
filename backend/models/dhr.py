from backend.extensions import db

class DHR(db.Model):
    """Designated Healthcare Representative (DHR) model."""
    __tablename__ = 'dhrs'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.patient_id', ondelete='CASCADE'), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    relationship = db.Column(db.String(50), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=True)
    government_id_type = db.Column(db.String(50), nullable=True)  # Aadhaar, Passport, Driving License, Voter ID
    government_id_number = db.Column(db.String(50), nullable=True)
    mobile_primary = db.Column(db.String(20), nullable=False)
    mobile_secondary = db.Column(db.String(20), nullable=True)
    email_primary = db.Column(db.String(100), nullable=False)
    email_secondary = db.Column(db.String(100), nullable=True)
    permanent_address = db.Column(db.Text, nullable=True)
    signing_address = db.Column(db.Text, nullable=True)
    preference_order = db.Column(db.Integer, default=1, nullable=False)  # 1 = Primary, 2 = Alternate 1, 3 = Alternate 2

    # Relationships
    patient = db.relationship('Patient', back_populates='dhrs')

    def __repr__(self):
        return f"<DHR {self.full_name} for Patient ID {self.patient_id}>"
