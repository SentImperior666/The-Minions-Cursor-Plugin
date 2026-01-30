"""
OpenAI API client for LLM operations.

Provides interface to OpenAI's chat completion API for:
- Chat summarization
- Instruction processing
- General LLM queries

Copied from Victor's implementation (vgh workspace).
"""

import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import logging

try:
    from openai import OpenAI, AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class CompletionResult:
    """Result from an OpenAI completion request."""
    content: str
    model: str
    usage: Dict[str, int]
    finish_reason: str


class OpenAIAPI:
    """
    Interface to OpenAI API for LLM operations.
    
    Handles chat completions for summarization and instruction processing.
    
    Attributes:
        api_key: OpenAI API key
        model: Model to use for completions (default: gpt-4o-mini)
        max_tokens: Maximum tokens for completion responses
    """
    
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_MAX_TOKENS = 2048
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
    ):
        """
        Initialize the OpenAI API client.
        
        Args:
            api_key: OpenAI API key. If not provided, uses OPENAI_API_KEY env var.
            model: Model to use for completions.
            max_tokens: Maximum tokens for responses.
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.max_tokens = max_tokens
        
        if OPENAI_AVAILABLE and self.api_key:
            self._client = OpenAI(api_key=self.api_key)
            self._async_client = AsyncOpenAI(api_key=self.api_key)
        else:
            self._client = None
            self._async_client = None
            if not OPENAI_AVAILABLE:
                logger.warning("OpenAI package not installed. Running in mock mode.")
            elif not self.api_key:
                logger.warning("No OpenAI API key provided. Running in mock mode.")
    
    def _is_available(self) -> bool:
        """Check if the OpenAI client is available."""
        return self._client is not None
    
    @property
    def is_configured(self) -> bool:
        """Check if the OpenAI client is configured."""
        return self._is_available()
    
    def complete(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """
        Generate a completion from chat messages.
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: Optional system prompt to prepend.
            temperature: Sampling temperature (0-2).
            
        Returns:
            CompletionResult with the generated content.
        """
        full_messages = []
        
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        
        full_messages.extend(messages)
        
        if not self._is_available():
            # Mock response for testing
            return CompletionResult(
                content="[Mock response - OpenAI not configured]",
                model=self.model,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                finish_reason="stop",
            )
        
        response = self._client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            max_tokens=self.max_tokens,
            temperature=temperature,
        )
        
        choice = response.choices[0]
        return CompletionResult(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    async def complete_async(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
    ) -> CompletionResult:
        """
        Async version of complete().
        
        Args:
            messages: List of message dicts with 'role' and 'content' keys.
            system_prompt: Optional system prompt to prepend.
            temperature: Sampling temperature (0-2).
            
        Returns:
            CompletionResult with the generated content.
        """
        full_messages = []
        
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        
        full_messages.extend(messages)
        
        if not self._is_available():
            return CompletionResult(
                content="[Mock response - OpenAI not configured]",
                model=self.model,
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                finish_reason="stop",
            )
        
        response = await self._async_client.chat.completions.create(
            model=self.model,
            messages=full_messages,
            max_tokens=self.max_tokens,
            temperature=temperature,
        )
        
        choice = response.choices[0]
        return CompletionResult(
            content=choice.message.content or "",
            model=response.model,
            usage={
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            },
            finish_reason=choice.finish_reason,
        )
    
    def summarize(
        self,
        text: str,
        max_length: int = 500,
        style: str = "concise",
    ) -> str:
        """
        Summarize the given text.
        
        Args:
            text: The text to summarize.
            max_length: Approximate maximum length of summary in words.
            style: Summary style - "concise", "detailed", or "bullet".
            
        Returns:
            The summarized text.
        """
        style_prompts = {
            "concise": "Provide a very concise summary focusing on key points.",
            "detailed": "Provide a detailed summary covering all important aspects.",
            "bullet": "Provide a summary as bullet points, highlighting key actions and decisions.",
        }
        
        system_prompt = f"""You are a helpful assistant that summarizes coding conversations.
{style_prompts.get(style, style_prompts['concise'])}
Keep the summary under {max_length} words.
Focus on: what was discussed, what was implemented, any problems encountered, and next steps if mentioned."""
        
        messages = [{"role": "user", "content": f"Please summarize this conversation:\n\n{text}"}]
        
        result = self.complete(messages, system_prompt=system_prompt, temperature=0.5)
        return result.content
    
    def process_instruction(
        self,
        instruction: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Process a user instruction and determine the appropriate action.
        
        Args:
            instruction: The user's instruction/command.
            context: Optional context about current state.
            
        Returns:
            Dict with 'action' and 'parameters' keys.
        """
        system_prompt = """You are a Minion assistant that processes voice commands.
Analyze the instruction and return a JSON response with:
- "action": one of ["stop", "forget", "spawn", "summarize", "unknown"]
- "parameters": any relevant parameters for the action
- "response": a brief acknowledgment to speak back

Examples:
- "stop" -> stop the current task
- "forget" -> clear memory/context
- "spawn" -> create a new minion
- "summarize" -> provide a summary"""

        content = instruction
        if context:
            content = f"Context: {context}\n\nInstruction: {instruction}"
        
        messages = [{"role": "user", "content": content}]
        
        result = self.complete(messages, system_prompt=system_prompt, temperature=0.3)
        
        # Try to parse as JSON, fallback to basic structure
        try:
            import json
            return json.loads(result.content)
        except (json.JSONDecodeError, TypeError):
            return {
                "action": "unknown",
                "parameters": {},
                "response": result.content,
            }
    
    # Alias for backward compatibility
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs: Any,
    ) -> Optional[CompletionResult]:
        """Alias for complete() for backward compatibility."""
        return self.complete(messages, temperature=temperature)
    
    def summarize_text(
        self,
        text: str,
        max_length: int = 200,
        context: Optional[str] = None,
    ) -> Optional[str]:
        """Alias for summarize() for backward compatibility."""
        return self.summarize(text, max_length=max_length, style="concise")
