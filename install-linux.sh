#!/bin/bash
# Linux Installation Script for Quality System

set -e

APP_NAME="QualitySystem"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/256x256/apps/$APP_NAME.png"

echo "Installing Quality Management System..."

# Create directories
mkdir -p "$INSTALL_DIR"
mkdir -p "$HOME/.local/share/applications"
mkdir -p "$HOME/.local/share/icons/hicolor/256x256/apps"

# Find the AppImage file
APPIMAGE=$(ls QualitySystem-*.AppImage 2>/dev/null | head -n1)

if [ -z "$APPIMAGE" ]; then
    echo "Error: No AppImage file found!"
    echo "Please run this script from the directory containing the AppImage file."
    exit 1
fi

# Copy AppImage to install directory
echo "Installing $APPIMAGE..."
cp "$APPIMAGE" "$INSTALL_DIR/QualitySystem.AppImage"
chmod +x "$INSTALL_DIR/QualitySystem.AppImage"

# Extract icon from AppImage (if available)
if [ -f "quality_system_icon.png" ]; then
    cp quality_system_icon.png "$ICON_FILE"
else
    echo "Note: No icon file found, using default icon"
fi

# Create desktop entry
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Quality System
Comment=Quality Management System for ISO Standards
Exec=$INSTALL_DIR/QualitySystem.AppImage
Icon=$APP_NAME
Terminal=false
Categories=Office;Development;
Keywords=quality;iso;management;inspection;
StartupWMClass=quality_system
EOF

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications"
fi

# Create uninstall script
cat > "$INSTALL_DIR/uninstall.sh" << 'EOF'
#!/bin/bash
APP_NAME="QualitySystem"
INSTALL_DIR="$HOME/.local/share/$APP_NAME"
DESKTOP_FILE="$HOME/.local/share/applications/$APP_NAME.desktop"
ICON_FILE="$HOME/.local/share/icons/hicolor/256x256/apps/$APP_NAME.png"

echo "Uninstalling Quality Management System..."
rm -rf "$INSTALL_DIR"
rm -f "$DESKTOP_FILE"
rm -f "$ICON_FILE"

if command -v update-desktop-database &> /dev/null; then
    update-desktop-database "$HOME/.local/share/applications"
fi

echo "Uninstalled successfully!"
EOF

chmod +x "$INSTALL_DIR/uninstall.sh"

echo ""
echo "✓ Installation complete!"
echo ""
echo "You can now:"
echo "  • Launch from application menu: Search for 'Quality System'"
echo "  • Run from terminal: $INSTALL_DIR/QualitySystem.AppImage"
echo "  • Uninstall: $INSTALL_DIR/uninstall.sh"
echo ""
