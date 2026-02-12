"""
Auto-updater for Quality Management System
Checks for updates and downloads new versions
"""
import requests
import json
import os
import sys
import tempfile
import subprocess
import platform
from pathlib import Path
from version import __version__, __update_url__, __download_url__


class Updater:
    """Handle application updates"""
    
    def __init__(self):
        self.current_version = __version__
        self.update_url = __update_url__
        self.download_url = __download_url__
        self.system = platform.system()
    
    def check_for_updates(self):
        """
        Check if a newer version is available
        
        Returns:
            dict: Update info with keys: available (bool), version (str), url (str), notes (str)
                  or None if check fails
        """
        try:
            # Request version info from server
            response = requests.get(self.update_url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                latest_version = data.get('version', '0.0.0')
                
                # Get platform-specific download URL
                if self.system == 'Windows':
                    platform_data = data.get('windows', {})
                elif self.system == 'Linux':
                    platform_data = data.get('linux', {})
                else:  # Darwin (macOS)
                    platform_data = data.get('macos', {})
                
                download_url = platform_data.get('url', data.get('download_url', ''))
                release_notes_url = data.get('release_notes_url', '')
                size_mb = platform_data.get('size_mb', 0)
                
                # Compare versions
                if self._is_newer_version(latest_version, self.current_version):
                    return {
                        'available': True,
                        'version': latest_version,
                        'url': download_url,
                        'notes': f'New version available: {latest_version}\nSize: ~{size_mb}MB\n\nRelease notes: {release_notes_url}',
                        'size_mb': size_mb
                    }
                else:
                    return {
                        'available': False,
                        'version': self.current_version,
                        'url': '',
                        'notes': 'You are running the latest version'
                    }
            else:
                return None
                
        except Exception as e:
            print(f"Update check failed: {e}")
            return None
    
    def _is_newer_version(self, latest, current):
        """
        Compare version strings (semantic versioning: MAJOR.MINOR.PATCH)
        
        Args:
            latest: Latest version string
            current: Current version string
            
        Returns:
            bool: True if latest is newer than current
        """
        try:
            latest_parts = [int(x) for x in latest.split('.')]
            current_parts = [int(x) for x in current.split('.')]
            
            # Pad to same length
            while len(latest_parts) < 3:
                latest_parts.append(0)
            while len(current_parts) < 3:
                current_parts.append(0)
            
            # Compare major.minor.patch
            for i in range(3):
                if latest_parts[i] > current_parts[i]:
                    return True
                elif latest_parts[i] < current_parts[i]:
                    return False
            
            return False  # Versions are equal
            
        except:
            return False
    
    def download_update(self, download_url, progress_callback=None):
        """
        Download update file
        
        Args:
            download_url: URL to download from
            progress_callback: Optional callback function(bytes_downloaded, total_bytes)
            
        Returns:
            str: Path to downloaded file, or None if failed
        """
        try:
            # Determine file extension based on platform
            if self.system == 'Windows':
                ext = '.exe'
            elif self.system == 'Linux':
                ext = '.AppImage'
            else:  # Darwin (macOS)
                ext = '.dmg'
            
            # Create temp file
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f"QMS_Update{ext}")
            
            # Download with progress
            response = requests.get(download_url, stream=True, timeout=30)
            total_size = int(response.headers.get('content-length', 0))
            
            downloaded = 0
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded, total_size)
            
            return temp_file
            
        except Exception as e:
            print(f"Download failed: {e}")
            return None
    
    def install_update(self, installer_path):
        """
        Install the downloaded update
        
        Args:
            installer_path: Path to installer file
            
        Returns:
            bool: True if install initiated successfully
        """
        try:
            if self.system == 'Windows':
                # Run installer and exit current app
                subprocess.Popen([installer_path])
                return True
                
            elif self.system == 'Linux':
                # Make AppImage executable
                os.chmod(installer_path, 0o755)
                # Run it
                subprocess.Popen([installer_path])
                return True
                
            else:  # macOS
                # Open DMG
                subprocess.Popen(['open', installer_path])
                return True
                
        except Exception as e:
            print(f"Install failed: {e}")
            return False


def check_for_updates_silent():
    """
    Silently check for updates (no UI)
    
    Returns:
        dict: Update info or None
    """
    updater = Updater()
    return updater.check_for_updates()
