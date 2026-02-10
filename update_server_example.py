#!/usr/bin/env python3
"""
Simple Update Server Example
This is a basic Flask server that provides version information for auto-updates.

To run:
    pip install flask
    python update_server.py

Then set in version.py:
    __update_url__ = "http://localhost:5000/api/version"
"""

from flask import Flask, jsonify, send_file
import os

app = Flask(__name__)

# Current version information
VERSION_INFO = {
    "version": "1.0.1",  # Change this to your latest version
    "build": "20260211",
    "download_url": "http://localhost:5000/downloads/QMS-1.0.1",  # Will auto-detect platform
    "notes": """New in version 1.0.1:
• Fixed image attachment display in PDF reports
• Improved audit logging system
• Enhanced notification system
• Performance improvements
• Bug fixes"""
}

@app.route('/api/version', methods=['GET'])
def get_version():
    """Return version information"""
    return jsonify(VERSION_INFO)

@app.route('/downloads/<filename>', methods=['GET'])
def download_file(filename):
    """
    Serve download files
    
    In production, you would check the user's platform and serve the appropriate file:
    - Linux: .AppImage
    - Windows: .exe or installer
    - macOS: .dmg
    """
    # Example: check if file exists in downloads folder
    downloads_dir = os.path.join(os.path.dirname(__file__), 'downloads')
    
    if not os.path.exists(downloads_dir):
        return jsonify({"error": "Downloads directory not found"}), 404
    
    # In production, implement platform detection and file serving
    files = os.listdir(downloads_dir)
    for file in files:
        if filename in file:
            filepath = os.path.join(downloads_dir, file)
            return send_file(filepath, as_attachment=True)
    
    return jsonify({"error": "File not found"}), 404

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "QMS Update Server"})

if __name__ == '__main__':
    print("=" * 50)
    print("QMS Update Server")
    print("=" * 50)
    print(f"Version API: http://localhost:5000/api/version")
    print(f"Download: http://localhost:5000/downloads/<filename>")
    print()
    print(f"Current version: {VERSION_INFO['version']}")
    print()
    print("Note: Create a 'downloads' folder and place your")
    print("      build files there for distribution.")
    print("=" * 50)
    
    # Run server
    app.run(host='0.0.0.0', port=5000, debug=True)
