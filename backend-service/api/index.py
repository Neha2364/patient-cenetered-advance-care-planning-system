"""Vercel Serverless Function entrypoint for ACP Care Flask backend & integrated AI service."""
import os
import sys
from pathlib import Path

# Add project root and ahcp-ai-service to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

AI_SERVICE_DIR = ROOT_DIR / "ahcp-ai-service"
if str(AI_SERVICE_DIR) not in sys.path and AI_SERVICE_DIR.exists():
    sys.path.insert(0, str(AI_SERVICE_DIR))

# Ensure knowledge directory is explicitly set
os.environ.setdefault("AHCP_KNOWLEDGE_DIR", str(AI_SERVICE_DIR / "knowledge"))

# Ensure serverless in-process mode is active for AI service
os.environ.setdefault("AHCP_AI_BASE_URL", "inprocess")

# Ensure writable temp PDF directory on Vercel
os.environ.setdefault("TEMP_PDF_DIR", "/tmp/temp_pdfs")

from backend.app import create_app

# WSGI application callable for Vercel Python runtime
app = create_app()
