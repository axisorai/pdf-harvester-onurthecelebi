@echo off
REM ============================================================
REM PDF Harvester Build Script for Windows
REM Created by ONUR THE CELEBI Solutions
REM ============================================================

echo.
echo ============================================================
echo    PDF Harvester - Windows Build Script
echo    Created by ONUR THE CELEBI Solutions
echo ============================================================
echo.

REM Step 1: Create virtual environment
echo [1/5] Creating virtual environment...
python -m venv venv
call venv\Scripts\activate.bat

REM Step 2: Install dependencies
echo [2/5] Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Step 3: Install Playwright browsers
echo [3/5] Installing Playwright browsers...
playwright install chromium

REM Step 4: Build executable
echo [4/5] Building executable with PyInstaller...
pyinstaller build_windows.spec --clean

echo.
echo ============================================================
echo    BUILD COMPLETE!
echo    Created by ONUR THE CELEBI Solutions
echo ============================================================
echo.
echo Executable created: dist\PDFHarvester_OnurTheCelebi.exe
echo.
echo IMPORTANT: To create the installer:
echo 1. Install Inno Setup from https://jrsoftware.org/isinfo.php
echo 2. Open installer.iss with Inno Setup
echo 3. Click Build ^> Compile
echo 4. Installer will be created in installer_output folder
echo.
echo ============================================================
pause
