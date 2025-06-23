@echo off
echo Setting up Jarvis Voice Assistant for Windows...

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed or not in PATH
    echo Please install Python 3.7 or higher from https://www.python.org/downloads/
    echo Ensure "Add Python to PATH" is checked during installation
    pause
    exit /b 1
)

REM Check for curl
curl --version >nul 2>&1
if errorlevel 1 (
    echo curl is not available. Please install curl or add it to PATH
    pause
    exit /b 1
)

REM Check Python architecture and version
python -c "import struct; import sys; arch='amd64' if struct.calcsize('P') * 8 == 64 else 'win32'; ver='cp%d%d' % (sys.version_info[0], sys.version_info[1]); print('ARCH=' + arch); print('PYVER=' + ver)" > tmp_vars.txt
set /p ARCH_LINE=<tmp_vars.txt
set /p PYVER_LINE=<tmp_vars.txt
set %ARCH_LINE%
set %PYVER_LINE%
del tmp_vars.txt

REM Download Vosk wheel
echo Downloading Vosk wheel for %ARCH%...
set VOSK_VERSION=0.3.45
set WHEEL_FILE=vosk-%VOSK_VERSION%-%PYVER%-%PYVER%-%ARCH%.whl
curl -L -o %WHEEL_FILE% https://alphacephei.com/vosk/wheels/%WHEEL_FILE%
if errorlevel 1 (
    echo Failed to download Vosk wheel
    pause
    exit /b 1
)

REM Create and activate virtual environment
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

REM Install Vosk wheel first
echo Installing Vosk...
pip install %WHEEL_FILE%
del %WHEEL_FILE%

REM Install other dependencies
echo Installing other dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install dependencies
    pause
    exit /b 1
)

REM Run setup.py
echo Running setup script...
python setup.py
if errorlevel 1 (
    echo Setup failed. Please check the error messages above.
    pause
    exit /b 1
)

echo.
echo Setup completed successfully!
echo.
echo Required manual installations:
echo 1. Download and install eSpeak-NG from:
echo    https://github.com/espeak-ng/espeak-ng/releases
echo.
echo To start the voice assistant:
echo 1. Run: .\venv\Scripts\activate
echo 2. Run: python main.py
echo.
echo Make sure to:
echo - Update your Groq API key in config/config.json
echo - Install eSpeak-NG if you haven't already

pause
