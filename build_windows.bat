@echo off
REM Build script for Quality Management System - Windows

echo ==========================================
echo Building Quality Management System v1.0.0
echo Platform: Windows
echo ==========================================

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo PyInstaller not found. Installing...
    python -m pip install pyinstaller
)

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
del /q *.spec 2>nul

REM Activate virtual environment if exists
if exist env\Scripts\activate.bat (
    echo Activating virtual environment...
    call env\Scripts\activate.bat
)

REM Create build directory
if not exist build mkdir build

REM Build with PyInstaller
echo Building application...
pyinstaller ^
    --name="QualityManagementSystem" ^
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

if %errorlevel% equ 0 (
    echo.
    echo ==========================================
    echo Build successful!
    echo Executable: dist\QualityManagementSystem.exe
    echo ==========================================
    
    REM Get file size
    for %%A in (dist\QualityManagementSystem.exe) do echo File size: %%~zA bytes
    
    REM Option to create installer
    echo.
    set /p CREATE_INSTALLER="Create installer with Inno Setup? (y/n): "
    if /i "%CREATE_INSTALLER%"=="y" (
        echo Creating installer...
        
        REM Check if Inno Setup is installed
        if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
            REM Create Inno Setup script
            echo [Setup] > installer.iss
            echo AppName=Quality Management System >> installer.iss
            echo AppVersion=1.0.0 >> installer.iss
            echo DefaultDirName={pf}\QualityManagementSystem >> installer.iss
            echo DefaultGroupName=Quality Management System >> installer.iss
            echo OutputBaseFilename=QMS-Setup-1.0.0 >> installer.iss
            echo Compression=lzma2 >> installer.iss
            echo SolidCompression=yes >> installer.iss
            echo.>> installer.iss
            echo [Files] >> installer.iss
            echo Source: "dist\QualityManagementSystem.exe"; DestDir: "{app}"; Flags: ignoreversion >> installer.iss
            echo.>> installer.iss
            echo [Icons] >> installer.iss
            echo Name: "{group}\Quality Management System"; Filename: "{app}\QualityManagementSystem.exe" >> installer.iss
            echo Name: "{commondesktop}\Quality Management System"; Filename: "{app}\QualityManagementSystem.exe" >> installer.iss
            echo.>> installer.iss
            echo [Run] >> installer.iss
            echo Filename: "{app}\QualityManagementSystem.exe"; Description: "Launch Quality Management System"; Flags: nowait postinstall skipifsilent >> installer.iss
            
            REM Compile installer
            "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
            
            if exist "Output\QMS-Setup-1.0.0.exe" (
                echo Installer created: Output\QMS-Setup-1.0.0.exe
            )
        ) else (
            echo Inno Setup not found. Please install from https://jrsoftware.org/isinfo.php
        )
    )
) else (
    echo.
    echo Build failed! Check errors above.
    exit /b 1
)

pause
