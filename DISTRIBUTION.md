# Distribution Workflow for Quality Management System

## For Linux (AppImage)

### 1. Build AppImage
```bash
chmod +x build-linux.sh
./build-linux.sh
```

Output: `QualitySystem-1.0.0-x86_64.AppImage`

### 2. Test Locally
```bash
# Test the AppImage
chmod +x QualitySystem-1.0.0-x86_64.AppImage
./QualitySystem-1.0.0-x86_64.AppImage

# Test installation
./install-linux.sh
```

### 3. Create Release Package
```bash
chmod +x create-release.sh
./create-release.sh
```

Output:
- `releases/QualitySystem-1.0.0-Linux-x86_64/` - Folder with all files
- `releases/QualitySystem-1.0.0-Linux-x86_64.tar.gz` - Linux distribution
- `releases/QualitySystem-1.0.0-Linux-x86_64.zip` - Alternative format

### 4. Upload to GitHub Releases

```bash
# Using GitHub CLI (gh)
gh release create v1.0.0 \
  releases/QualitySystem-1.0.0-Linux-x86_64.tar.gz \
  releases/QualitySystem-1.0.0-Linux-x86_64.zip \
  --title "Version 1.0.0" \
  --notes "See releases/QualitySystem-1.0.0-Linux-x86_64/RELEASE_NOTES.txt"
```

Or manually:
1. Go to GitHub → Releases → Create new release
2. Tag: `v1.0.0`
3. Upload `QualitySystem-1.0.0-Linux-x86_64.tar.gz`
4. Upload `QualitySystem-1.0.0-Linux-x86_64.zip`
5. Copy release notes from `RELEASE_NOTES.txt`

### 5. Update Auto-Update Server

Edit `update_info.json`:
```json
{
  "version": "1.0.0",
  "linux": {
    "url": "https://github.com/yourusername/quality-system/releases/download/v1.0.0/QualitySystem-1.0.0-x86_64.AppImage",
    "sha256": "get-this-from-SHA256SUMS"
  },
  "release_notes": "What's new in 1.0.0..."
}
```

Host this file at:
- `https://yourdomain.com/updates/update_info.json`
- Or: GitHub Pages, GitLab Pages, etc.

---

## For Windows

### 1. Build Installer
```bash
# On Windows with Python + PyInstaller installed
python build-windows.py
```

Output: `dist/QualitySystem-1.0.0-Setup.exe`

### 2. Test Installer
- Run on clean Windows VM
- Test installation
- Test auto-update
- Test uninstallation

### 3. Sign the Installer (Optional but Recommended)
```bash
# Using SignTool (requires code signing certificate)
signtool sign /f "certificate.pfx" /p "password" /t http://timestamp.digicert.com QualitySystem-1.0.0-Setup.exe
```

### 4. Create Release Package
```bash
# Already done by build-windows.py
# Output in: releases/QualitySystem-1.0.0-Windows/
```

### 5. Upload to GitHub Releases
```bash
gh release upload v1.0.0 \
  releases/QualitySystem-1.0.0-Windows/QualitySystem-1.0.0-Setup.exe
```

### 6. Update Auto-Update JSON
Add Windows section to `update_info.json`:
```json
{
  "version": "1.0.0",
  "windows": {
    "url": "https://github.com/yourusername/quality-system/releases/download/v1.0.0/QualitySystem-1.0.0-Setup.exe",
    "sha256": "checksum-here"
  }
}
```

---

## Distribution Checklist

Before each release:

- [ ] Update version in `version.py`
- [ ] Update CHANGELOG.md
- [ ] Test on Linux
- [ ] Test on Windows
- [ ] Build Linux AppImage
- [ ] Build Windows installer
- [ ] Create release packages
- [ ] Generate checksums
- [ ] Upload to GitHub Releases
- [ ] Update `update_info.json`
- [ ] Test auto-update on both platforms
- [ ] Announce release

---

## Hosting Options for update_info.json

### Option 1: GitHub Pages (Free, Recommended)
```bash
# Create gh-pages branch
git checkout --orphan gh-pages
echo '{"version": "1.0.0", ...}' > update_info.json
git add update_info.json
git commit -m "Add update info"
git push origin gh-pages

# Enable GitHub Pages in repo settings
# URL: https://yourusername.github.io/quality-system/update_info.json
```

### Option 2: GitHub Raw (Simple)
Store in repo main branch:
```
https://raw.githubusercontent.com/yourusername/quality-system/main/update_info.json
```

### Option 3: Your Own Server
Upload to your web server:
```bash
scp update_info.json user@yourserver.com:/var/www/html/updates/
```

### Option 4: CDN (Cloudflare, etc.)
Upload to CDN for faster global distribution

---

## User Installation Instructions

### Linux Users:
```bash
# Download and extract
wget https://github.com/yourusername/quality-system/releases/download/v1.0.0/QualitySystem-1.0.0-Linux-x86_64.tar.gz
tar -xzf QualitySystem-1.0.0-Linux-x86_64.tar.gz
cd QualitySystem-1.0.0-Linux-x86_64

# Install
chmod +x install-linux.sh
./install-linux.sh

# Or run portable
chmod +x QualitySystem-1.0.0-x86_64.AppImage
./QualitySystem-1.0.0-x86_64.AppImage
```

### Windows Users:
1. Download `QualitySystem-1.0.0-Setup.exe`
2. Run the installer
3. Follow installation wizard
4. Launch from Start Menu

---

## Versioning

Use Semantic Versioning (semver):
- **1.0.0** → **1.0.1** - Bug fixes
- **1.0.0** → **1.1.0** - New features (backward compatible)
- **1.0.0** → **2.0.0** - Breaking changes

Update in `version.py`:
```python
__version__ = "1.1.0"
```

---

## Support & Documentation

### For Users:
- Installation guide: LINUX_INSTALL.md / WINDOWS_INSTALL.md
- User manual: docs/USER_GUIDE.md
- FAQ: docs/FAQ.md
- Issues: GitHub Issues

### For Developers:
- Build instructions: This file
- Contributing: CONTRIBUTING.md
- API docs: docs/API.md
