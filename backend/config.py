import os
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

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
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Supabase Client Config
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET", "amd-documents")
    
    # ReportLab Configuration
    # We will use this path to save temporary PDFs before uploading to Supabase
    TEMP_PDF_DIR = os.path.join(os.path.dirname(__file__), "temp_pdfs")
    
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
        if not cls.SUPABASE_KEY or cls.SUPABASE_KEY == "placeholder-key":
            missing.append("SUPABASE_KEY")
            
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

# Ensure temporary PDF dir exists locally for buffer operations
os.makedirs(Config.TEMP_PDF_DIR, exist_ok=True)
