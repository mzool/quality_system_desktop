"""
Version information for Quality Management System
"""

__version__ = "1.0.4"
__build__ = "20260210"
__app_name__ = "Quality Management System"
__author__ = "Mohammad Basem"

# Update URLs - Configure after setting up GitHub Actions
# Option 1: GitHub Pages (recommended)
#   1. Push release tag: git tag v1.0.0 && git push origin v1.0.0
#   2. Download update_info.json from Actions artifacts
#   3. Create gh-pages branch and add update_info.json
#   4. Enable GitHub Pages in repository settings
#   5. Use: https://YOUR_USERNAME.github.io/YOUR_REPO/update_info.json
#
# Option 2: GitHub Releases
#   Use: https://github.com/YOUR_USERNAME/YOUR_REPO/releases/latest/download/update_info.json
#
__update_url__ = "https://raw.githubusercontent.com/mzool/quality_system_desktop/main/update_info.json"
__download_url__ = "https://github.com/mzool/quality_system_desktop/releases/latest/download"

def get_version():
    """Get current version string"""
    return __version__

def get_version_info():
    """Get full version information"""
    return {
        "version": __version__,
        "build": __build__,
        "app_name": __app_name__,
        "author": __author__
    }
