import sounddevice as sd
import numpy as np
from typing import Optional
import queue
import threading
from threading import Lock
import time
from ..config import config

class AudioRecorder:
    def __init__(self):
        # Get config from singleton
        audio_config = config.get('audio')
        self.sample_rate = audio_config['sample_rate']
        self.channels = audio_config['channels']
        self.chunk_size = audio_config['chunk_size']
        self.record_seconds = audio_config['record_seconds']
        
        # Thread-safe queue with size limit to prevent memory issues
        self.audio_queue = queue.Queue(maxsize=100)  # Limit queue size
        self.is_recording = False
        self.lock = Lock()  # For thread-safe state management
        self.stream: Optional[sd.InputStream] = None
        self._overflow_count = 0
        self.MAX_OVERFLOW_COUNT = 5

    def callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        try:
            if status:
                print(f'Audio callback status: {status}')
                if status.input_overflow:
                    with self.lock:
                        self._overflow_count += 1
                    if self._overflow_count >= self.MAX_OVERFLOW_COUNT:
                        print("Too many input overflows, stopping recording")
                        self.stop_recording()
                        return
                
            # Normalize audio data
            normalized_data = self.normalize_audio(indata.copy())
            
            try:
                # Non-blocking put with timeout
                self.audio_queue.put(normalized_data, timeout=0.1)
            except queue.Full:
                print("Audio buffer full, dropping oldest chunk")
                try:
                    self.audio_queue.get_nowait()  # Remove oldest chunk
                    self.audio_queue.put(normalized_data)
                except (queue.Empty, queue.Full):
                    pass  # Skip this chunk if queue operations fail
                    
        except Exception as e:
            print(f"Error in audio callback: {str(e)}")

    def normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Normalize audio data and ensure correct format."""
        # Convert to mono if multi-channel
        if len(audio_data.shape) > 1 and audio_data.shape[1] > 1:
            audio_data = np.mean(audio_data, axis=1, keepdims=True)
        
        # Normalize amplitude
        max_val = np.abs(audio_data).max()
        if max_val > 0:
            audio_data = audio_data / max_val
            
        return audio_data

    def start_recording(self):
        """Start recording audio in a non-blocking way."""
        with self.lock:
            if self.is_recording:
                return  # Already recording
                
            self.is_recording = True
            self._overflow_count = 0
            
            try:
                self.stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=self.callback,
                    blocksize=self.chunk_size,
                    dtype=np.float32
                )
                self.stream.start()
            except Exception as e:
                self.is_recording = False
                raise Exception(f"Failed to start recording: {str(e)}")

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return the recorded audio data."""
        with self.lock:
            if not self.is_recording:
                return None

            self.is_recording = False
            
            try:
                if self.stream is not None:
                    self.stream.stop()
                    self.stream.close()
                    self.stream = None
            except Exception as e:
                print(f"Error stopping stream: {str(e)}")

        # Collect all audio data from the queue with timeout
        audio_data = []
        timeout = time.time() + 1.0  # 1 second timeout
        
        while time.time() < timeout:
            try:
                chunk = self.audio_queue.get_nowait()
                audio_data.append(chunk)
            except queue.Empty:
                break

        if not audio_data:
            return None

        try:
            return np.concatenate(audio_data, axis=0)
        except Exception as e:
            print(f"Error concatenating audio data: {str(e)}")
            return None

    def record_fixed_duration(self) -> Optional[np.ndarray]:
        """Record audio for a fixed duration specified in config."""
        print(f"Recording for {self.record_seconds} seconds...")
        
        try:
            audio_data = sd.rec(
                int(self.sample_rate * self.record_seconds),
                samplerate=self.sample_rate,
                channels=self.channels,
                blocking=True,
                dtype=np.float32
            )
            
            if audio_data is not None:
                audio_data = self.normalize_audio(audio_data)
                print("Recording finished.")
                return audio_data
            
        except Exception as e:
            print(f"Error during fixed duration recording: {str(e)}")
        
        return None
        
    def cleanup(self):
        """Clean up resources."""
        self.stop_recording()
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
