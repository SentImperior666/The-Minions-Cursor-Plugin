"""
Twilio API client for phone call management.

Provides interface to Twilio API for:
- Initiating outbound calls
- Managing call status
- Handling voice webhooks
"""

import os
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
import logging

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

logger = logging.getLogger(__name__)


class CallStatus(str, Enum):
    """Status of a Twilio call."""
    QUEUED = "queued"
    RINGING = "ringing"
    IN_PROGRESS = "in-progress"
    COMPLETED = "completed"
    BUSY = "busy"
    FAILED = "failed"
    NO_ANSWER = "no-answer"
    CANCELED = "canceled"


@dataclass
class CallInfo:
    """Information about a Twilio call."""
    call_sid: str
    status: CallStatus
    from_number: str
    to_number: str
    duration: Optional[int] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None


class TwilioAPI:
    """
    Interface to Twilio API for phone call operations.
    
    Handles outbound calls for the Minion's voice communication.
    
    Attributes:
        account_sid: Twilio Account SID
        auth_token: Twilio Auth Token
        from_number: Default number to call from
    """
    
    BASE_URL = "https://api.twilio.com/2010-04-01"
    
    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ):
        """
        Initialize the Twilio API client.
        
        Args:
            account_sid: Twilio Account SID. Uses TWILIO_ACCOUNT_SID env var if not provided.
            auth_token: Twilio Auth Token. Uses TWILIO_AUTH_TOKEN env var if not provided.
            from_number: Phone number to call from. Uses TWILIO_FROM_NUMBER env var if not provided.
        """
        self.account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN")
        self.from_number = from_number or os.getenv("TWILIO_FROM_NUMBER")
        
        if HTTPX_AVAILABLE and self.account_sid and self.auth_token:
            self._client = httpx.Client(
                base_url=self.BASE_URL,
                auth=(self.account_sid, self.auth_token),
                timeout=30.0,
            )
            self._async_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                auth=(self.account_sid, self.auth_token),
                timeout=30.0,
            )
        else:
            self._client = None
            self._async_client = None
            if not HTTPX_AVAILABLE:
                logger.warning("httpx package not installed. Running in mock mode.")
            elif not self.account_sid or not self.auth_token:
                logger.warning("No Twilio credentials provided. Running in mock mode.")
    
    def _is_available(self) -> bool:
        """Check if the Twilio client is available."""
        return self._client is not None
    
    def initiate_call(
        self,
        to_number: str,
        webhook_url: str,
        status_callback_url: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> CallInfo:
        """
        Initiate an outbound phone call.
        
        Args:
            to_number: Phone number to call (E.164 format).
            webhook_url: URL for TwiML instructions when call connects.
            status_callback_url: URL for status callbacks.
            from_number: Phone number to call from. Uses default if not provided.
            
        Returns:
            CallInfo with the initiated call details.
        """
        from_num = from_number or self.from_number
        
        if not self._is_available():
            logger.info("Mock: Initiating call from %s to %s", from_num, to_number)
            return CallInfo(
                call_sid="mock_call_sid",
                status=CallStatus.QUEUED,
                from_number=from_num or "+15551234567",
                to_number=to_number,
            )
        
        response = self._client.post(
            f"/Accounts/{self.account_sid}/Calls.json",
            data={
                "To": to_number,
                "From": from_num,
                "Url": webhook_url,
                "StatusCallback": status_callback_url,
                "StatusCallbackMethod": "POST",
            },
        )
        response.raise_for_status()
        
        data = response.json()
        return CallInfo(
            call_sid=data["sid"],
            status=CallStatus(data["status"]),
            from_number=data["from"],
            to_number=data["to"],
        )
    
    async def initiate_call_async(
        self,
        to_number: str,
        webhook_url: str,
        status_callback_url: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> CallInfo:
        """
        Async version of initiate_call().
        
        Args:
            to_number: Phone number to call (E.164 format).
            webhook_url: URL for TwiML instructions when call connects.
            status_callback_url: URL for status callbacks.
            from_number: Phone number to call from.
            
        Returns:
            CallInfo with the initiated call details.
        """
        from_num = from_number or self.from_number
        
        if not self._is_available():
            logger.info("Mock: Initiating call async from %s to %s", from_num, to_number)
            return CallInfo(
                call_sid="mock_call_sid",
                status=CallStatus.QUEUED,
                from_number=from_num or "+15551234567",
                to_number=to_number,
            )
        
        response = await self._async_client.post(
            f"/Accounts/{self.account_sid}/Calls.json",
            data={
                "To": to_number,
                "From": from_num,
                "Url": webhook_url,
                "StatusCallback": status_callback_url,
                "StatusCallbackMethod": "POST",
            },
        )
        response.raise_for_status()
        
        data = response.json()
        return CallInfo(
            call_sid=data["sid"],
            status=CallStatus(data["status"]),
            from_number=data["from"],
            to_number=data["to"],
        )
    
    def get_call_status(self, call_sid: str) -> CallInfo:
        """
        Get the current status of a call.
        
        Args:
            call_sid: SID of the call to check.
            
        Returns:
            CallInfo with current call status.
        """
        if not self._is_available():
            return CallInfo(
                call_sid=call_sid,
                status=CallStatus.IN_PROGRESS,
                from_number="+15551234567",
                to_number="+15559876543",
            )
        
        response = self._client.get(
            f"/Accounts/{self.account_sid}/Calls/{call_sid}.json"
        )
        response.raise_for_status()
        
        data = response.json()
        return CallInfo(
            call_sid=data["sid"],
            status=CallStatus(data["status"]),
            from_number=data["from"],
            to_number=data["to"],
            duration=int(data["duration"]) if data.get("duration") else None,
            start_time=data.get("start_time"),
            end_time=data.get("end_time"),
        )
    
    def end_call(self, call_sid: str) -> CallInfo:
        """
        End an in-progress call.
        
        Args:
            call_sid: SID of the call to end.
            
        Returns:
            CallInfo with updated status.
        """
        if not self._is_available():
            logger.info("Mock: Ending call %s", call_sid)
            return CallInfo(
                call_sid=call_sid,
                status=CallStatus.COMPLETED,
                from_number="+15551234567",
                to_number="+15559876543",
            )
        
        response = self._client.post(
            f"/Accounts/{self.account_sid}/Calls/{call_sid}.json",
            data={"Status": "completed"},
        )
        response.raise_for_status()
        
        data = response.json()
        return CallInfo(
            call_sid=data["sid"],
            status=CallStatus(data["status"]),
            from_number=data["from"],
            to_number=data["to"],
        )
    
    def generate_twiml_say(
        self,
        text: str,
        voice: str = "Polly.Matthew",
        language: str = "en-US",
    ) -> str:
        """
        Generate TwiML for speaking text.
        
        Args:
            text: Text to speak.
            voice: Twilio voice to use.
            language: Language code.
            
        Returns:
            TwiML XML string.
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="{voice}" language="{language}">{text}</Say>
</Response>'''
    
    def generate_twiml_stream(
        self,
        websocket_url: str,
    ) -> str:
        """
        Generate TwiML for bidirectional audio streaming.
        
        This enables real-time audio streaming to/from the call,
        which is used for ElevenLabs voice synthesis.
        
        Args:
            websocket_url: WebSocket URL for audio streaming.
            
        Returns:
            TwiML XML string.
        """
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Connect>
        <Stream url="{websocket_url}">
            <Parameter name="minion" value="true"/>
        </Stream>
    </Connect>
</Response>'''
