# GitHub Actions Workflows

## Build and Release Workflow

Automatically builds your Quality Management System for both Linux and Windows.

### How to Use

1. **First Time Setup:**
   ```bash
   # Initialize git repository if not already done
   git init
   git add .
   git commit -m "Initial commit"
   
   # Add your GitHub repository
   git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
   git push -u origin main
   ```

2. **Create a Release:**
   ```bash
   # Update version in version.py first
   # Then create and push a version tag
   git tag v1.0.0
   git push origin v1.0.0
   ```

3. **Automatic Build:**
   - GitHub Actions will automatically:
     - Build Linux AppImage
     - Build Windows executable
     - Generate SHA256 checksums
     - Create a GitHub Release with all files
     - Generate update_info.json for auto-updates

4. **Manual Trigger:**
   - Go to GitHub → Actions tab → Build and Release → Run workflow
   - Select branch and click "Run workflow"

### What Gets Built

#### Linux Build
- **Output:** `QualitySystem-v1.0.0-x86_64.AppImage`
- **Size:** ~140 MB
- **Requirements:** libfuse2
- **Format:** AppImage (portable, no installation needed)

#### Windows Build
- **Output:** `QualitySystem-v1.0.0-Windows-x86_64.exe`
- **Size:** ~80-100 MB
- **Requirements:** Windows 10/11
- **Format:** Standalone executable

### Release Assets

Each release includes:
- Linux AppImage file
- Windows EXE file
- SHA256 checksum files
- Detailed release notes
- update_info.json (for auto-update system)

### Setting Up Auto-Updates

1. **After First Release:**
   - Download `update_info.json` from workflow artifacts
   - Upload to GitHub Pages or your server
   - URL should be: `https://your-domain.com/update_info.json`

2. **Update updater.py:**
   ```python
   UPDATE_CHECK_URL = "https://your-domain.com/update_info.json"
   ```

3. **For GitHub Pages:**
   ```bash
   # Create gh-pages branch
   git checkout --orphan gh-pages
   git rm -rf .
   
   # Add update_info.json
   cp update_info.json .
   git add update_info.json
   git commit -m "Add update info"
   git push origin gh-pages
   
   # Enable GitHub Pages in repository settings
   # URL will be: https://YOUR_USERNAME.github.io/YOUR_REPO/update_info.json
   ```

### Troubleshooting

**Build fails on Linux:**
- Check Python version (3.12 required)
- Verify all dependencies in requirements.txt
- Check PyInstaller compatibility

**Build fails on Windows:**
- Check for Windows-specific path issues
- Verify PyQt6 Windows wheels available
- Check for antivirus interference

**Release not created:**
- Verify tag format is `v*` (e.g., v1.0.0)
- Check GitHub permissions (needs write access)
- Review workflow logs in Actions tab

**AppImage won't run:**
- Install libfuse2: `sudo apt install libfuse2`
- Make executable: `chmod +x *.AppImage`
- Try: `./QualitySystem-*.AppImage --appimage-extract-and-run`

### Version Management

1. **Update version.py:**
   ```python
   __version__ = "1.0.1"  # Increment version
   ```

2. **Create git tag:**
   ```bash
   git add version.py
   git commit -m "Bump version to 1.0.1"
   git push
   
   git tag v1.0.1
   git push origin v1.0.1
   ```

3. **Wait for build:**
   - Check Actions tab for progress
   - Release appears when complete

### Workflow Files

- **build.yml** - Main build and release workflow
- Triggers: Git tags (v*), manual dispatch
- Jobs: build-linux, build-windows, create-release
- Artifacts: AppImage, EXE, checksums, update info

### Security Notes

- Checksums are automatically generated for verification
- No secrets required for basic builds
- Windows executables are unsigned (will show SmartScreen warning)
- Consider code signing for production releases

### Advanced Configuration

**Add code signing (Windows):**
```yaml
- name: Sign Windows executable
  uses: dlemstra/code-sign-action@v1
  with:
    certificate: '${{ secrets.CERTIFICATE }}'
    password: '${{ secrets.CERTIFICATE_PASSWORD }}'
    folder: 'dist'
```

**Add macOS build:**
```yaml
build-macos:
  runs-on: macos-latest
  steps:
    # Similar to Linux build
    # Create .app bundle or DMG
```

**Notify on release:**
```yaml
- name: Send notification
  uses: actions/slack-action@v3
  with:
    status: ${{ job.status }}
    webhook: ${{ secrets.SLACK_WEBHOOK }}
```
