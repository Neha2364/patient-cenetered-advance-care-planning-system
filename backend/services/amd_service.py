import os
from datetime import datetime
from backend.extensions import db
from backend.config import Config
from backend.models.generated_amd import GeneratedAMD
from backend.models.patient import Patient
from backend.models.acp_preference import ACPPreference
from backend.models.dhr import DHR
from backend.services.storage_service import StorageService
from backend.services.audit_service import AuditService
from backend.utils.pdf_generator import generate_amd_pdf

class AMDService:
    """Service layer orchestrating the retrieval, rendering, storage upload, and metadata persistence of AMDs."""

    @staticmethod
    def generate_patient_amd(data, performed_by_id):
        """Extract preferences, render ReportLab PDF, upload to Supabase, and write metadata."""
        patient_id = data.get('patient_id')

        # 1. Fetch data
        patient = Patient.query.get(patient_id)
        if not patient:
            raise FileNotFoundError(f"Patient with ID {patient_id} does not exist.")

        preferences = ACPPreference.query.filter_by(patient_id=patient_id).first()
        if not preferences or not preferences.is_completed:
            raise ValueError(f"Advance Care Planning is not completed/active for Patient ID {patient_id}.")

        dhrs = DHR.query.filter_by(patient_id=patient_id).order_by(DHR.preference_order.asc()).all()
        if not dhrs:
            raise ValueError(f"At least one Designated Healthcare Representative (DHR) is required to generate an AMD.")

        # 2. Reuse the active document unless the caller explicitly requests a new version.
        active_amd = GeneratedAMD.query.filter_by(patient_id=patient_id, status='Active').first()
        if active_amd and not data.get('create_new_version', False):
            return active_amd, False

        # Mark past active AMDs as Superseded only for an intentional new version.
        past_amds = GeneratedAMD.query.filter_by(patient_id=patient_id, status='Active').all()
        current_version = 1
        for past in past_amds:
            past.status = 'Superseded'
            current_version = max(current_version, past.version + 1)
        
        # 3. Create temp local path
        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"AMD_Patient_{patient_id}_v{current_version}_{timestamp_str}.pdf"
        local_pdf_path = os.path.join(Config.TEMP_PDF_DIR, pdf_filename)
        storage_path = f"patient_{patient_id}/v{current_version}/{pdf_filename}"

        try:
            # 4. Generate the PDF locally using ReportLab
            generate_amd_pdf(
                patient=patient,
                preferences=preferences,
                dhrs=dhrs,
                witnesses=data.get('witnesses'),
                notary_name=data.get('notary_name'),
                notary_place=data.get('notary_place'),
                executor_place=data.get('executor_place'),
                output_path=local_pdf_path
            )

            # 5. Upload to Supabase Storage
            upload_result = StorageService.upload_pdf(
                local_file_path=local_pdf_path,
                storage_path=storage_path
            )

            # 6. Save metadata in PostgreSQL
            amd_metadata = GeneratedAMD(
                patient_id=patient_id,
                pdf_name=upload_result['pdf_name'],
                pdf_url=upload_result['pdf_url'],
                storage_bucket=upload_result['storage_bucket'],
                storage_path=upload_result['storage_path'],
                version=current_version,
                status='Active'
            )
            db.session.add(amd_metadata)

            # Mark preference workflow state as generated
            preferences.amd_generated = True
            db.session.commit()

            # 7. Write Audit log
            AuditService.log_action(
                patient_id=patient_id,
                action="AMD Generated",
                performed_by_id=performed_by_id,
                remarks=f"Generated Advance Medical Directive PDF (Version {current_version}). Uploaded to Supabase Storage."
            )

            return amd_metadata, True

        finally:
            # Cleanup local temporary file
            if os.path.exists(local_pdf_path):
                try:
                    os.remove(local_pdf_path)
                except Exception as cleanup_err:
                    print(f"Warning: Failed to clean up temp file {local_pdf_path}: {str(cleanup_err)}")

    @staticmethod
    def get_latest_amd(patient_id):
        """Retrieve the latest active AMD metadata record for a patient."""
        return GeneratedAMD.query.filter_by(patient_id=patient_id, status='Active').order_by(GeneratedAMD.version.desc()).first()

    @staticmethod
    def get_amd(patient_id, amd_id):
        """Retrieve a specific AMD document only when it belongs to the patient."""
        return GeneratedAMD.query.filter_by(patient_id=patient_id, id=amd_id).first()

    @staticmethod
    def get_amd_history(patient_id):
        """Retrieve all generated AMD metadata records for a patient."""
        return GeneratedAMD.query.filter_by(patient_id=patient_id).order_by(GeneratedAMD.version.desc()).all()
