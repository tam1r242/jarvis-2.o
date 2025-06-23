from vosk import Model, KaldiRecognizer
import json
import numpy as np
import os
from typing import Optional, Callable
from threading import Lock
from ..config import config

class KeywordDetector:
    def __init__(self, model_path: str = "models/vosk-model"):
        """
        Initialize keyword detector with Vosk.
        
        Args:
            model_path: Path to the Vosk model directory
        """
        # Get config from singleton
        speech_config = config.get('speech')
        audio_config = config.get('audio')
        
        self.wake_phrase = speech_config['wake_phrase'].lower()
        self.threshold = speech_config['keyword_threshold']
        self.sample_rate = audio_config['sample_rate']
        
        # Validate and initialize model
        self._validate_model_path(model_path)
        self._init_model(model_path)
        
        self.lock = Lock()
        self.is_listening = False
        self._last_detected = None
        self._callback: Optional[Callable[[str], None]] = None
        
    def _validate_model_path(self, model_path: str) -> None:
        """Validate the Vosk model path and files."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(
                f"Vosk model directory not found at {model_path}. "
                "Please download the model from https://alphacephei.com/vosk/models"
            )
            
        required_files = ['final.mdl', 'conf/mfcc.conf', 'graph/HCLG.fst']
        for file in required_files:
            full_path = os.path.join(model_path, file)
            if not os.path.exists(full_path):
                raise FileNotFoundError(
                    f"Required model file '{file}' not found in {model_path}. "
                    "The model directory appears to be incomplete or corrupted."
                )
                
    def _init_model(self, model_path: str) -> None:
        """Initialize the Vosk model and recognizer."""
        try:
            self.model = Model(model_path)
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)  # Enable word timing
        except Exception as e:
            raise Exception(f"Failed to initialize Vosk model: {str(e)}")

    def process_audio(self, audio_data: np.ndarray) -> bool:
        """
        Process audio data and check for wake word.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            bool: True if wake word was detected
        """
        if not self.is_listening:
            return False
            
        try:
            # Ensure audio data is in the correct format (16-bit integers)
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)
                
            audio_int16 = (audio_data * 32768).astype(np.int16).tobytes()
            
            if self.recognizer.AcceptWaveform(audio_int16):
                result = json.loads(self.recognizer.Result())
                if 'text' in result and result['text']:
                    detected_text = result['text'].lower()
                    confidence = self._calculate_confidence(detected_text)
                    
                    if self.wake_phrase in detected_text and confidence >= self.threshold:
                        with self.lock:
                            self._last_detected = detected_text
                            if self._callback:
                                try:
                                    self._callback(detected_text)
                                except Exception as e:
                                    print(f"Error in wake word callback: {str(e)}")
                        return True
            
            return False
            
        except Exception as e:
            print(f"Error processing audio: {str(e)}")
            return False
            
    def _calculate_confidence(self, text: str) -> float:
        """Calculate confidence score for wake word detection."""
        # Simple confidence calculation based on word count
        # Could be improved with more sophisticated metrics
        words = text.split()
        if not words:
            return 0.0
            
        wake_words = self.wake_phrase.split()
        matches = sum(1 for w in wake_words if w in words)
        return matches / len(wake_words)

    def start_listening(self, callback: Optional[Callable[[str], None]] = None) -> bool:
        """
        Start continuous listening for wake word.
        
        Args:
            callback: Optional callback function to call when wake word is detected
            
        Returns:
            bool: True if successfully started listening
        """
        try:
            with self.lock:
                if self.is_listening:
                    return True  # Already listening
                    
                self.is_listening = True
                self._last_detected = None
                self._callback = callback
                self.recognizer.Reset()  # Reset the recognizer state
                return True
                
        except Exception as e:
            print(f"Error starting wake word detection: {str(e)}")
            self.is_listening = False
            return False
        
    def stop_listening(self) -> None:
        """Stop listening for wake word."""
        with self.lock:
            self.is_listening = False
            self._last_detected = None
            self._callback = None

    def get_last_detected(self) -> Optional[str]:
        """Get the last detected phrase that contained the wake word."""
        with self.lock:
            return self._last_detected

    def reset(self) -> None:
        """Reset the detector state."""
        with self.lock:
            self.recognizer.Reset()
            self._last_detected = None
            
    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_listening()
        self.reset()
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
