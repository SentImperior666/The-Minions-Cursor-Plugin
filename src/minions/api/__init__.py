"""
API module - External service integrations.

Copied from Victor's implementations (vgh workspace - Task 2).
"""

from .openai_api import OpenAIAPI, CompletionResult
from .elevenlabs_api import ElevenLabsAPI, VoiceInfo, VoiceSettings
from .twilio_api import TwilioAPI, CallInfo, CallStatus

__all__ = [
    # OpenAI
    "OpenAIAPI",
    "CompletionResult",
    # ElevenLabs
    "ElevenLabsAPI",
    "VoiceInfo",
    "VoiceSettings",
    # Twilio
    "TwilioAPI",
    "CallInfo",
    "CallStatus",
]
