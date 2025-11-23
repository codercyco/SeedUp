"""
SeedUp - Smart Torrent Management Tool
Simplified Google Drive uploader module for Colab environments.
Based on direct Drive API usage with resumable uploads and progress tracking.

Copyright 2025 Ishara Deshapriya

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

This module automatically handles authentication in Google Colab environments.
No manual service setup required - just run your upload commands directly.
"""

import os
import mimetypes
from typing import Dict, List, Optional
from tqdm import tqdm
import logging

# Suppress Google Cloud warnings
logging.getLogger('google.auth._default').setLevel(logging.ERROR)
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)
os.environ['GOOGLE_CLOUD_PROJECT'] = 'dummy-project'
import warnings
warnings.filterwarnings("ignore", message="No project ID could be determined")
warnings.filterwarnings("ignore", message="file_cache is only supported with oauth2client")

from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from config import get_logger

logger = get_logger(__name__)
# Suppress INFO level logging to reduce verbose output
logger.setLevel(logging.WARNING)

# Check if running in Google Colab
try:
    from google.colab import auth
    from googleapiclient.discovery import build
    IN_COLAB = True
    logger.info("Running in Google Colab environment")
except ImportError:
    IN_COLAB = False
    logger.warning("Not running in Google Colab - upload features unavailable")

def get_drive_service():
    """
    Get authenticated Google Drive service.
    
    Returns:
        Google Drive service object
        
    Raises:
        RuntimeError: If not in Colab or authentication fails
    """
    if not IN_COLAB:
        raise RuntimeError("Not running in Google Colab environment")
    
    try:
        # Suppress warnings during authentication
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            # Authenticate and build service directly like your working script
            auth.authenticate_user()
            drive_service = build('drive', 'v3')
            return drive_service
    except Exception as e:
        raise RuntimeError(f"Failed to authenticate Google Drive: {str(e)}")


# For backward compatibility - these functions are no longer needed but kept for existing code
def set_drive_service(service):
    """Legacy function - no longer needed with automatic authentication."""
    logger.info("Drive service set (using automatic authentication)")

class SimpleDriveUploader:
    """Simplified Google Drive uploader with progress bars and skip existing feature."""
    
    def __init__(self, skip_existing: bool = True):
        """
        Initialize the uploader with automatic authentication.
        
        Args:
            skip_existing: If True, skip files that already exist in Drive
            
        Raises:
            RuntimeError: If not in Colab or authentication fails
        """
        self.drive_service = get_drive_service()
        self.skip_existing = skip_existing
    
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
            
            # Upload without individual progress bar
            response = None
            while response is None:
                status, response = request.next_chunk()
            
            file_id = response.get('id')
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
        parent_id: str,
        _progress_bar=None,
        _total_size=None,
        _uploaded_size=[0],
        _file_count=[0, 0]  # [current, total]
    ) -> Dict[str, any]:
        """
        Upload a file or folder to Google Drive recursively.
        
        Args:
            local_path: Path to the local file or folder
            parent_id: Google Drive folder ID where content will be uploaded
            
        Returns:
            Dictionary with 'success', 'failed', 'skipped' lists and 'root_folder_id'
        """
        results = {'success': [], 'failed': [], 'skipped': [], 'root_folder_id': parent_id}
        
        # Validate path
        if not os.path.exists(local_path):
            results['failed'].append(local_path)
            return results
        
        # Initialize progress tracking on first call
        if _progress_bar is None:
            stats = self.count_items(local_path)
            _total_size = stats['total_size']
            _file_count[1] = stats['files']  # total files
            _uploaded_size[0] = 0
            _file_count[0] = 0  # current file count
            
            size_mb = _total_size / (1024 * 1024)
            print(f"📤 Uploading {stats['files']} files ({size_mb:.1f} MB)")
            _progress_bar = tqdm(
                total=_total_size,
                unit='B',
                unit_scale=True,
                unit_divisor=1024,
                desc="Upload",
                bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{rate_fmt}] {postfix}",
                disable=False,
                leave=True,
                ncols=100
            )
        
        # Upload file
        if os.path.isfile(local_path):
            file_name = os.path.basename(local_path)
            file_size = os.path.getsize(local_path)
            existing = self.file_exists(file_name, parent_id) if self.skip_existing else None
            
            if existing:
                results['skipped'].append(local_path)
                # Update progress even for skipped files
                if _progress_bar:
                    _uploaded_size[0] += file_size
                    _file_count[0] += 1
                    _progress_bar.set_postfix_str(f"Files: {_file_count[0]}/{_file_count[1]}")
                    _progress_bar.update(file_size)
            else:
                file_id = self.upload_file(local_path, parent_id)
                if file_id:
                    results['success'].append(local_path)
                else:
                    results['failed'].append(local_path)
                
                # Update progress after upload
                if _progress_bar:
                    _uploaded_size[0] += file_size
                    _file_count[0] += 1
                    _progress_bar.set_postfix_str(f"Files: {_file_count[0]}/{_file_count[1]}")
                    _progress_bar.update(file_size)
                
            return results
        
        # Upload directory
        if os.path.isdir(local_path):
            folder_name = os.path.basename(local_path)
            folder_id = self.create_folder(folder_name, parent_id)
            
            if folder_id:
                # Store the created folder ID as root folder for this upload
                results['root_folder_id'] = folder_id
                
                # Recursively upload all items in the folder
                try:
                    for item in os.listdir(local_path):
                        item_path = os.path.join(local_path, item)
                        sub_results = self.upload_to_drive(item_path, folder_id, _progress_bar, _total_size, _uploaded_size, _file_count)
                        results['success'].extend(sub_results['success'])
                        results['failed'].extend(sub_results['failed'])
                        results['skipped'].extend(sub_results['skipped'])
                except Exception as e:
                    results['failed'].append(local_path)
            else:
                results['failed'].append(local_path)
            
            # Close progress bar if this is the root call and we're done
            if _progress_bar and _file_count[0] >= _file_count[1]:
                _progress_bar.close()
                print()  # Add newline after progress bar
                
            return results
        
        # Close progress bar if this is the root call
        if _progress_bar and _file_count[0] >= _file_count[1]:
            _progress_bar.close()
            print()  # Add newline after progress bar
        
        results['failed'].append(local_path)
        return results
    
    def print_summary(self, results: Dict[str, List[str]], root_folder_id: str = None):
        """Print clean upload summary with folder link."""
        print("\n" + "="*60)
        print("🎉 UPLOAD COMPLETE")
        print("="*60)
        
        total_files = len(results['success']) + len(results.get('skipped', []))
        print(f"✅ {len(results['success'])} files uploaded successfully")
        
        if results.get('skipped'):
            print(f"⏭️  {len(results['skipped'])} files skipped (already exist)")
        
        if results['failed']:
            print(f"❌ {len(results['failed'])} files failed")
        
        if root_folder_id:
            folder_url = f"https://drive.google.com/drive/folders/{root_folder_id}"
            print(f"\n📁 View uploaded files: {folder_url}")
        
        print("="*60)


def upload_to_google_drive(local_path: str, folder_id: str, **kwargs):
    """
    Upload files to Google Drive with automatic authentication.
    
    Args:
        local_path: Path to file or folder to upload
        folder_id: Google Drive destination folder ID
        **kwargs: Additional options:
            - skip_existing (bool): Skip files that already exist (default: True)
        
    Returns:
        Dictionary with 'success', 'failed', and 'skipped' lists
        
    Raises:
        RuntimeError: If not in Colab or authentication fails
    """
    skip_existing = kwargs.get('skip_existing', True)
    
    uploader = SimpleDriveUploader(skip_existing=skip_existing)
    results = uploader.upload_to_drive(local_path, folder_id)
    
    # Get the root folder ID for the summary link
    root_folder_id = results.get('root_folder_id', folder_id)
    uploader.print_summary(results, root_folder_id)
    
    return results