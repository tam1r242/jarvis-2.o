import sounddevice as sd
import numpy as np
import threading
from threading import Lock, Event
from typing import Optional
from ..config import config

class AudioPlayer:
    def __init__(self):
        # Get config from singleton
        audio_config = config.get('audio')
        self.sample_rate = audio_config['sample_rate']
        self.channels = audio_config['channels']
        
        self.lock = Lock()
        self.is_playing = False
        self._play_thread: Optional[threading.Thread] = None
        self._stop_event = Event()

    def play(self, audio_data: np.ndarray, blocking: bool = False) -> bool:
        """
        Play audio data. Can be blocking or non-blocking.
        
        Args:
            audio_data: numpy array of audio samples
            blocking: if True, block until playback is complete
            
        Returns:
            bool: True if playback started successfully
        """
        try:
            # Ensure correct data format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalize if needed
            max_val = np.abs(audio_data).max()
            if max_val > 1.0:
                audio_data = audio_data / max_val

            with self.lock:
                if self.is_playing:
                    self.stop()  # Stop any existing playback
                
                self.is_playing = True
                self._stop_event.clear()
                
                if blocking:
                    return self._play_blocking(audio_data)
                else:
                    self._play_thread = threading.Thread(
                        target=self._play_blocking,
                        args=(audio_data,),
                        daemon=True  # Ensure thread doesn't prevent program exit
                    )
                    self._play_thread.start()
                    return True
                    
        except Exception as e:
            print(f"Error starting playback: {str(e)}")
            self.is_playing = False
            return False

    def _play_blocking(self, audio_data: np.ndarray) -> bool:
        """Internal method to play audio in a blocking way."""
        try:
            with sd.OutputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32
            ) as stream:
                stream.write(audio_data)
                while stream.active and not self._stop_event.is_set():
                    sd.sleep(100)  # Sleep to prevent busy waiting
                return True
        except Exception as e:
            print(f"Error during playback: {str(e)}")
            return False
        finally:
            with self.lock:
                self.is_playing = False

    def stop(self):
        """Stop any ongoing playback."""
        with self.lock:
            if self.is_playing:
                self._stop_event.set()
                sd.stop()
                self.is_playing = False
                
                if self._play_thread and self._play_thread.is_alive():
                    self._play_thread.join(timeout=1.0)  # Wait up to 1 second
                    if self._play_thread.is_alive():
                        print("Warning: Audio playback thread did not stop cleanly")

    def wait_until_done(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for any non-blocking playback to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            bool: True if playback completed, False if timed out
        """
        if self._play_thread and self._play_thread.is_alive():
            self._play_thread.join(timeout=timeout)
            return not self._play_thread.is_alive()
        return True
        
    def cleanup(self):
        """Clean up resources."""
        self.stop()
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
