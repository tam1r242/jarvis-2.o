# Jarvis Voice Assistant

A Raspberry Pi-compatible offline voice assistant with wake word detection, speech recognition, and text-to-speech capabilities.

## Features

- Wake word detection using Vosk (responds to "hi jarvis")
- Offline speech recognition using Whisper.cpp
- Iron Man-style voice responses using espeak-ng
- Continuous listening mode
- Web interface support
- Fully offline-capable except for LLM responses (uses Groq)

## Requirements

- Raspberry Pi (3 or newer recommended)
- Microphone
- Speaker/headphones
- Python 3.7+
- Internet connection (only for initial setup and LLM responses)

## Installation

### Prerequisites

#### Windows
- Python 3.7 or higher
- Visual C++ Build Tools for PyAudio
- Git (optional)

#### Raspberry Pi
- Raspberry Pi 3 or newer
- Python 3.7 or higher
- Git (optional)

### Setup

1. Get the code:
```bash
git clone <repository-url>
cd jarvis-2.o
```
Or download and extract the ZIP file.

2. Run the setup script:

**Windows:**
```bash
setup_windows.bat
```

**Raspberry Pi:**
```bash
chmod +x setup_raspberry_pi.sh
./setup_raspberry_pi.sh
```

Alternatively, you can use the cross-platform Python setup:
```bash
python setup.py
```

The setup script will:
- Install required system packages
- Set up a Python virtual environment
- Install Python dependencies
- Download required models (Vosk and Whisper)
- Create necessary directories
- Configure the application

## Configuration

Edit `config/config.json` to customize:
- Wake word phrase
- Audio settings
- Speech recognition settings
- TTS voice and settings
- Groq API key
- Web interface settings

## Usage

1. Activate the virtual environment:
```bash
source venv/bin/activate
```

2. Run the voice assistant:
```bash
python main.py
```

3. Say "hi jarvis" to activate the assistant
4. When the assistant responds, speak your command
5. Wait for the assistant's response

To use the web interface:
1. Ensure the assistant is running
2. Open a web browser
3. Navigate to `http://<raspberry-pi-ip>:5000`

## Components

- `src/audio/` - Audio recording and playback
- `src/speech/` - Speech processing (wake word, STT, TTS)
- `config/` - Configuration files
- `models/` - Downloaded model files
- `main.py` - Main application entry point
- `setup_raspberry_pi.sh` - Installation script

## Troubleshooting

### Windows Issues

1. **Audio Issues**
   - Ensure microphone and speakers are properly connected
   - Check Windows sound settings
   - Verify microphone permissions in Windows Privacy Settings
   - Test microphone in Windows Sound Control Panel

2. **Installation Issues**
   - Install Visual C++ Build Tools if PyAudio installation fails
   - Run setup_windows.bat as administrator if permission errors occur
   - Ensure Python is added to PATH during installation

### Raspberry Pi Issues

1. **Audio Issues**
   - Ensure microphone and speakers are properly connected
   - Check audio levels using `alsamixer`
   - Verify permissions for audio devices
   - Run `sudo raspi-config` to configure audio settings

2. **Model Downloads**
   - If model downloads fail, manually download from:
     - Vosk: https://alphacephei.com/vosk/models
     - Whisper: https://huggingface.co/ggerganov/whisper.cpp

3. **Performance**
   - If running slowly, try:
     - Using the tiny Whisper model (default)
     - Reducing audio quality in config
     - Closing unnecessary applications

## License

MIT License - See LICENSE file for details
