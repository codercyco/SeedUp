#!/usr/bin/env python3
"""
Main entry point for torrent downloader with optional Google Drive upload.
Combines torrent downloading and cloud storage capabilities.
"""

import sys
import argparse
import os
from pathlib import Path

from torrent_downloader import download_torrent, get_download_status, clear_session
#from gdrive_uploader import upload_to_google_drive, PatternMatcher, ProgressTracker
from config import ConfigManager, TORRENT_DOWNLOAD_PATH, get_logger

logger = get_logger(__name__)


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Download torrents and optionally upload to Google Drive',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download torrent only
  python main.py download -t movie.torrent
  python main.py download -t "magnet:?xt=urn:btih:..."
  
  # Download and upload to Google Drive
  python main.py download -t movie.torrent --upload -f FOLDER_ID
  
  # Upload existing files to Google Drive
  python main.py upload -p /path/to/folder -f FOLDER_ID
  
  # Upload with filters
  python main.py upload -p /path -f FOLDER_ID --include "*.mp4" --exclude "*.tmp"
  
  # Check for paused downloads
  python main.py status
  
  # Clear download session
  python main.py clear
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Download command
    download_parser = subparsers.add_parser('download', help='Download a torrent')
    download_parser.add_argument(
        '-t', '--torrent',
        type=str,
        required=True,
        help='Torrent file path or magnet link'
    )
    download_parser.add_argument(
        '-d', '--destination',
        type=str,
        default=TORRENT_DOWNLOAD_PATH,
        help=f'Download destination (default: {TORRENT_DOWNLOAD_PATH})'
    )
    download_parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Start fresh download (ignore previous session)'
    )
    download_parser.add_argument(
        '--upload',
        action='store_true',
        help='Upload to Google Drive after download'
    )
    download_parser.add_argument(
        '-f', '--folder-id',
        type=str,
        help='Google Drive folder ID (required with --upload)'
    )
    download_parser.add_argument(
        '--skip-existing',
        action='store_true',
        default=True,
        help='Skip files that already exist in Drive (default: True)'
    )
    download_parser.add_argument(
        '--parallel',
        action='store_true',
        help='Use parallel uploads for faster performance'
    )
    
    # Upload command
    upload_parser = subparsers.add_parser('upload', help='Upload files to Google Drive')
    upload_parser.add_argument(
        '-p', '--path',
        type=str,
        required=True,
        help='Local path to file or folder to upload'
    )
    upload_parser.add_argument(
        '-f', '--folder-id',
        type=str,
        required=True,
        help='Google Drive destination folder ID'
    )
    upload_parser.add_argument(
        '--no-skip',
        action='store_true',
        help='Force re-upload even if files exist'
    )
    upload_parser.add_argument(
        '--parallel',
        action='store_true',
        help='Enable parallel uploads for faster performance'
    )
    upload_parser.add_argument(
        '--include',
        type=str,
        action='append',
        help='Include only files matching pattern (can be used multiple times)'
    )
    upload_parser.add_argument(
        '--exclude',
        type=str,
        action='append',
        help='Exclude files matching pattern (can be used multiple times)'
    )
    upload_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview what would be uploaded without actually uploading'
    )
    upload_parser.add_argument(
        '--no-resume',
        action='store_true',
        help='Clear previous upload progress and start fresh'
    )
    
    # Status command
    subparsers.add_parser('status', help='Check download status')
    
    # Clear command
    subparsers.add_parser('clear', help='Clear download session')
    
    return parser.parse_args()


def handle_download(args):
    """Handle torrent download command."""
    print("="*60)
    print("TORRENT DOWNLOADER")
    print("="*60)
    
    # Check if upload is requested but folder ID is missing
    if args.upload and not args.folder_id:
        logger.error("--folder-id is required when using --upload")
        return 1
    
    # Download the torrent
    logger.info(f"Starting download: {args.torrent}")
    downloaded_path = download_torrent(
        args.torrent,
        download_path=args.destination,
        auto_resume=not args.no_resume
    )
    
    if not downloaded_path:
        logger.error("Download failed or was cancelled")
        return 1
    
    logger.info(f"Download completed: {downloaded_path}")
    
    # Upload to Google Drive if requested
    if args.upload:
        print("\n" + "="*60)
        print("UPLOADING TO GOOGLE DRIVE")
        print("="*60)
        
        results = upload_to_google_drive(
            downloaded_path,
            args.folder_id,
            skip_existing=args.skip_existing,
            parallel=args.parallel,
            use_progress=True
        )
        
        if results['failed']:
            logger.warning("Some files failed to upload")
            return 1
        
        logger.info("Upload completed successfully!")
    
    return 0


def handle_upload(args):
    """Handle Google Drive upload command."""
    print("="*60)
    print("GOOGLE DRIVE UPLOADER")
    print("="*60)
    
    # Clear progress if requested
    if args.no_resume:
        ProgressTracker().clear()
        logger.info("Previous upload progress cleared")
    
    # Setup pattern matcher if needed
    pattern_matcher = None
    if args.include or args.exclude:
        pattern_matcher = PatternMatcher(args.include, args.exclude)
    
    # Upload to Google Drive
    results = upload_to_google_drive(
        args.path,
        args.folder_id,
        skip_existing=not args.no_skip,
        parallel=args.parallel,
        include_patterns=args.include,
        exclude_patterns=args.exclude,
        dry_run=args.dry_run,
        use_progress=not args.no_resume
    )
    
    if results['failed']:
        logger.warning("Some files failed to upload")
        return 1
    
    logger.info(f"{'Dry run' if args.dry_run else 'Upload'} completed successfully!")
    return 0


def handle_status(args):
    """Handle status check command."""
    if get_download_status():
        print("✓ Found paused download session")
        print("  Run 'python main.py download -t <torrent>' to resume")
        return 0
    else:
        print("✗ No paused download session found")
        return 0


def handle_clear(args):
    """Handle clear session command."""
    if clear_session():
        print("✓ Download session cleared")
        return 0
    else:
        print("✗ Failed to clear session")
        return 1


def main():
    """Main entry point."""
    args = parse_arguments()
    
    # Show help if no command specified
    if not args.command:
        print("Error: No command specified\n")
        parse_arguments().print_help()
        return 1
    
    try:
        # Route to appropriate handler
        if args.command == 'download':
            return handle_download(args)
        elif args.command == 'upload':
            return handle_upload(args)
        elif args.command == 'status':
            return handle_status(args)
        elif args.command == 'clear':
            return handle_clear(args)
        else:
            logger.error(f"Unknown command: {args.command}")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
        if args.command == 'download':
            print("Download progress has been saved. Resume with the same command.")
        elif args.command == 'upload':
            print("Upload progress has been saved. Use the same command to resume.")
        return 130
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
