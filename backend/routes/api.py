from flask import Blueprint

# Instantiate Blueprint
api_bp = Blueprint('api', __name__)

# Import controllers (deferred imports or simple imports)
from backend.controllers.patient_controller import (
    create_patient, get_patient, update_patient, get_my_patient_profile
)
from backend.controllers.acp_controller import (
    save_acp, get_acp, update_acp
)
from backend.controllers.dhr_controller import (
    create_dhr, get_patient_dhrs, update_dhr
)
from backend.controllers.chat_controller import (
    process_chat_data, get_chat_history
)
from backend.controllers.audit_controller import (
    get_patient_audit_logs
)
from backend.controllers.amd_controller import (
    generate_amd, download_amd
)
from backend.controllers.dashboard_controller import (
    doctor_get_patients, doctor_get_patient_details, 
    doctor_get_patient_amd_history, doctor_review_patient_acp
)
from backend.controllers.auth_controller import register, login

# Auth APIs
api_bp.add_url_rule('/auth/register', view_func=register, methods=['POST'])
api_bp.add_url_rule('/auth/login', view_func=login, methods=['POST'])

# Patient APIs
api_bp.add_url_rule('/patients', view_func=create_patient, methods=['POST'])
api_bp.add_url_rule('/patients/me', view_func=get_my_patient_profile, methods=['GET'])
api_bp.add_url_rule('/patients/<int:id>', view_func=get_patient, methods=['GET'])
api_bp.add_url_rule('/patients/<int:id>', view_func=update_patient, methods=['PUT'])

# ACP APIs
api_bp.add_url_rule('/acp', view_func=save_acp, methods=['POST'])
api_bp.add_url_rule('/acp/<int:patient_id>', view_func=get_acp, methods=['GET'])
api_bp.add_url_rule('/acp/<int:patient_id>', view_func=update_acp, methods=['PUT'])

# DHR APIs
api_bp.add_url_rule('/dhr', view_func=create_dhr, methods=['POST'])
api_bp.add_url_rule('/dhr/<int:patient_id>', view_func=get_patient_dhrs, methods=['GET'])
api_bp.add_url_rule('/dhr/<int:id>', view_func=update_dhr, methods=['PUT'])

# Chat Integration APIs
api_bp.add_url_rule('/chat/process', view_func=process_chat_data, methods=['POST'])
api_bp.add_url_rule('/chat/history/<int:patient_id>', view_func=get_chat_history, methods=['GET'])

# Audit Log APIs
api_bp.add_url_rule('/audit-logs/patient/<int:patient_id>', view_func=get_patient_audit_logs, methods=['GET'])

# AMD APIs
api_bp.add_url_rule('/amd/generate', view_func=generate_amd, methods=['POST'])
api_bp.add_url_rule('/amd/download/<int:patient_id>', view_func=download_amd, methods=['GET'])
api_bp.add_url_rule('/amd/download/<int:patient_id>/<int:amd_id>', view_func=download_amd, methods=['GET'])

# Doctor Dashboard APIs
api_bp.add_url_rule('/doctor/patients', view_func=doctor_get_patients, methods=['GET'])
api_bp.add_url_rule('/doctor/patient/<int:id>', view_func=doctor_get_patient_details, methods=['GET'])
api_bp.add_url_rule('/doctor/amd/<int:patient_id>', view_func=doctor_get_patient_amd_history, methods=['GET'])
api_bp.add_url_rule('/doctor/review/<int:patient_id>', view_func=doctor_review_patient_acp, methods=['PUT'])
