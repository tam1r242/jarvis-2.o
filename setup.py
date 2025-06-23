import os
import sys
import platform
import subprocess
import venv
from pathlib import Path

def is_windows():
    return platform.system().lower() == "windows"

def is_raspberry_pi():
    try:
        with open('/sys/firmware/devicetree/base/model', 'r') as f:
            return 'raspberry pi' in f.read().lower()
    except:
        return False

def run_command(command, shell=True):
    """Run a command and return its output."""
    try:
        result = subprocess.run(
            command,
            shell=shell,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        print(f"Error output: {e.stderr}")
        raise

def install_espeak_windows():
    """Download and install espeak-ng on Windows."""
    print("Checking espeak-ng installation...")
    
    # Check if espeak-ng is already in PATH
    try:
        subprocess.run(['espeak-ng', '--version'], capture_output=True)
        print("espeak-ng is already installed")
        return
    except FileNotFoundError:
        pass
    
    print("Installing espeak-ng...")
    espeak_version = "1.51"
    espeak_url = f"https://github.com/espeak-ng/espeak-ng/releases/download/{espeak_version}/espeak-ng-{espeak_version}.msi"
    
    try:
        # Download installer
        msi_path = "espeak-ng-setup.msi"
        run_command(f"curl -L {espeak_url} -o {msi_path}")
        
        # Run installer
        print("Running espeak-ng installer...")
        run_command(f'msiexec /i {msi_path} /quiet /qn')
        
        # Clean up
        os.remove(msi_path)
        
        # Add to PATH if not already there
        espeak_path = os.path.join(os.environ.get('PROGRAMFILES', 'C:/Program Files'), 'eSpeak NG')
        if espeak_path not in os.environ['PATH']:
            os.environ['PATH'] = f"{espeak_path};{os.environ['PATH']}"
            
        print("espeak-ng installed successfully")
        
    except Exception as e:
        print(f"Error installing espeak-ng: {e}")
        print("Please install espeak-ng manually from:")
        print("https://github.com/espeak-ng/espeak-ng/releases")
        print("And ensure it's added to your system PATH")
        sys.exit(1)

def setup_windows():
    """Windows-specific setup steps."""
    print("Setting up for Windows...")
    
    # Check for Python
    if sys.version_info < (3, 7):
        raise RuntimeError("Python 3.7 or higher is required")

    # Install Visual C++ Build Tools if needed
    try:
        import pyaudio
    except ImportError:
        print("Please install Visual C++ Build Tools:")
        print("1. Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/")
        print("2. Install 'Desktop development with C++'")
        print("3. Run this setup script again")
        sys.exit(1)
        
    # Install espeak-ng
    install_espeak_windows()

def setup_raspberry_pi():
    """Raspberry Pi-specific setup steps."""
    print("Setting up for Raspberry Pi...")
    
    # Install system packages
    packages = [
        "python3-dev",
        "portaudio19-dev",
        "espeak-ng",
        "libespeak-ng-dev",
        "libasound2-dev"
    ]
    
    run_command("sudo apt-get update")
    run_command(f"sudo apt-get install -y {' '.join(packages)}")

def create_virtual_environment():
    """Create and configure virtual environment."""
    print("Creating virtual environment...")
    venv.create("venv", with_pip=True)
    
    # Activate virtual environment
    if is_windows():
        activate_script = "venv\\Scripts\\activate"
    else:
        activate_script = "source venv/bin/activate"
    
    print(f"To activate virtual environment, run: {activate_script}")

def download_models():
    """Download required models."""
    print("Downloading models...")
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # Download Vosk model
    vosk_model = "vosk-model-small-en-us-0.15.zip"
    vosk_url = f"https://alphacephei.com/vosk/models/{vosk_model}"
    
    print("Downloading Vosk model...")
    if is_windows():
        run_command(f"curl -L {vosk_url} -o {vosk_model}")
    else:
        run_command(f"wget {vosk_url}")
    
    # Extract Vosk model
    if is_windows():
        run_command(f"tar -xf {vosk_model}")
    else:
        run_command(f"unzip {vosk_model}")
    
    # Move to models directory
    source = "vosk-model-small-en-us-0.15"
    target = models_dir / "vosk-model"
    if target.exists():
        import shutil
        shutil.rmtree(target)
    Path(source).rename(target)
    
    # Download Whisper model
    whisper_model = "whisper-tiny.bin"
    whisper_url = f"https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin"
    
    print("Downloading Whisper model...")
    if is_windows():
        run_command(f"curl -L {whisper_url} -o {models_dir / whisper_model}")
    else:
        run_command(f"wget -O {models_dir / whisper_model} {whisper_url}")

def setup():
    """Main setup function."""
    print("Starting Jarvis Voice Assistant setup...")
    
    # Platform-specific setup
    if is_raspberry_pi():
        setup_raspberry_pi()
    elif is_windows():
        setup_windows()
    else:
        print("Unsupported platform. Please use Windows or Raspberry Pi.")
        sys.exit(1)
    
    # Create virtual environment
    create_virtual_environment()
    
    # Install Python dependencies
    print("Installing Python dependencies...")
    pip_command = "venv\\Scripts\\pip" if is_windows() else "venv/bin/pip"
    run_command(f"{pip_command} install -r requirements.txt")
    
    # Download models
    download_models()
    
    # Create config directory if needed
    config_dir = Path("config")
    config_dir.mkdir(exist_ok=True)
    
    # Copy config if not exists
    config_file = config_dir / "config.json"
    if not config_file.exists():
        Path("config.json").rename(config_file)
    
    print("\nSetup completed successfully!")
    print("\nTo start the voice assistant:")
    if is_windows():
        print("1. Run: .\\venv\\Scripts\\activate")
    else:
        print("1. Run: source venv/bin/activate")
    print("2. Run: python main.py")
    print("\nMake sure to update your Groq API key in config/config.json")

if __name__ == "__main__":
    setup()
