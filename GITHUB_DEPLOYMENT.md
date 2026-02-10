# Quick Start: GitHub Actions Deployment

## Setup Steps

### 1. Create GitHub Repository

```bash
# Initialize git if not already done
cd /home/mohammad-basem/Desktop/python/quality_system
git init

# Add all files
git add .
git commit -m "Initial commit - Quality Management System v1.0.0"

# Create repository on GitHub.com, then:
git remote add origin https://github.com/YOUR_USERNAME/quality-system.git
git branch -M main
git push -u origin main
```

### 2. Verify Workflow File

The workflow is already created at `.github/workflows/build.yml`. It will:
- ✅ Build Linux AppImage automatically
- ✅ Build Windows EXE automatically  
- ✅ Generate SHA256 checksums
- ✅ Create GitHub Release with all files
- ✅ Generate update_info.json for auto-updates

### 3. Create Your First Release

```bash
# Make sure version.py has the correct version
cat version.py
# Should show: __version__ = "1.0.0"

# Create and push a version tag
git tag v1.0.0
git push origin v1.0.0
```

### 4. Watch the Build

1. Go to your GitHub repository
2. Click "Actions" tab
3. Watch the "Build and Release" workflow run
4. Takes about 10-15 minutes to complete

### 5. Download Your Release

1. Go to "Releases" on your GitHub repository
2. You'll see v1.0.0 release with:
   - `QualitySystem-v1.0.0-x86_64.AppImage` (Linux)
   - `QualitySystem-v1.0.0-Windows-x86_64.exe` (Windows)
   - Checksum files (.sha256)
   - Release notes

### 6. Setup Auto-Updates (Optional)

#### Option A: GitHub Pages (Free, Easy)

```bash
# Download update_info.json from workflow artifacts
# Then create gh-pages branch

git checkout --orphan gh-pages
git rm -rf .
wget https://github.com/YOUR_USERNAME/quality-system/actions/runs/XXXXX/artifacts/update-info
unzip update-info
git add update_info.json
git commit -m "Add update info"
git push origin gh-pages

# Enable GitHub Pages in Settings → Pages
# Source: gh-pages branch, / (root)
```

#### Option B: Use GitHub Releases (Alternative)

Host `update_info.json` directly from your latest release:

```bash
# After each release, upload update_info.json as an additional asset
# URL: https://github.com/YOUR_USERNAME/quality-system/releases/latest/download/update_info.json
```

Then update `updater.py`:
```python
UPDATE_CHECK_URL = "https://YOUR_USERNAME.github.io/quality-system/update_info.json"
# or
UPDATE_CHECK_URL = "https://github.com/YOUR_USERNAME/quality-system/releases/latest/download/update_info.json"
```

### 7. Future Updates

```bash
# 1. Make your changes
# 2. Update version in version.py
echo '__version__ = "1.0.1"' > version.py

# 3. Commit changes
git add .
git commit -m "Version 1.0.1 - Bug fixes and improvements"
git push

# 4. Create new tag
git tag v1.0.1
git push origin v1.0.1

# 5. GitHub Actions automatically builds and releases!
```

## Testing Locally Before Release

```bash
# Test Linux build
./build_linux.sh

# Test the AppImage
./QualitySystem-1.0.0-x86_64.AppImage

# If it works, push your tag
git tag v1.0.0
git push origin v1.0.0
```

## Troubleshooting

### Workflow Doesn't Start
- Check tag format: Must be `v*` (v1.0.0, v2.1.3, etc.)
- Check Actions tab → Workflow permissions (allow read/write)

### Build Fails
- Check workflow logs in Actions tab
- Common issues:
  - Missing dependencies in requirements.txt
  - Python version mismatch
  - PyInstaller compatibility

### No Release Created
- Check workflow has completed all 3 jobs
- Verify repository has "Contents: write" permission
- Check "Releases" page after ~15 minutes

## What You Get

### Linux Users
```bash
# Download AppImage
chmod +x QualitySystem-v1.0.0-x86_64.AppImage

# Install FUSE if needed
sudo apt install libfuse2

# Run
./QualitySystem-v1.0.0-x86_64.AppImage
```

### Windows Users
```bash
# Download EXE
# Double-click to run
# Allow Windows SmartScreen if prompted
```

## Cost

- ✅ GitHub Actions: FREE (2,000 minutes/month)
- ✅ GitHub Pages: FREE (1GB storage)
- ✅ GitHub Releases: FREE (2GB per file)

Perfect for open source or small projects!
