"""
SeedUp - Smart Torrent Management Tool
Shared configuration and constants for the torrent downloader and drive uploader.

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
"""

import os
import json
import logging

# Torrent Downloader Configuration
TORRENT_SESSION_FILE = "torrent_session.json"
TORRENT_DOWNLOAD_PATH = "../SeedUp Downloads"

# Google Drive Uploader Configuration
CHUNK_SIZE = 100 * 1024 * 1024  # 100MB chunks for large files
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds base delay for exponential backoff
LARGE_FILE_THRESHOLD = 1024 * 1024 * 1024  # 1GB
MAX_WORKERS = 3  # Number of parallel uploads
PROGRESS_FILE = '.gdrive_upload_progress.json'
CONFIG_FILE = '.gdrive-uploader.conf'
TOKEN_FILE = 'token.pickle'
CREDENTIALS_FILE = 'credentials.dat'
GOOGLE_DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def get_logger(name):
    """Get a logger instance."""
    return logging.getLogger(name)


class ConfigManager:
    """Manage configuration file for storing default settings."""
    
    @staticmethod
    def load_config(config_path: str = CONFIG_FILE) -> dict:
        """Load configuration from file."""
        logger = get_logger(__name__)
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}")
        return {}
    
    @staticmethod
    def save_config(config: dict, config_path: str = CONFIG_FILE):
        """Save configuration to file."""
        logger = get_logger(__name__)
        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
            logger.info(f"Configuration saved to {config_path}")
        except Exception as e:
            logger.error(f"Could not save config file: {e}")
