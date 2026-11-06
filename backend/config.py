import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Explicitly load env variables from backend/.env or root .env
_basedir = os.path.abspath(os.path.dirname(__file__))
_backend_env = os.path.join(_basedir, '.env')
_root_env = os.path.join(os.path.dirname(_basedir), '.env')

if os.path.exists(_backend_env):
    load_dotenv(_backend_env, override=True)
elif os.path.exists(_root_env):
    load_dotenv(_root_env, override=True)
else:
    load_dotenv(override=True)

class Config:
    """Base Configuration class."""
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    ENV = os.getenv("FLASK_ENV", "production")
    PORT = int(os.getenv("PORT", 5000))
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
    JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", 24))
    
    # SQLAlchemy (Supabase PostgreSQL) Config
    # SQLAlchemy Configuration
    _raw_db_url = os.getenv("DATABASE_URL")
    if _raw_db_url and _raw_db_url.startswith("postgresql://"):
        _raw_db_url = _raw_db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URI = _raw_db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Supabase Client Config
    SUPABASE_URL = (os.getenv("SUPABASE_URL") or "").strip().rstrip('/')
    SUPABASE_KEY = (os.getenv("SUPABASE_KEY") or "").strip()
    SUPABASE_SERVICE_ROLE_KEY = (os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_KEY") or "").strip()
    SUPABASE_BUCKET = (os.getenv("SUPABASE_BUCKET") or "amd-documents").strip().strip('"').strip("'")
    
    # ReportLab Configuration
    # We will use this path to save temporary PDFs before uploading to Supabase
    TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), "temp_pdfs")

    # AHCP AI Microservice Config
    AHCP_AI_BASE_URL = os.getenv("AHCP_AI_BASE_URL", "http://127.0.0.1:8000")
    AHCP_AI_SERVICE_API_KEY = os.getenv("AHCP_AI_SERVICE_API_KEY", "")
    AHCP_AI_TIMEOUT_SECONDS = int(os.getenv("AHCP_AI_TIMEOUT_SECONDS", 30))
    
    @classmethod
    def validate(cls):
        """Validate crucial production environment parameters."""
        missing = []
        if not cls.SQLALCHEMY_DATABASE_URI:
            missing.append("DATABASE_URL") 
        if not cls.JWT_SECRET_KEY:
            missing.append("JWT_SECRET_KEY")
        if not cls.SUPABASE_URL or cls.SUPABASE_URL == "https://placeholder.supabase.co":
            missing.append("SUPABASE_URL")
        supabase_secret = cls.SUPABASE_SERVICE_ROLE_KEY or cls.SUPABASE_KEY
        if not supabase_secret or supabase_secret == "placeholder-key":
            missing.append("SUPABASE_SERVICE_ROLE_KEY")
        if not cls.SUPABASE_BUCKET:
            missing.append("SUPABASE_BUCKET")
            
        if missing:
            raise ValueError(
                f"Configuration Error: Missing required environment variable(s): {', '.join(missing)}. "
                "Please configure them in your .env file."
            )
        
        # Adjust SQLAlchemy DB URL for compatibility with older SQLAlchemy versions if needed
        # (e.g. replacing 'postgres://' with 'postgresql://')
        if cls.SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            cls.SQLALCHEMY_DATABASE_URI = cls.SQLALCHEMY_DATABASE_URI.replace(
                "postgres://",
                "postgresql://",
                1
            )

        # Safe diagnostic log for project host and storage bucket without exposing secret credentials
        parsed_host = urlparse(cls.SUPABASE_URL).netloc if cls.SUPABASE_URL else "Not configured"
        print(f"[CONFIG DIAGNOSTIC] Supabase Host: {parsed_host} | Target Storage Bucket: {cls.SUPABASE_BUCKET}")

# Ensure temporary PDF dir exists locally for buffer operations
os.makedirs(Config.TEMP_PDF_DIR, exist_ok=True)
