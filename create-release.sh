#!/bin/bash
# Create distributable release package for Linux

set -e

VERSION=$(python3 -c "from version import __version__; print(__version__)")
ARCH="x86_64"
RELEASE_NAME="QualitySystem-${VERSION}-Linux-${ARCH}"
RELEASE_DIR="releases/${RELEASE_NAME}"

echo "Creating release package: ${RELEASE_NAME}"

# Create release directory
mkdir -p "$RELEASE_DIR"

# Find and copy AppImage
APPIMAGE=$(ls QualitySystem-*.AppImage 2>/dev/null | head -n1)
if [ -z "$APPIMAGE" ]; then
    echo "Error: No AppImage found! Build it first with: ./build-linux.sh"
    exit 1
fi

echo "Copying AppImage: $APPIMAGE"
cp "$APPIMAGE" "$RELEASE_DIR/"

# Copy installation script
echo "Copying installation script..."
cp install-linux.sh "$RELEASE_DIR/"
chmod +x "$RELEASE_DIR/install-linux.sh"

# Copy documentation
echo "Copying documentation..."
cp LINUX_INSTALL.md "$RELEASE_DIR/README.md"
cp LICENSE "$RELEASE_DIR/" 2>/dev/null || echo "Note: No LICENSE file found"

# Copy icon if available
if [ -f "quality_system_icon.png" ]; then
    cp quality_system_icon.png "$RELEASE_DIR/"
fi

# Create checksums
echo "Generating checksums..."
cd "$RELEASE_DIR"
sha256sum * > SHA256SUMS
cd - > /dev/null

# Create tarball
echo "Creating tarball..."
cd releases
tar -czf "${RELEASE_NAME}.tar.gz" "${RELEASE_NAME}"
cd - > /dev/null

# Create zip (for Windows users downloading)
echo "Creating zip archive..."
cd releases
zip -r "${RELEASE_NAME}.zip" "${RELEASE_NAME}" > /dev/null
cd - > /dev/null

# Generate release notes
cat > "$RELEASE_DIR/RELEASE_NOTES.txt" << EOF
Quality Management System - Version ${VERSION}
Release Date: $(date +"%Y-%m-%d")

WHAT'S INCLUDED:
- QualitySystem-${VERSION}-x86_64.AppImage - Main application
- install-linux.sh - Installation script
- README.md - Installation and usage instructions
- SHA256SUMS - File verification checksums

QUICK START:
1. Extract this archive
2. Run: chmod +x install-linux.sh && ./install-linux.sh
3. Launch from your application menu

For detailed instructions, see README.md

CHANGES IN THIS VERSION:
$(git log --oneline -10 2>/dev/null || echo "- Initial release")

SYSTEM REQUIREMENTS:
- Linux x86_64 (64-bit)
- GLIBC 2.31+
- 200 MB disk space

SUPPORT:
Report issues at: https://github.com/yourusername/quality-system/issues
EOF

echo ""
echo "✓ Release package created successfully!"
echo ""
echo "Output files:"
echo "  • releases/${RELEASE_NAME}/ - Extracted package"
echo "  • releases/${RELEASE_NAME}.tar.gz - Linux tarball"
echo "  • releases/${RELEASE_NAME}.zip - Zip archive"
echo ""
echo "To distribute:"
echo "  1. Upload .tar.gz and .zip to GitHub Releases"
echo "  2. Update update_info.json with new version"
echo "  3. Users can install with: tar -xzf ${RELEASE_NAME}.tar.gz && cd ${RELEASE_NAME} && ./install-linux.sh"
echo ""
