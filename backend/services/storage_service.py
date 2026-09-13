import os
from supabase import create_client, Client
from backend.config import Config

class StorageService:
    """Service layer dealing with Supabase Storage file uploads and downloads."""

    @staticmethod
    def _get_client() -> Client:
        """Create and return a Supabase Client instance."""
        return create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)

    @classmethod
    def upload_pdf(cls, local_file_path, storage_path):
        """Upload a local PDF file to the configured Supabase Storage bucket."""
        try:
            supabase_client = cls._get_client()
            bucket_name = Config.SUPABASE_BUCKET

            # Ensure bucket is configured
            if not os.path.exists(local_file_path):
                raise FileNotFoundError(f"Local PDF file at {local_file_path} not found.")

            # Read file bytes
            with open(local_file_path, 'rb') as f:
                file_data = f.read()

            # Upload using the Supabase Storage client API.
            # We override if the file already exists (or we can use unique paths)
            response = supabase_client.storage.from_(bucket_name).upload(
                path=storage_path,
                file=file_data,
                file_options={"content-type": "application/pdf", "x-upsert": "true"}
            )

            # Get public download URL
            public_url = supabase_client.storage.from_(bucket_name).get_public_url(storage_path)

            return {
                'success': True,
                'pdf_name': os.path.basename(storage_path),
                'pdf_url': public_url,
                'storage_bucket': bucket_name,
                'storage_path': storage_path
            }

        except Exception as e:
            # Wrap standard exceptions to propagate cleaner errors
            raise RuntimeError(f"Failed to upload document to Supabase Storage: {str(e)}")
