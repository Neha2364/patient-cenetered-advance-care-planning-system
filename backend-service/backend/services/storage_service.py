import os
import logging
from urllib.parse import urlparse
from supabase import create_client
from storage3 import SyncStorageClient
from backend.config import Config

logger = logging.getLogger(__name__)

class StorageService:
    """Service layer dealing with Supabase Storage file uploads and downloads."""

    @staticmethod
    def _get_storage_client():
        """Create and return a Supabase Storage Client instance using the server-side service-role key.
        
        Using the server-side service-role credential bypasses Storage RLS policies,
        allowing the Flask backend to perform administrative file uploads and downloads
        to private buckets like amd-documents securely without making the bucket public.
        
        Supports both legacy JWT service-role keys (eyJ...) and modern Supabase secret keys (sb_secret_...).
        """
        service_role_key = Config.SUPABASE_SERVICE_ROLE_KEY or Config.SUPABASE_KEY
        
        # SAFE diagnostic logging without exposing secret key
        key_exists = bool(service_role_key)
        if service_role_key:
            if service_role_key.startswith("sb_secret_"):
                key_prefix = "sb_secret_..."
            elif service_role_key.startswith("eyJ"):
                key_prefix = "eyJ... (JWT)"
            else:
                key_prefix = service_role_key[:8] + "..."
        else:
            key_prefix = "None"

        parsed_host = urlparse(Config.SUPABASE_URL).netloc if Config.SUPABASE_URL else "Not configured"
        diag_msg = (
            f"[STORAGE DIAGNOSTIC] Host: {parsed_host} | "
            f"Target Bucket: {Config.SUPABASE_BUCKET} | "
            f"Service-role key: {key_exists} (Type: {key_prefix})"
        )
        print(diag_msg)
        logger.info(diag_msg)

        if not service_role_key:
            raise ValueError("SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY is missing from environment variables.")

        # Modern Supabase secret keys (sb_secret_...) are raw API secrets, not JWT tokens.
        # Direct initialization of SyncStorageClient bypasses client-side JWT format checks.
        if service_role_key.startswith("sb_secret_"):
            storage_url = f"{Config.SUPABASE_URL.rstrip('/')}/storage/v1"
            headers = {
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}"
            }
            return SyncStorageClient(storage_url, headers)

        # For JWT format keys (eyJ...), use standard create_client with fallback to SyncStorageClient.
        try:
            client = create_client(Config.SUPABASE_URL, service_role_key)
            return client.storage
        except Exception as client_err:
            logger.warning(f"create_client failed ({client_err}), falling back to direct SyncStorageClient.")
            storage_url = f"{Config.SUPABASE_URL.rstrip('/')}/storage/v1"
            headers = {
                "apikey": service_role_key,
                "Authorization": f"Bearer {service_role_key}"
            }
            return SyncStorageClient(storage_url, headers)

    @classmethod
    def create_signed_url(cls, storage_path: str, expires_in: int = 31536000) -> str:
        """Generate a time-limited signed download URL for private bucket objects without disabling RLS or making bucket public."""
        try:
            storage_client = cls._get_storage_client()
            bucket_name = Config.SUPABASE_BUCKET
            logger.info(f"[STORAGE] Generating signed URL for bucket '{bucket_name}', path '{storage_path}' (expires_in={expires_in}s)")

            result = storage_client.from_(bucket_name).create_signed_url(storage_path, expires_in)
            signed_url = result.get('signedURL') or result.get('signed_url') or result.get('signedUrl')
            if not signed_url:
                raise RuntimeError(f"Storage service returned no signed URL: {result}")

            if signed_url.startswith('/'):
                base = Config.SUPABASE_URL.rstrip('/')
                if not signed_url.startswith('/storage/v1'):
                    signed_url = f"{base}/storage/v1{signed_url}"
                else:
                    signed_url = f"{base}{signed_url}"

            return signed_url
        except Exception as e:
            raise RuntimeError(f"Failed to generate signed download URL for {storage_path}: {str(e)}")

    @classmethod
    def download_pdf(cls, storage_path: str) -> bytes:
        """Download binary content of a PDF file from the private Supabase Storage bucket using service-role credentials."""
        try:
            storage_client = cls._get_storage_client()
            bucket_name = Config.SUPABASE_BUCKET
            logger.info(f"[STORAGE] Downloading document from bucket '{bucket_name}', path '{storage_path}'")
            return storage_client.from_(bucket_name).download(storage_path)
        except Exception as e:
            raise RuntimeError(f"Failed to download document from Supabase Storage: {str(e)}")

    @classmethod
    def upload_pdf(cls, local_file_path, storage_path):
        """Upload a local PDF file to the configured Supabase Storage bucket and return a signed download URL."""
        try:
            storage_client = cls._get_storage_client()
            bucket_name = Config.SUPABASE_BUCKET
            logger.info(f"[STORAGE] Uploading PDF to bucket '{bucket_name}', destination path '{storage_path}'")

            # Ensure bucket is configured
            if not os.path.exists(local_file_path):
                raise FileNotFoundError(f"Local PDF file at {local_file_path} not found.")

            # Read file bytes
            with open(local_file_path, 'rb') as f:
                file_data = f.read()

            # Upload using the Supabase Storage client API.
            # We override if the file already exists
            response = storage_client.from_(bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "application/pdf", "x-upsert": "true"}
            )
            logger.info(f"[STORAGE] Upload succeeded to bucket '{bucket_name}', path '{storage_path}'")

            # Generate a signed URL for private bucket access (valid for 1 year = 31536000 seconds)
            # Private buckets return "Bucket not found" on get_public_url; signed URLs preserve private bucket security.
            try:
                download_url = cls.create_signed_url(storage_path, expires_in=31536000)
            except Exception as sign_err:
                logger.error(f"[STORAGE] Failed to generate signed URL for uploaded file {storage_path}: {sign_err}")
                raise RuntimeError(f"Failed to generate signed download URL for uploaded document: {sign_err}")

            return {
                'success': True,
                'pdf_name': os.path.basename(storage_path),
                'pdf_url': download_url,
                'storage_bucket': bucket_name,
                'storage_path': storage_path
            }

        except Exception as e:
            # Wrap standard exceptions to propagate cleaner errors
            raise RuntimeError(f"Failed to upload document to Supabase Storage: {str(e)}")
