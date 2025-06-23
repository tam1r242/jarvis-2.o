"""
Speech processing package for wake word detection, STT, and TTS functionality.
"""

from .keywords import KeywordDetector
from .stt import SpeechToText
from .tts import TextToSpeech

__all__ = ['KeywordDetector', 'SpeechToText', 'TextToSpeech']
