from faster_whisper import WhisperModel
import numpy as np
from typing import Optional
import os
from threading import Lock
from ..config import config

class SpeechToText:
    def __init__(self):
        """Initialize speech-to-text with faster-whisper."""
        # Get config from singleton
        whisper_config = config.get('whisper')
        self.model_name = whisper_config['model']
        self.language = whisper_config['language']
        
        self.lock = Lock()
        self.model = None
        
        # Initialize model
        self._init_model()

    def _init_model(self) -> None:
        """Initialize faster-whisper model."""
        try:
            model_dir = os.path.join("models", "whisper")
            os.makedirs(model_dir, exist_ok=True)
            
            # Initialize model with compute type optimized for the device
            self.model = WhisperModel(
                self.model_name,
                device="auto",  # Will use CUDA if available, else CPU
                compute_type="auto",  # Will select optimal compute type
                download_root=model_dir
            )
            print(f"Initialized Whisper model: {self.model_name}")
        except Exception as e:
            raise Exception(f"Failed to initialize Whisper model: {str(e)}")

    def transcribe(self, audio_data: np.ndarray) -> Optional[str]:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio data as numpy array
            
        Returns:
            str: Transcribed text or None if transcription failed
        """
        if self.model is None:
            print("Model not initialized")
            return None
            
        try:
            with self.lock:
                # Ensure audio data is in the correct format (32-bit float)
                if audio_data.dtype != np.float32:
                    audio_data = audio_data.astype(np.float32)
                
                # Normalize audio if needed
                max_val = np.abs(audio_data).max()
                if max_val > 1.0:
                    audio_data = audio_data / max_val
                
                # Perform transcription
                segments, _ = self.model.transcribe(
                    audio_data,
                    language=self.language,
                    beam_size=5,
                    vad_filter=True,  # Filter out non-speech
                    vad_parameters=dict(
                        min_silence_duration_ms=500,
                        speech_pad_ms=500
                    )
                )
                
                # Combine all segments
                text = " ".join(segment.text for segment in segments).strip()
                return text if text else None
                
        except Exception as e:
            print(f"Transcription error: {str(e)}")
            # Attempt to reinitialize model on failure
            try:
                self._init_model()
            except Exception as e2:
                print(f"Failed to reinitialize model: {str(e2)}")
            return None

    def update_language(self, language: str) -> None:
        """Update the transcription language."""
        with self.lock:
            self.language = language
            
    def cleanup(self) -> None:
        """Clean up resources."""
        with self.lock:
            if self.model is not None:
                del self.model
                self.model = None
            
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
