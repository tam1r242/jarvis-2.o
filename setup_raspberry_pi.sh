#!/bin/bash

echo "Setting up Jarvis Voice Assistant on Raspberry Pi..."

# Exit on error
set -e

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    portaudio19-dev \
    espeak-ng \
    libespeak-ng-dev \
    libasound2-dev \
    wget \
    unzip \
    cmake \
    build-essential \
    git

# Install PyTorch for ARM
echo "Installing PyTorch for ARM..."
pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Create virtual environment
echo "Setting up Python virtual environment..."
python3 -m pip install --user virtualenv
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

# Create directories
echo "Creating required directories..."
mkdir -p models

# Download Vosk model
echo "Downloading Vosk model..."
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip -d models/
mv models/vosk-model-small-en-us-0.15 models/vosk-model
rm vosk-model-small-en-us-0.15.zip

# Download faster-whisper model
echo "Downloading faster-whisper tiny model..."
mkdir -p models/whisper
if [ ! -d "models/whisper/tiny" ]; then
    python3 -c "
from faster_whisper import WhisperModel
print('Downloading and converting Whisper tiny model...')
model = WhisperModel('tiny', download_root='models/whisper')
print('Model downloaded successfully')
"
fi

# Set up configuration
if [ ! -f "config/config.json" ]; then
    echo "Creating default configuration..."
    mkdir -p config
    cp config.json config/config.json
fi

# Make main script executable
chmod +x main.py

echo "Installation complete!"
echo ""
echo "To start the voice assistant:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Run the assistant: python main.py"
echo ""
echo "Note: Please ensure you have updated the Groq API key in config/config.json"
echo "The wake word is set to 'hi jarvis' by default. You can change this in config/config.json"
