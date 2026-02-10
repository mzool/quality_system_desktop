# Building and Distribution Guide

## Quality Management System - Build Instructions

### Prerequisites

1. **Python 3.12+** installed
2. **PyInstaller** for building executables
3. **Virtual environment** with all dependencies

### Install Build Dependencies

```bash
# Linux/macOS
pip install pyinstaller requests

# Windows
python -m pip install pyinstaller requests
```

## Building for Linux

### Method 1: Simple Executable

```bash
chmod +x build_linux.sh
./build_linux.sh
```

Output: `dist/QualityManagementSystem`

### Method 2: AppImage (Recommended for Distribution)

The build script will ask if you want to create an AppImage. Select 'y' for yes.

Output: `QualityManagementSystem-x86_64.AppImage`

**Advantages of AppImage:**
- Single file
- No installation required
- Works on any Linux distribution
- Can be run from USB stick
- Self-contained with all dependencies

### Manual Build (Linux)

```bash
pyinstaller --name="QualityManagementSystem" \
    --onefile \
    --windowed \
    --icon=assets/icon.ico \
    --add-data "migrations:migrations" \
    --hidden-import="sqlalchemy.sql.default_comparator" \
    --hidden-import="PyQt6" \
    --hidden-import="reportlab" \
    --hidden-import="openpyxl" \
    --hidden-import="pandas" \
    --hidden-import="numpy" \
    --hidden-import="matplotlib" \
    --hidden-import="PIL" \
    --collect-all="reportlab" \
    --collect-all="matplotlib" \
    main.py
```

## Building for Windows

### Method 1: Executable Only

```cmd
build_windows.bat
```

Output: `dist\QualityManagementSystem.exe`

### Method 2: Installer (Recommended)

1. Install [Inno Setup](https://jrsoftware.org/isinfo.php)
2. Run `build_windows.bat`
3. When prompted, select 'y' to create installer

Output: `Output\QMS-Setup-1.0.0.exe`

### Manual Build (Windows)

```cmd
pyinstaller --name="QualityManagementSystem" ^
    --onefile ^
    --windowed ^
    --icon=assets/icon.ico ^
    --add-data="migrations;migrations" ^
    --hidden-import="sqlalchemy.sql.default_comparator" ^
    --hidden-import="PyQt6" ^
    --hidden-import="reportlab" ^
    --hidden-import="openpyxl" ^
    --hidden-import="pandas" ^
    --hidden-import="numpy" ^
    --hidden-import="matplotlib" ^
    --hidden-import="PIL" ^
    --collect-all="reportlab" ^
    --collect-all="matplotlib" ^
    main.py
```

## Build Options Explained

- `--onefile`: Bundle everything into single executable
- `--windowed`: No console window (GUI only)
- `--icon`: Application icon
- `--add-data`: Include additional files (migrations folder)
- `--hidden-import`: Import modules that PyInstaller might miss
- `--collect-all`: Include all files from a package

## Reducing Build Size

If the executable is too large (typical: 80-150 MB), you can:

1. **Use `--onedir` instead of `--onefile`:**
   - Creates folder with executable and DLLs
   - Slightly smaller total size
   - Faster startup time

2. **Exclude unnecessary packages:**
   ```bash
   --exclude-module=tkinter \
   --exclude-module=unittest \
   --exclude-module=test
   ```

3. **Use UPX compression:**
   ```bash
   pip install upx-ucl
   pyinstaller ... --upx-dir=/path/to/upx
   ```

## Auto-Update System

### 1. Update Server Setup

Create a JSON endpoint at `https://your-server.com/api/version`:

```json
{
  "version": "1.0.1",
  "download_url": "https://your-server.com/downloads/QMS-1.0.1-linux.AppImage",
  "notes": "Bug fixes and improvements:\n- Fixed image attachment issue\n- Improved PDF generation\n- Performance enhancements"
}
```

### 2. Configure Update URL

Edit `version.py`:

```python
__update_url__ = "https://your-server.com/api/version"
__download_url__ = "https://your-server.com/downloads"
```

### 3. How Auto-Update Works

1. App checks for updates on startup
2. If newer version available, shows notification
3. User can download and install with one click
4. Automatic installation (Linux: AppImage, Windows: .exe)

### 4. Testing Auto-Update

1. Build version 1.0.0
2. Deploy to server
3. Update `version.py` to 1.0.1
4. Build new version
5. Update server JSON
6. Run old version - should prompt for update

## Distribution

### Linux Distribution

**Option 1: AppImage (Recommended)**
- Upload `.AppImage` file to your server
- Users download and run (no installation)
- Update URL in version.py

**Option 2: DEB Package**
```bash
# Install fpm
gem install fpm

# Create .deb package
fpm -s dir -t deb \
    -n quality-management-system \
    -v 1.0.0 \
    --description "Quality Management System" \
    dist/QualityManagementSystem=/usr/bin/
```

**Option 3: Snap**
```bash
# Create snapcraft.yaml and build
snapcraft
```

### Windows Distribution

**Option 1: Installer (Recommended)**
- Use Inno Setup (included in build script)
- Creates professional installer with shortcuts
- Handles uninstallation

**Option 2: Portable .exe**
- Just distribute the .exe file
- No installation required
- Runs from any location

**Option 3: Microsoft Store**
- Requires packaging as MSIX
- Wider distribution
- Automatic updates via Store

## Code Signing (Optional but Recommended)

### Linux
```bash
# Sign AppImage with GPG
gpg --detach-sign QualityManagementSystem-x86_64.AppImage
```

### Windows
```bash
# Sign with signtool (requires certificate)
signtool sign /f certificate.pfx /p password /t http://timestamp.digicert.com dist/QualityManagementSystem.exe
```

## Continuous Integration

### GitHub Actions Example

Create `.github/workflows/build.yml`:

```yaml
name: Build Application

on:
  push:
    tags:
      - 'v*'

jobs:
  build-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pip install pyinstaller
      - run: chmod +x build_linux.sh
      - run: ./build_linux.sh
      - uses: actions/upload-artifact@v2
        with:
          name: linux-build
          path: QualityManagementSystem-x86_64.AppImage

  build-windows:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
      - run: pip install -r requirements.txt
      - run: pip install pyinstaller
      - run: build_windows.bat
      - uses: actions/upload-artifact@v2
        with:
          name: windows-build
          path: dist/QualityManagementSystem.exe
```

## Troubleshooting

### Build Errors

**"Module not found"**
- Add to `--hidden-import` in build script
- Or use `--collect-all=module_name`

**"Cannot find Qt platform plugin"**
- Already handled in scripts with `--collect-all`
- If still occurs, add: `--add-binary="/path/to/Qt/plugins:qt_plugins"`

**Large file size**
- Normal: 80-150 MB for full app
- Use `--onedir` for smaller total size
- Exclude unused modules

### Runtime Errors

**"Failed to execute script"**
- Run with console: remove `--windowed` flag
- Check error messages

**Missing DLLs (Windows)**
- Install Visual C++ Redistributable
- Or include DLLs: `--add-binary`

**Permission denied (Linux)**
```bash
chmod +x QualityManagementSystem
# or
chmod +x *.AppImage
```

## Version Management

### Release Process

1. **Update version.py**
   ```python
   __version__ = "1.1.0"
   __build__ = "20260215"
   ```

2. **Build executables**
   ```bash
   ./build_linux.sh    # Linux
   build_windows.bat   # Windows
   ```

3. **Test builds**
   - Run on clean system
   - Test all features
   - Verify database creation

4. **Upload to server**
   ```bash
   scp QMS-*.AppImage user@server:/var/www/downloads/
   ```

5. **Update version API**
   - Update JSON with new version number
   - Update download URLs
   - Add release notes

6. **Announce release**
   - Update documentation
   - Notify users
   - Create GitHub release

### Semantic Versioning

- **Major** (1.0.0): Breaking changes
- **Minor** (1.1.0): New features, backward compatible 
- **Patch** (1.0.1): Bug fixes only

## Creating Icon

### From PNG to ICO (Windows)

```bash
# Using ImageMagick
convert icon.png -define icon:auto-resize=256,128,64,48,32,16 icon.ico

# Online tool
# https://favicon.io/favicon-converter/
```

### For Linux AppImage

Place PNG icon in `assets/icon.png` (256x256 or 512x512 recommended)

## Performance Optimization

### Startup Time

- Use `--onedir` instead of `--onefile`
- Lazy import large modules
- Optimize database initialization

### File Size

- Remove debug prints
- Exclude test files
- Use UPX compression

## Support & Updates

For issues or questions:
- Check build logs in `build/` folder
- Review PyInstaller documentation
- Test on clean VM before distribution
