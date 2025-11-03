"""
Torrent downloader module using libtorrent with resume capability.
"""

import libtorrent as lt
import time
import os
import sys
from tqdm import tqdm
from config import TORRENT_SESSION_FILE, TORRENT_DOWNLOAD_PATH, get_logger

logger = get_logger(__name__)

# Check if running in Google Colab
try:
    from google.colab import files
    IN_COLAB = True
except ImportError:
    IN_COLAB = False


def save_session(session, session_file=TORRENT_SESSION_FILE):
    """Save session state to resume later (correctly saves binary data)."""
    try:
        with open(session_file, "wb") as f:
            session_state = session.save_state()
            f.write(lt.bencode(session_state))
        logger.debug(f"Session saved to {session_file}")
    except Exception as e:
        logger.error(f"Failed to save session: {e}")


def load_session(session_file=TORRENT_SESSION_FILE):
    """Load session state if exists, otherwise return a new session."""
    if os.path.exists(session_file):
        try:
            with open(session_file, "rb") as f:
                session_data = f.read()
                if not session_data:
                    raise ValueError("Session file is empty.")
                
                session_state = lt.bdecode(session_data)
                ses = lt.session()
                ses.load_state(session_state)
                logger.info(f"Session loaded from {session_file}")
                return ses
        except (RuntimeError, ValueError) as e:
            logger.warning(f"Failed to load session ({e}). Starting fresh.")
            os.remove(session_file)
    
    return lt.session()


def download_torrent(source, download_path=TORRENT_DOWNLOAD_PATH, 
                    session_file=TORRENT_SESSION_FILE, auto_resume=True):
    """
    Download a torrent file using libtorrent, with support for stopping/resuming.
    
    :param source: .torrent file path or magnet link.
    :param download_path: Directory to save the downloaded content.
    :param session_file: File to save/load session state.
    :param auto_resume: Automatically load previous session if available.
    :return: Path to downloaded content or None on failure.
    """
    if not os.path.exists(download_path):
        os.makedirs(download_path)
        logger.info(f"Created download directory: {download_path}")

    # Load existing session or create new one
    ses = load_session(session_file) if auto_resume else lt.session()

    # Apply necessary settings
    settings = {
        'listen_interfaces': '0.0.0.0:6881',
    }
    ses.apply_settings(settings)

    # Initialize add_torrent_params
    params = lt.add_torrent_params()
    params.save_path = download_path
    params.storage_mode = lt.storage_mode_t.storage_mode_sparse

    # Handle magnet link or .torrent file
    if source.startswith("magnet:"):
        params.url = source
        logger.info(f"Adding magnet link: {source[:60]}...")
    elif source.endswith(".torrent"):
        if not os.path.exists(source):
            logger.error(f"Torrent file not found: {source}")
            return None
        
        try:
            with open(source, "rb") as f:
                torrent_data = lt.bdecode(f.read())
                info = lt.torrent_info(torrent_data)
                params.ti = info
            logger.info(f"Adding torrent file: {source}")
        except Exception as e:
            logger.error(f"Failed to read torrent file: {e}")
            return None
    else:
        logger.error("Invalid source. Provide a .torrent file or magnet link.")
        return None

    # Add the torrent to the session
    try:
        handle = ses.add_torrent(params)
        logger.info(f"Downloading to: {download_path}")
    except Exception as e:
        logger.error(f"Failed to add torrent: {e}")
        return None

    # Wait for metadata
    logger.info("Waiting for metadata...")
    while not handle.status().has_metadata:
        time.sleep(1)

    torrent_name = handle.status().name
    logger.info(f"Downloading: {torrent_name}")

    # Initialize progress bar
    with tqdm(total=100, desc="Download Progress", unit="%",
              bar_format="{l_bar}{bar} {n:.1f}/{total_fmt}% [{postfix}]", 
              ncols=120) as pbar:
        try:
            while handle.status().state != lt.torrent_status.seeding:
                s = handle.status()
                progress = s.progress * 100

                # Calculate ETA
                eta_str = "N/A"
                if s.download_rate > 0:
                    total_size = s.total_wanted
                    downloaded = s.total_done
                    remaining = total_size - downloaded
                    eta_seconds = remaining / s.download_rate
                    
                    if eta_seconds < 60:
                        eta_str = f"{int(eta_seconds)}s"
                    elif eta_seconds < 3600:
                        eta_str = f"{int(eta_seconds / 60)}m {int(eta_seconds % 60)}s"
                    else:
                        hours = int(eta_seconds / 3600)
                        minutes = int((eta_seconds % 3600) / 60)
                        eta_str = f"{hours}h {minutes}m"

                # Format download speed
                if s.download_rate > 1024 * 1024:  # > 1 MB/s
                    speed_str = f"{s.download_rate / (1024 * 1024):.2f} MB/s"
                else:
                    speed_str = f"{s.download_rate / 1024:.2f} KB/s"

                # Update progress bar
                pbar.n = progress
                pbar.set_postfix({
                    "Seeds": s.num_seeds,
                    "Peers": s.num_peers - s.num_seeds,
                    "Speed": speed_str,
                    "ETA": eta_str
                })
                pbar.refresh()

                # Save session periodically (every 10 seconds)
                if int(time.time()) % 10 == 0:
                    save_session(ses, session_file)
                
                time.sleep(1)

        except KeyboardInterrupt:
            logger.warning("Download paused by user. Session saved for resume.")
            save_session(ses, session_file)
            return None

    logger.info("Download complete!")
    
    # Clean up session file on successful completion
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
            logger.debug("Session file removed after successful download")
        except Exception as e:
            logger.warning(f"Could not remove session file: {e}")
    
    # Return the path to downloaded content
    downloaded_path = os.path.join(download_path, torrent_name)
    return downloaded_path


def get_download_status(session_file=TORRENT_SESSION_FILE):
    """
    Check if there's a paused download that can be resumed.
    
    :return: True if a session file exists, False otherwise.
    """
    return os.path.exists(session_file)


def clear_session(session_file=TORRENT_SESSION_FILE):
    """
    Clear the session file to start fresh.
    
    :return: True if cleared successfully, False otherwise.
    """
    if os.path.exists(session_file):
        try:
            os.remove(session_file)
            logger.info("Session file cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
            return False
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python torrent_downloader.py <torrent_file/magnet_link>")
        sys.exit(1)

    source = sys.argv[1]
    result = download_torrent(source)
    
    if result:
        print(f"\nDownloaded to: {result}")
        sys.exit(0)
    else:
        sys.exit(1)
