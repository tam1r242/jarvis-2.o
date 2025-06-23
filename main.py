import json
import os
import signal
import sys
import time
import threading
from typing import Optional
from contextlib import ExitStack

from src.audio.recorder import AudioRecorder
from src.audio.player import AudioPlayer
from src.speech.keywords import KeywordDetector
from src.speech.stt import SpeechToText
from src.speech.tts import TextToSpeech
from src.config import config

class VoiceAssistant:
    def __init__(self):
        self.running = False
        self.exit_stack = ExitStack()
        self.lock = threading.Lock()
        self.error_count = 0
        self.MAX_ERRORS = 3
        
        # Initialize components using context managers
        self.recorder = self.exit_stack.enter_context(AudioRecorder())
        self.player = self.exit_stack.enter_context(AudioPlayer())
        self.keyword_detector = self.exit_stack.enter_context(KeywordDetector())
        self.stt = self.exit_stack.enter_context(SpeechToText())
        self.tts = self.exit_stack.enter_context(TextToSpeech())
        
        self.setup_signal_handlers()

    def setup_signal_handlers(self) -> None:
        """Setup handlers for graceful shutdown."""
        for sig in [signal.SIGINT, signal.SIGTERM]:
            signal.signal(sig, self.signal_handler)

    def signal_handler(self, signum, frame) -> None:
        """Handle shutdown signals."""
        print("\nShutting down gracefully...")
        with self.lock:
            self.running = False

    def speak(self, text: str) -> None:
        """Speak text with Iron Man style voice."""
        if not text:
            return
            
        print(f"Assistant: {text}")
        try:
            self.tts.speak(text)
        except Exception as e:
            print(f"Error during speech synthesis: {str(e)}")
            with self.lock:
                self.error_count += 1

    def process_command(self, audio_data: np.ndarray) -> None:
        """Process the command after wake word detection."""
        if audio_data is None or len(audio_data) == 0:
            self.speak("No audio data received.")
            return
            
        try:
            # Transcribe audio to text
            text = self.stt.transcribe(audio_data)
            
            if not text:
                self.speak("I couldn't understand that. Could you please repeat?")
                return

            print(f"User said: {text}")

            # Process the command using Groq integration
            try:
                from app import ask_groq
                
                # Add retry logic for API calls
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        response = ask_groq(text)
                        if response:
                            self.speak(response)
                            return
                        break
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(1)
                        
                self.speak("I'm having trouble processing that request.")
                
            except ImportError:
                self.speak("Groq integration is not available.")
            except Exception as e:
                print(f"Error processing command: {str(e)}")
                self.speak("I encountered an error while processing your request.")
                with self.lock:
                    self.error_count += 1
                    
        except Exception as e:
            print(f"Error in command processing pipeline: {str(e)}")
            self.speak("I encountered an unexpected error.")
            with self.lock:
                self.error_count += 1

    def run(self) -> None:
        """Run the voice assistant with continuous wake word detection."""
        print("Starting voice assistant...")
        
        try:
            # Initialize audio pipeline
            if not self._initialize_audio():
                print("Failed to initialize audio pipeline")
                return
                
            self.speak("Voice assistant initialized. Listening for wake word.")
            
            # Main processing loop
            audio_config = config.get('audio')
            chunk_duration = audio_config['chunk_size'] / audio_config['sample_rate']
            
            while self.running:
                try:
                    # Reset error count periodically
                    with self.lock:
                        if self.error_count >= self.MAX_ERRORS:
                            print("Too many errors, restarting audio pipeline...")
                            self._reinitialize_audio()
                            self.error_count = 0
                    
                    # Get audio data
                    audio_data = self.recorder.stop_recording()
                    if audio_data is None:
                        continue

                    # Check for wake word
                    if self.keyword_detector.process_audio(audio_data):
                        self.speak("Yes, how can I help you?")
                        
                        # Record command with timeout
                        command_audio = self.recorder.record_fixed_duration()
                        if command_audio is not None:
                            self.process_command(command_audio)
                        
                        # Reset for next command
                        self._reinitialize_audio()
                    else:
                        # Continue listening
                        self.recorder.start_recording()

                    # Prevent CPU overuse
                    time.sleep(chunk_duration / 2)
                    
                except Exception as e:
                    print(f"Error in main loop: {str(e)}")
                    with self.lock:
                        self.error_count += 1
                    time.sleep(1)  # Prevent rapid error loops

        except Exception as e:
            print(f"Critical error: {str(e)}")
        finally:
            self.cleanup()
            
    def _initialize_audio(self) -> bool:
        """Initialize the audio pipeline."""
        try:
            self.running = True
            if not self.recorder.start_recording():
                return False
            if not self.keyword_detector.start_listening():
                return False
            return True
        except Exception as e:
            print(f"Error initializing audio: {str(e)}")
            return False
            
    def _reinitialize_audio(self) -> None:
        """Reinitialize the audio pipeline."""
        self.recorder.stop_recording()
        self.keyword_detector.reset()
        self.recorder.start_recording()

    def cleanup(self) -> None:
        """Clean up all resources."""
        try:
            with self.lock:
                self.running = False
            
            # Close all resources using context manager stack
            self.exit_stack.close()
            
        except Exception as e:
            print(f"Error during cleanup: {str(e)}")

def main() -> None:
    """Main entry point for the voice assistant."""
    try:
        # Ensure required directories exist
        os.makedirs("models", exist_ok=True)
        
        # Create and run voice assistant
        with VoiceAssistant() as assistant:
            assistant.run()
            
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
