#!/bin/bash
# Build script for Quality Management System - Linux

echo "=========================================="
echo "Building Quality Management System v1.0.0"
echo "Platform: Linux"
echo "=========================================="

# Check if PyInstaller is installed
if ! command -v pyinstaller &> /dev/null
then
    echo "PyInstaller not found. Installing..."
    pip install pyinstaller
fi

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Activate virtual environment if exists
if [ -d "env" ]; then
    echo "Activating virtual environment..."
    source env/bin/activate
fi

# Create build directory
mkdir -p build

# Build with PyInstaller
echo "Building application..."
pyinstaller \
    --name="QualityManagementSystem" \
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

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "Build successful!"
    echo "Executable: dist/QualityManagementSystem"
    echo "=========================================="
    
    # Make executable
    chmod +x dist/QualityManagementSystem
    
    # Get file size
    size=$(du -h dist/QualityManagementSystem | cut -f1)
    echo "File size: $size"
    
    # Create AppImage (optional)
    read -p "Create AppImage? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]
    then
        echo "Creating AppImage..."
        # Install appimagetool if needed
        if ! command -v appimagetool &> /dev/null
        then
            echo "Downloading appimagetool..."
            wget https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage
            chmod +x appimagetool-x86_64.AppImage
        fi
        
        # Create AppDir structure
        mkdir -p AppDir/usr/bin
        mkdir -p AppDir/usr/share/applications
        mkdir -p AppDir/usr/share/icons/hicolor/256x256/apps
        
        # Copy executable
        cp dist/QualityManagementSystem AppDir/usr/bin/
        
        # Create desktop file
        cat > AppDir/usr/share/applications/qms.desktop << EOF
[Desktop Entry]
Type=Application
Name=Quality Management System
Exec=QualityManagementSystem
Icon=qms
Categories=Office;
EOF
        
        # Copy icon (if exists)
        if [ -f "assets/icon.png" ]; then
            cp assets/icon.png AppDir/usr/share/icons/hicolor/256x256/apps/qms.png
        fi
        
        # Create AppRun
        cat > AppDir/AppRun << 'EOF'
#!/bin/bash
SELF=$(readlink -f "$0")
HERE=${SELF%/*}
export PATH="${HERE}/usr/bin/:${HERE}/usr/sbin/:${HERE}/usr/games/:${HERE}/bin/:${HERE}/sbin/${PATH:+:$PATH}"
export LD_LIBRARY_PATH="${HERE}/usr/lib/:${HERE}/usr/lib/i386-linux-gnu/:${HERE}/usr/lib/x86_64-linux-gnu/:${HERE}/usr/lib32/:${HERE}/usr/lib64/:${HERE}/lib/:${HERE}/lib/i386-linux-gnu/:${HERE}/lib/x86_64-linux-gnu/:${HERE}/lib32/:${HERE}/lib64/${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export PYTHONPATH="${HERE}/usr/share/pyshared/${PYTHONPATH:+:$PYTHONPATH}"
export XDG_DATA_DIRS="${HERE}/usr/share/${XDG_DATA_DIRS:+:$XDG_DATA_DIRS}"
export PERLLIB="${HERE}/usr/share/perl5/:${HERE}/usr/lib/perl5/${PERLLIB:+:$PERLLIB}"
export GSETTINGS_SCHEMA_DIR="${HERE}/usr/share/glib-2.0/schemas/${GSETTINGS_SCHEMA_DIR:+:$GSETTINGS_SCHEMA_DIR}"
export QT_PLUGIN_PATH="${HERE}/usr/lib/qt5/plugins/:${HERE}/usr/lib/i386-linux-gnu/qt5/plugins/:${HERE}/usr/lib/x86_64-linux-gnu/qt5/plugins/:${HERE}/usr/lib32/qt5/plugins/:${HERE}/usr/lib64/qt5/plugins/:${HERE}/usr/lib/qt/plugins/:${QT_PLUGIN_PATH:+:$QT_PLUGIN_PATH}"
EXEC=$(grep -e '^Exec=.*' "${HERE}"/*.desktop | head -n 1 | cut -d "=" -f 2 | cut -d " " -f 1)
exec "${EXEC}" "$@"
EOF
        chmod +x AppDir/AppRun
        
        # Build AppImage
        if [ -f "appimagetool-x86_64.AppImage" ]; then
            ./appimagetool-x86_64.AppImage AppDir QualityManagementSystem-x86_64.AppImage
        else
            appimagetool AppDir QualityManagementSystem-x86_64.AppImage
        fi
        
        echo "AppImage created: QualityManagementSystem-x86_64.AppImage"
    fi
else
    echo ""
    echo "Build failed! Check errors above."
    exit 1
fi
