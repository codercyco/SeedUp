"""
Simplified Google Drive uploader module for Colab environments.
Based on direct Drive API usage with resumable uploads and progress tracking.

NOTE: This module requires a pre-authenticated Google Drive service.
Run this in a Colab notebook cell BEFORE using this module:

    from google.colab import auth
    from googleapiclient.discovery import build
    auth.authenticate_user()
    drive_service = build('drive', 'v3')
    
    from gdrive_uploader import set_drive_service
    set_drive_service(drive_service)
"""

import os
import mimetypes
from typing import Dict, List, Optional
from tqdm import tqdm

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import get_logger

logger = get_logger(__name__)

# Global variable to store pre-authenticated service
_DRIVE_SERVICE = None
_ERROR_SHOWN = False

# Environment check at module level
try:
    from google.colab import auth
    IN_COLAB = True
    logger.info("Running in Google Colab environment")
except ImportError:
    IN_COLAB = False
    logger.warning("Not running in Google Colab - upload features unavailable")


def set_drive_service(service):
    """
    Set a pre-authenticated Google Drive service.
    
    This should be called from the notebook cell before using any upload functions.
    
    Args:
        service: Authenticated Google Drive service object
    """
    global _DRIVE_SERVICE, _ERROR_SHOWN
    _DRIVE_SERVICE = service
    _ERROR_SHOWN = False  # Reset error flag when service is set
    logger.info("Pre-authenticated Drive service registered")


def get_drive_service():
    """
    Get the pre-authenticated Google Drive service.
    
    Returns:
        Google Drive service object
        
    Raises:
        RuntimeError: If not in Colab or service has not been set
    """
    # First check if we're in Colab
    if not IN_COLAB:
        error_msg = (
            "\n" + "="*60 + "\n"
            "ERROR: Not running in Google Colab environment!\n"
            "="*60 + "\n"
            "Google Drive upload is only supported in Google Colab.\n"
            "Please run this script in Colab to use upload features.\n"
            + "="*60
        )
        raise RuntimeError(error_msg)
    
    # Then check if service was initialized
    if _DRIVE_SERVICE is None:
        global _ERROR_SHOWN
        if not _ERROR_SHOWN:
            _ERROR_SHOWN = True
            error_msg = (
                "\n" + "="*60 + "\n"
                "ERROR: Google Drive service not initialized!\n"
                "="*60 + "\n"
                "You must authenticate in a Colab notebook cell BEFORE running this command.\n\n"
                "Run this in a notebook cell:\n\n"
                "  from google.colab import auth\n"
                "  from googleapiclient.discovery import build\n"
                "  auth.authenticate_user()\n"
                "  drive_service = build('drive', 'v3')\n\n"
                "  from gdrive_uploader import set_drive_service\n"
                "  set_drive_service(drive_service)\n"
                "  print('✓ Ready to upload!')\n\n"
                "Then run your command:\n\n"
                "  !python main.py upload -p '/path/to/files' -f 'FOLDER_ID'\n"
                + "="*60
            )
            raise RuntimeError(error_msg)
        else:
            # Just raise a simple error on subsequent calls
            raise RuntimeError("Google Drive service not initialized")
    
    return _DRIVE_SERVICE


class SimpleDriveUploader:
    """Simplified Google Drive uploader with progress bars and skip existing feature."""
    
    def __init__(self, skip_existing: bool = True, drive_service=None):
        """
        Initialize the uploader.
        
        Args:
            skip_existing: If True, skip files that already exist in Drive
            drive_service: Pre-authenticated Google Drive service (optional)
            
        Raises:
            RuntimeError: If not in Colab or service not available
        """
        if drive_service is not None:
            self.drive_service = drive_service
        else:
            # This will raise RuntimeError with clear message if not set up
            try:
                self.drive_service = get_drive_service()
            except RuntimeError as e:
                # Re-raise the error without creating multiple instances
                raise e
        
        self.skip_existing = skip_existing
        logger.info("Successfully initialized with Google Drive service")
    
    def file_exists(self, file_name: str, parent_id: str) -> Optional[Dict]:
        """
        Check if a file with the given name already exists in the parent folder.
        
        Args:
            file_name: Name of the file to check
            parent_id: Parent folder ID
            
        Returns:
            File info dict if exists, None otherwise
        """
        try:
            # Escape single quotes in filename for query
            escaped_name = file_name.replace("'", "\\'")
            query = f"name='{escaped_name}' and '{parent_id}' in parents and trashed=false"
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name, size, mimeType)',
                pageSize=1
            ).execute()
            
            files = results.get('files', [])
            if files:
                return files[0]
            return None
            
        except HttpError as e:
            logger.error(f"Error checking if file exists: {str(e)}")
            return None
    
    def folder_exists(self, folder_name: str, parent_id: str) -> Optional[str]:
        """
        Check if a folder with the given name already exists in the parent folder.
        
        Args:
            folder_name: Name of the folder to check
            parent_id: Parent folder ID
            
        Returns:
            Folder ID if exists, None otherwise
        """
        try:
            # Escape single quotes in folder name for query
            escaped_name = folder_name.replace("'", "\\'")
            query = (f"name='{escaped_name}' and '{parent_id}' in parents "
                    f"and mimeType='application/vnd.google-apps.folder' and trashed=false")
            
            results = self.drive_service.files().list(
                q=query,
                fields='files(id, name)',
                pageSize=1
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                return folders[0]['id']
            return None
            
        except HttpError as e:
            logger.error(f"Error checking if folder exists: {str(e)}")
            return None
    
    def upload_file(self, local_path: str, parent_id: str) -> Optional[str]:
        """
        Upload a single file to Google Drive with progress bar.
        
        Args:
            local_path: Path to the local file
            parent_id: Google Drive folder ID where file will be uploaded
            
        Returns:
            File ID if successful, None otherwise
        """
        file_name = os.path.basename(local_path)
        
        # Check if file already exists
        if self.skip_existing:
            existing = self.file_exists(file_name, parent_id)
            if existing:
                logger.info(f"Skipping '{file_name}' - already exists in Drive")
                return existing['id']
        
        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(local_path)
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        # Prepare file metadata
        file_metadata = {'name': file_name, 'parents': [parent_id]}
        
        try:
            # Create resumable upload
            media = MediaFileUpload(
                local_path,
                mimetype=mime_type,
                resumable=True
            )
            request = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            )
            
            # Upload with progress bar
            total_size = os.path.getsize(local_path)
            with tqdm(
                total=total_size,
                unit='B',
                unit_scale=True,
                desc=f"Uploading {file_name}"
            ) as pbar:
                response = None
                previous_uploaded = 0
                
                while response is None:
                    status, response = request.next_chunk()
                    if status:
                        uploaded = status.resumable_progress
                        pbar.update(uploaded - previous_uploaded)
                        previous_uploaded = uploaded
                
                # Ensure progress bar reaches 100%
                if previous_uploaded < total_size:
                    pbar.update(total_size - previous_uploaded)
            
            file_id = response.get('id')
            logger.info(f"Successfully uploaded '{file_name}' (ID: {file_id})")
            return file_id
            
        except HttpError as e:
            logger.error(f"HTTP error uploading '{file_name}': {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error uploading '{file_name}': {str(e)}")
            return None
    
    def create_folder(self, folder_name: str, parent_id: str) -> Optional[str]:
        """
        Create a folder in Google Drive or return existing folder ID.
        
        Args:
            folder_name: Name of the folder to create
            parent_id: Parent folder ID
            
        Returns:
            Folder ID if successful, None otherwise
        """
        # Check if folder already exists
        if self.skip_existing:
            existing_id = self.folder_exists(folder_name, parent_id)
            if existing_id:
                logger.info(f"Folder '{folder_name}' already exists (ID: {existing_id})")
                return existing_id
        
        try:
            folder_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            folder_id = folder.get('id')
            logger.info(f"Created folder '{folder_name}' (ID: {folder_id})")
            return folder_id
        except Exception as e:
            logger.error(f"Error creating folder '{folder_name}': {str(e)}")
            return None
    
    def count_items(self, local_path: str) -> Dict[str, int]:
        """
        Count total files and folders in the path.
        
        Args:
            local_path: Path to count items from
            
        Returns:
            Dictionary with files, folders, and total_size counts
        """
        if os.path.isfile(local_path):
            return {
                'files': 1,
                'folders': 0,
                'total_size': os.path.getsize(local_path)
            }
        
        files = 0
        folders = 0
        total_size = 0
        
        try:
            for root, dirs, filenames in os.walk(local_path):
                folders += len(dirs)
                files += len(filenames)
                
                for filename in filenames:
                    try:
                        file_path = os.path.join(root, filename)
                        total_size += os.path.getsize(file_path)
                    except OSError:
                        pass
        except Exception as e:
            logger.error(f"Error counting items: {str(e)}")
        
        return {'files': files, 'folders': folders, 'total_size': total_size}
    
    def upload_to_drive(
        self,
        local_path: str,
        parent_id: str
    ) -> Dict[str, List[str]]:
        """
        Upload a file or folder to Google Drive recursively.
        
        Args:
            local_path: Path to the local file or folder
            parent_id: Google Drive folder ID where content will be uploaded
            
        Returns:
            Dictionary with 'success', 'failed', and 'skipped' lists of paths
        """
        results = {'success': [], 'failed': [], 'skipped': []}
        
        # Validate path
        if not os.path.exists(local_path):
            logger.error(f"Path does not exist: {local_path}")
            results['failed'].append(local_path)
            return results
        
        # Show statistics
        stats = self.count_items(local_path)
        logger.info(f"Total items to upload: {stats['files']} files, {stats['folders']} folders")
        logger.info(f"Total size: {stats['total_size'] / (1024**3):.2f} GB")
        
        # Upload file
        if os.path.isfile(local_path):
            file_name = os.path.basename(local_path)
            existing = self.file_exists(file_name, parent_id) if self.skip_existing else None
            
            if existing:
                results['skipped'].append(local_path)
            else:
                file_id = self.upload_file(local_path, parent_id)
                if file_id:
                    results['success'].append(local_path)
                else:
                    results['failed'].append(local_path)
            return results
        
        # Upload directory
        if os.path.isdir(local_path):
            folder_name = os.path.basename(local_path)
            folder_id = self.create_folder(folder_name, parent_id)
            
            if folder_id:
                # Recursively upload all items in the folder
                try:
                    for item in os.listdir(local_path):
                        item_path = os.path.join(local_path, item)
                        sub_results = self.upload_to_drive(item_path, folder_id)
                        results['success'].extend(sub_results['success'])
                        results['failed'].extend(sub_results['failed'])
                        results['skipped'].extend(sub_results['skipped'])
                except Exception as e:
                    logger.error(f"Error processing folder '{local_path}': {str(e)}")
                    results['failed'].append(local_path)
            else:
                results['failed'].append(local_path)
            
            return results
        
        logger.error(f"Path '{local_path}' is neither a file nor a directory")
        results['failed'].append(local_path)
        return results
    
    def print_summary(self, results: Dict[str, List[str]]):
        """Print upload summary."""
        print("\n" + "="*60)
        print("UPLOAD SUMMARY")
        print("="*60)
        print(f"Successful uploads: {len(results['success'])}")
        print(f"Skipped (already exist): {len(results.get('skipped', []))}")
        print(f"Failed uploads: {len(results['failed'])}")
        
        if results['failed']:
            print("\nFailed items:")
            for item in results['failed'][:10]:
                print(f"  - {item}")
            if len(results['failed']) > 10:
                print(f"  ... and {len(results['failed']) - 10} more")
        print("="*60)


def upload_to_google_drive(local_path: str, folder_id: str, **kwargs):
    """
    Convenience function to upload files to Google Drive.
    
    Args:
        local_path: Path to file or folder to upload
        folder_id: Google Drive destination folder ID
        **kwargs: Additional options:
            - skip_existing (bool): Skip files that already exist (default: True)
            - drive_service: Pre-authenticated Drive service (optional)
        
    Returns:
        Dictionary with 'success', 'failed', and 'skipped' lists
        
    Raises:
        RuntimeError: If not in Colab or service not initialized
    """
    skip_existing = kwargs.get('skip_existing', True)
    drive_service = kwargs.get('drive_service', None)
    
    try:
        uploader = SimpleDriveUploader(skip_existing=skip_existing, drive_service=drive_service)
    except RuntimeError as e:
        # Don't retry, just raise the error immediately
        raise e
    
    results = uploader.upload_to_drive(local_path, folder_id)
    uploader.print_summary(results)
    
    return results