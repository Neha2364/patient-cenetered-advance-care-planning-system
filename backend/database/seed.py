from datetime import date, datetime
from backend.app import create_app
from backend.extensions import db
from backend.models.user import User
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.models.audit_log import AuditLog

def seed_database():
    """Seed sample data to test workflows and dashboard aggregations."""
    print("Seeding database...")
    
    # Ensure tables exist
    db.create_all()

    # 1. Create Users
    if not User.query.filter_by(email="patient@example.com").first():
        u1 = User(full_name="Rajesh Kumar", email="patient@example.com", role="patient")
        u1.set_password("password123")
        u2 = User(full_name="Dr. Aradhana Gowda", email="doctor@example.com", role="doctor")
        u2.set_password("password123")
        u3 = User(full_name="Admin Chief", email="admin@example.com", role="admin")
        u3.set_password("password123")
        
        db.session.add_all([u1, u2, u3])
        db.session.commit()
        print("Created users.")
    
    user_patient = User.query.filter_by(email="patient@example.com").first()
    user_doctor = User.query.filter_by(email="doctor@example.com").first()

    # 2. Create Patient Profile
    if not Patient.query.filter_by(user_id=user_patient.id).first():
        patient = Patient(
            user_id=user_patient.id,
            age=68,
            gender="Male",
            date_of_birth=date(1958, 4, 15),
            phone="+919876543210",
            address="12, 4th Cross, Malleshwaram, Bangalore",
            preferred_language="English",
            government_id_type="Aadhaar",
            government_id_number="1234-5678-9012",
            permanent_address="12, 4th Cross, Malleshwaram, Bangalore",
            current_address="12, 4th Cross, Malleshwaram, Bangalore",
            municipality_panchayat="BBMP Ward 45",
            beliefs_values="I value quality of life over duration. I wish to avoid prolonged suffering and want my family to remember me as peaceful."
        )
        db.session.add(patient)
        db.session.commit()
        print("Created patient profile.")

    patient = Patient.query.filter_by(user_id=user_patient.id).first()

    # 3. Create ACP Preferences
    if not ACPPreference.query.filter_by(patient_id=patient.patient_id).first():
        acp = ACPPreference(
            patient_id=patient.patient_id,
            cpr_preference="DO NOT WANT",
            ventilator_preference="DO NOT WANT",
            dialysis_preference="DO NOT WANT",
            chemotherapy_preference="NOT SPECIFIED",
            radiotherapy_preference="NOT SPECIFIED",
            surgery_preference="DO NOT WANT",
            iv_fluids_preference="WANT",
            nutrition_hydration_preference="DO NOT WANT",
            pain_management="Intensive comfort care, maximum pain relief even if it induces drowsiness.",
            preferred_place_of_care="Home",
            preferred_hospital="Manipal Hospital, Bangalore",
            preferred_physician_name="Dr. Aradhana Gowda",
            preferred_physician_designation="Senior Palliative Specialist",
            preferred_physician_institution="Manipal Palliative Clinic",
            special_focus_priority="Alleviating mental distress and breathing difficulty. Prefer quiet settings with family presence.",
            gender_identity_instructions="Please address me by my legal name Rajesh Kumar.",
            relationship_instructions="Refer to my wife Sunita Kumar as my legal next of kin.",
            organ_donation="YES",
            body_donation="NO",
            last_rites="Traditional rites in Malleshwaram Crematorium.",
            forward_to_dhrs=True,
            forward_to_physician=True,
            forward_to_custodian=False,
            additional_wishes="Please ensure my family is supported emotionally during this transition.",
            is_completed=True,
            completed_at=datetime.utcnow(),
            review_status="Pending Review"
        )
        db.session.add(acp)
        db.session.commit()
        print("Created ACP Preferences.")

    # 4. Create DHRs
    if not DHR.query.filter_by(patient_id=patient.patient_id).first():
        dhr1 = DHR(
            patient_id=patient.patient_id,
            full_name="Sunita Kumar",
            relationship="Spouse",
            date_of_birth=date(1962, 8, 20),
            government_id_type="Aadhaar",
            government_id_number="9876-5432-1098",
            mobile_primary="+919876543211",
            email_primary="sunita.k@example.com",
            permanent_address="12, 4th Cross, Malleshwaram, Bangalore",
            signing_address="12, 4th Cross, Malleshwaram, Bangalore",
            preference_order=1
        )
        dhr2 = DHR(
            patient_id=patient.patient_id,
            full_name="Amit Kumar",
            relationship="Son",
            date_of_birth=date(1988, 11, 5),
            government_id_type="Passport",
            government_id_number="Z1234567",
            mobile_primary="+919876543212",
            email_primary="amit.k@example.com",
            permanent_address="Flat 402, Prestige Enclave, Whitefield, Bangalore",
            signing_address="Flat 402, Prestige Enclave, Whitefield, Bangalore",
            preference_order=2
        )
        db.session.add_all([dhr1, dhr2])
        db.session.commit()
        print("Created DHR appointments.")

    # 5. Create Audit log
    if not AuditLog.query.filter_by(patient_id=patient.patient_id).first():
        log1 = AuditLog(
            patient_id=patient.patient_id,
            action="ACP Created",
            performed_by=user_patient.id,
            remarks="Patient registered profile and completed Advance Care Preferences."
        )
        db.session.add(log1)
        db.session.commit()
        print("Created audit trail entries.")

    print("Seeding completed successfully.")

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        seed_database()
