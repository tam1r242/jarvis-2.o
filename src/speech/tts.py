import ctypes
import os
import platform
import numpy as np
import sounddevice as sd
from typing import Optional, Dict
from pathlib import Path
from threading import Lock
import tempfile
import soundfile as sf
from ctypes import (
    CDLL, c_int, c_char_p, c_wchar_p, 
    c_void_p, c_float, POINTER, Structure
)
from ..config import config

# Define espeak structures
class SpeakAudioStruct(Structure):
    _fields_ = [
        ("data", POINTER(c_int)),
        ("length", c_int),
        ("sampling_rate", c_int),
    ]

class EspeakVoice(Structure):
    _fields_ = [
        ("name", c_char_p),
        ("languages", c_char_p),
        ("identifier", c_char_p),
        ("gender", c_int),  # 1=male, 2=female
        ("age", c_int),
        ("variant", c_int),
    ]

class TextToSpeech:
    # Load espeak-ng library
    if platform.system().lower() == "windows":
        _lib_paths = [
            os.path.join(os.environ.get('PROGRAMFILES', 'C:/Program Files'), 'eSpeak NG', 'libespeak-ng.dll'),
            os.path.join(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)'), 'eSpeak NG', 'libespeak-ng.dll'),
            'libespeak-ng.dll'  # Search in PATH
        ]
        for lib_path in _lib_paths:
            try:
                _lib = CDLL(lib_path)
                break
            except OSError:
                continue
        else:
            raise OSError("Could not find espeak-ng library. Please ensure it's installed.")
    else:
        # Linux/Unix systems
        try:
            _lib = CDLL('libespeak-ng.so.1')
        except OSError:
            _lib = CDLL('libespeak-ng.so')

    # Initialize function signatures
    _lib.espeak_Initialize.argtypes = [c_int, c_int, c_char_p, c_int]
    _lib.espeak_Initialize.restype = c_int
    
    _lib.espeak_SetVoiceByName.argtypes = [c_char_p]
    _lib.espeak_SetVoiceByName.restype = c_int
    
    _lib.espeak_Synth.argtypes = [c_void_p, c_int, c_int, c_int, c_int, c_int, POINTER(c_int), c_void_p]
    _lib.espeak_Synth.restype = c_int
    
    _lib.espeak_SetParameter.argtypes = [c_int, c_int, c_int]
    _lib.espeak_SetParameter.restype = c_int
    
    _lib.espeak_ListVoices.argtypes = [POINTER(EspeakVoice)]
    _lib.espeak_ListVoices.restype = POINTER(POINTER(EspeakVoice))

    # Constants
    AUDIO_OUTPUT_RETRIEVAL = 2
    RATE_MINIMUM = 80
    RATE_MAXIMUM = 450
    VOLUME_MINIMUM = 0
    VOLUME_MAXIMUM = 200
    
    # Parameter constants
    RATE = 3
    VOLUME = 1
    PITCH = 2
    RANGE = 4
    def __init__(self):
        """Initialize text-to-speech with espeak-ng."""
        # Get config from singleton
        tts_config = config.get('tts')
        audio_config = config.get('audio')
        
        self.voice = tts_config['voice']
        self.rate = min(max(tts_config['rate'], self.RATE_MINIMUM), self.RATE_MAXIMUM)
        # Convert 0-1 volume to espeak's 0-200 range
        self.volume = int(min(max(tts_config['volume'], 0), 1) * 200)
        self.sample_rate = audio_config['sample_rate']
        
        self.lock = Lock()
        self.temp_dir = tempfile.mkdtemp(prefix='tts_')
        
        # Initialize espeak-ng
        self._initialize_espeak()
        
    def _initialize_espeak(self) -> None:
        """Initialize espeak-ng library."""
        try:
            # Initialize with output mode for audio retrieval
            result = self._lib.espeak_Initialize(
                self.AUDIO_OUTPUT_RETRIEVAL,  # Output mode
                0,  # Buffer length (0 = default)
                None,  # Path to espeak-data (None = default)
                0  # Options (0 = default)
            )
            if result < 0:
                raise Exception("Failed to initialize espeak-ng")

            # Set voice
            result = self._lib.espeak_SetVoiceByName(self.voice.encode())
            if result < 0:
                raise Exception(f"Failed to set voice: {self.voice}")

            print(f"Initialized eSpeak-NG with voice: {self.voice}")
            
        except Exception as e:
            if platform.system().lower() == "windows":
                raise Exception(
                    "eSpeak-NG initialization failed. Please ensure it's installed and in PATH.\n"
                    "Download from: https://github.com/espeak-ng/espeak-ng/releases\n"
                    f"Error: {str(e)}"
                )
            else:
                raise Exception(
                    "eSpeak-NG initialization failed. Please install with:\n"
                    "sudo apt-get install espeak-ng libespeak-ng-dev\n"
                    f"Error: {str(e)}"
                )

    def speak(self, text: str, blocking: bool = True) -> Optional[np.ndarray]:
        """
        Convert text to speech and play it.
        
        Args:
            text: Text to convert to speech
            blocking: Whether to block until audio finishes playing
            
        Returns:
            np.ndarray: Audio data if successful, None otherwise
        """
        if not text:
            print("Empty text provided to TTS")
            return None
            
        with self.lock:
            try:
                # Prepare text
                text_bytes = text.encode('utf-8')
                text_length = len(text_bytes)
                
                # Prepare audio buffer structure
                audio_data = SpeakAudioStruct()
                audio_data.data = None
                audio_data.length = 0
                audio_data.sampling_rate = self.sample_rate
                
                # Set synthesis parameters
                flags = c_int(0)  # No special flags
                position = c_int(0)  # Start position
                position_type = c_int(0)  # Position type (0 = character)
                end_position = c_int(0)  # End position (0 = until end)
                unique_identifier = c_int(0)  # Unique identifier for callback
                user_data = c_void_p(None)  # User data for callback
                
                # Synthesize speech
                result = self._lib.espeak_Synth(
                    text_bytes,  # Text
                    text_length,  # Text length
                    position,  # Position
                    position_type,  # Position type
                    end_position,  # End position
                    flags,  # Flags
                    POINTER(c_int)(unique_identifier),  # Unique identifier
                    user_data  # User data
                )
                
                if result < 0:
                    raise Exception("Speech synthesis failed")
                
                # Get the synthesized audio data
                audio_array = np.ctypeslib.as_array(
                    audio_data.data,
                    shape=(audio_data.length,)
                )
                
                # Convert to float32 and normalize
                audio_float = audio_array.astype(np.float32) / 32768.0
                
                # Play the audio
                if blocking:
                    sd.play(audio_float, self.sample_rate)
                    sd.wait()
                else:
                    sd.play(audio_float, self.sample_rate)
                
                return audio_float
                
            except Exception as e:
                print(f"TTS error: {str(e)}")
                return None

    def update_voice(self, voice: str) -> None:
        """Update the TTS voice."""
        with self.lock:
            result = self._lib.espeak_SetVoiceByName(voice.encode())
            if result < 0:
                raise Exception(f"Failed to set voice: {voice}")
            self.voice = voice
            
    def update_rate(self, rate: int) -> None:
        """Update the speech rate."""
        with self.lock:
            self.rate = min(max(rate, self.RATE_MINIMUM), self.RATE_MAXIMUM)
            self._lib.espeak_SetParameter(3, self.rate, 0)  # 3 is rate parameter
            
    def update_volume(self, volume: float) -> None:
        """Update the speech volume (0-1)."""
        with self.lock:
            self.volume = int(min(max(volume, 0), 1) * 200)
            self._lib.espeak_SetParameter(1, self.volume, 0)  # 1 is volume parameter
            
    def get_available_voices(self) -> Dict[str, Dict[str, str]]:
        """Get list of available espeak-ng voices with details."""
        voices = {}
        try:
            voice_list = self._lib.espeak_ListVoices(None)
            if not voice_list:
                return voices
                
            index = 0
            while voice_list[index]:
                voice = voice_list[index].contents
                name = voice.name.decode('utf-8')
                voices[name] = {
                    'name': name,
                    'language': voice.languages.decode('utf-8'),
                    'identifier': voice.identifier.decode('utf-8') if voice.identifier else '',
                    'gender': 'M' if voice.gender == 1 else 'F' if voice.gender == 2 else 'N',
                    'age': str(voice.age) if voice.age else ''
                }
                index += 1
                
        except Exception as e:
            print(f"Error getting voices: {str(e)}")
            
        return voices
            
    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            shutil.rmtree(self.temp_dir)
        except Exception as e:
            print(f"Error cleaning up TTS temp directory: {str(e)}")
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
