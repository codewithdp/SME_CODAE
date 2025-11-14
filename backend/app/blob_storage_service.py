"""
Azure Blob Storage Service
Handles file upload, download, and deletion from Azure Blob Storage
"""

import os
import logging
from typing import Optional, BinaryIO
from datetime import datetime, timedelta
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, generate_blob_sas, BlobSasPermissions, ContentSettings
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError

logger = logging.getLogger(__name__)


class BlobStorageService:
    """
    Service for managing files in Azure Blob Storage
    """

    def __init__(self, connection_string: str, container_name: str = "bulk-uploads"):
        """
        Initialize Blob Storage service

        Args:
            connection_string: Azure Storage connection string
            container_name: Default container name
        """
        self.connection_string = connection_string
        self.default_container = container_name
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)

        # Ensure default container exists
        self._ensure_container_exists(container_name)

    def _ensure_container_exists(self, container_name: str):
        """Create container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(container_name)
            if not container_client.exists():
                container_client.create_container()
                logger.info(f"Created container: {container_name}")
        except ResourceExistsError:
            pass
        except Exception as e:
            logger.error(f"Error ensuring container exists: {e}")
            raise

    def upload_file(
        self,
        file_data: BinaryIO,
        blob_name: str,
        container_name: Optional[str] = None,
        content_type: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> str:
        """
        Upload file to blob storage

        Args:
            file_data: File-like object to upload
            blob_name: Name/path for the blob (e.g., "2025-01/upload_123/original.pdf")
            container_name: Container name (uses default if not specified)
            content_type: MIME type of the file
            metadata: Optional metadata dictionary

        Returns:
            str: Blob path (container_name/blob_name)
        """
        container = container_name or self.default_container
        self._ensure_container_exists(container)

        try:
            blob_client = self.blob_service_client.get_blob_client(
                container=container,
                blob=blob_name
            )

            # Upload with optional content type and metadata
            content_settings_obj = ContentSettings(content_type=content_type) if content_type else None

            blob_client.upload_blob(
                file_data,
                overwrite=True,
                content_settings=content_settings_obj,
                metadata=metadata
            )

            blob_path = f"{container}/{blob_name}"
            logger.info(f"Uploaded file to: {blob_path}")
            return blob_path

        except Exception as e:
            logger.error(f"Error uploading file to blob storage: {e}")
            raise

    def download_file(self, blob_path: str) -> bytes:
        """
        Download file from blob storage

        Args:
            blob_path: Full path (container/blob_name)

        Returns:
            bytes: File content
        """
        try:
            # Parse container and blob name from path
            parts = blob_path.split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid blob path: {blob_path}")

            container, blob_name = parts

            blob_client = self.blob_service_client.get_blob_client(
                container=container,
                blob=blob_name
            )

            return blob_client.download_blob().readall()

        except ResourceNotFoundError:
            logger.error(f"Blob not found: {blob_path}")
            raise
        except Exception as e:
            logger.error(f"Error downloading file from blob storage: {e}")
            raise

    def delete_file(self, blob_path: str) -> bool:
        """
        Delete file from blob storage

        Args:
            blob_path: Full path (container/blob_name)

        Returns:
            bool: True if deleted, False if not found
        """
        try:
            parts = blob_path.split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid blob path: {blob_path}")

            container, blob_name = parts

            blob_client = self.blob_service_client.get_blob_client(
                container=container,
                blob=blob_name
            )

            blob_client.delete_blob()
            logger.info(f"Deleted blob: {blob_path}")
            return True

        except ResourceNotFoundError:
            logger.warning(f"Blob not found for deletion: {blob_path}")
            return False
        except Exception as e:
            logger.error(f"Error deleting blob: {e}")
            raise

    def get_blob_url(self, blob_path: str, expiry_hours: int = 24) -> str:
        """
        Generate a temporary SAS URL for blob access

        Args:
            blob_path: Full path (container/blob_name)
            expiry_hours: Hours until URL expires

        Returns:
            str: SAS URL
        """
        try:
            parts = blob_path.split("/", 1)
            if len(parts) != 2:
                raise ValueError(f"Invalid blob path: {blob_path}")

            container, blob_name = parts

            blob_client = self.blob_service_client.get_blob_client(
                container=container,
                blob=blob_name
            )

            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=blob_client.account_name,
                container_name=container,
                blob_name=blob_name,
                account_key=self._get_account_key(),
                permission=BlobSasPermissions(read=True),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )

            return f"{blob_client.url}?{sas_token}"

        except Exception as e:
            logger.error(f"Error generating SAS URL: {e}")
            raise

    def _get_account_key(self) -> str:
        """Extract account key from connection string"""
        parts = dict(part.split("=", 1) for part in self.connection_string.split(";") if "=" in part)
        return parts.get("AccountKey", "")

    def list_blobs(self, container_name: Optional[str] = None, prefix: Optional[str] = None) -> list:
        """
        List blobs in container

        Args:
            container_name: Container name (uses default if not specified)
            prefix: Optional prefix filter

        Returns:
            list: List of blob names
        """
        container = container_name or self.default_container

        try:
            container_client = self.blob_service_client.get_container_client(container)
            blobs = container_client.list_blobs(name_starts_with=prefix)
            return [blob.name for blob in blobs]

        except Exception as e:
            logger.error(f"Error listing blobs: {e}")
            raise

    def delete_old_files(self, days: int = 180, container_name: Optional[str] = None):
        """
        Delete files older than specified days (for 6-month retention policy)

        Args:
            days: Age threshold in days (default 180 = 6 months)
            container_name: Container name (uses default if not specified)
        """
        container = container_name or self.default_container
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        try:
            container_client = self.blob_service_client.get_container_client(container)
            deleted_count = 0

            for blob in container_client.list_blobs():
                if blob.creation_time < cutoff_date:
                    blob_client = container_client.get_blob_client(blob.name)
                    blob_client.delete_blob()
                    deleted_count += 1

            logger.info(f"Deleted {deleted_count} blobs older than {days} days")
            return deleted_count

        except Exception as e:
            logger.error(f"Error deleting old files: {e}")
            raise


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

if __name__ == "__main__":
    # Initialize service
    connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    blob_service = BlobStorageService(connection_string)

    # Upload file
    with open("test.pdf", "rb") as f:
        blob_path = blob_service.upload_file(
            f,
            "2025-01/test_upload/test.pdf",
            content_type="application/pdf",
            metadata={"upload_id": "12345"}
        )

    # Download file
    content = blob_service.download_file(blob_path)

    # Get temporary URL
    url = blob_service.get_blob_url(blob_path, expiry_hours=1)

    # List blobs
    blobs = blob_service.list_blobs(prefix="2025-01")

    # Delete file
    blob_service.delete_file(blob_path)
