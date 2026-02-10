# Quality Management System - Linux Distribution

## Installation

### Option 1: Quick Install (Recommended)
```bash
chmod +x install-linux.sh
./install-linux.sh
```

This will:
- Install the application to `~/.local/share/QualitySystem/`
- Create a desktop menu entry
- Add application icon
- Enable launching from application menu

### Option 2: Portable Mode (No Installation)
```bash
chmod +x QualitySystem-1.0.0-x86_64.AppImage
./QualitySystem-1.0.0-x86_64.AppImage
```

## Running the Application

After installation:
- **From Menu**: Search for "Quality System" in your application launcher
- **From Terminal**: `~/.local/share/QualitySystem/QualitySystem.AppImage`

## Uninstallation

```bash
~/.local/share/QualitySystem/uninstall.sh
```

## Auto-Updates

The application will automatically check for updates on startup. When a new version is available:
1. You'll see a notification with release notes
2. Click "Download Update" to get the new version
3. The update will be downloaded and verified
4. Restart the application to use the new version

## System Requirements

- Linux x86_64 (64-bit)
- GLIBC 2.31 or newer
- ~200 MB disk space
- Graphics: OpenGL 2.0+
- Display: 1024x768 minimum

## Supported Distributions

Tested on:
- Ubuntu 20.04+
- Debian 11+
- Fedora 34+
- openSUSE Leap 15.3+
- Arch Linux
- Linux Mint 20+

Should work on any modern Linux distribution.

## Data Location

Application data is stored in:
- Database: `~/.quality_system/quality_system.db`
- Documents: `~/.quality_system/documents/`
- Images: `~/.quality_system/images/`
- Backups: `~/.quality_system/backups/`

## Troubleshooting

### AppImage won't run
```bash
# Make sure it's executable
chmod +x QualitySystem-1.0.0-x86_64.AppImage

# Check FUSE support
sudo apt install fuse libfuse2  # Ubuntu/Debian
sudo dnf install fuse fuse-libs  # Fedora
```

### Desktop integration not working
```bash
# Manually register desktop file
desktop-file-install --dir=$HOME/.local/share/applications ~/.local/share/applications/QualitySystem.desktop
update-desktop-database ~/.local/share/applications
```

### Database permission issues
```bash
# Fix permissions
chmod 755 ~/.quality_system
chmod 644 ~/.quality_system/quality_system.db
```

## Support

For issues and updates, visit: https://github.com/yourusername/quality-system

## License

See LICENSE file for details.
