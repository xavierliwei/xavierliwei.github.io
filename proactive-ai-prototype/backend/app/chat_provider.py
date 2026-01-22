"""
Chat Provider Abstraction Layer.

This module defines the interface for chat providers and implements
both mock (for dev) and Claude API (for production) providers.

Supports both synchronous and streaming response generation.

Usage:
    # Development with mock responses
    provider = MockChatProvider()

    # Production with Claude API
    provider = ClaudeChatProvider(api_key="your-key", model="claude-haiku-3-5-20241022")

    # Streaming usage
    for chunk in provider.generate_response_stream(messages):
        print(chunk, end="", flush=True)
"""

from abc import ABC, abstractmethod
from typing import Optional, Generator, Iterator
from dataclasses import dataclass
import time


@dataclass
class ChatMessage:
    """A message in a conversation."""
    role: str  # "user" or "assistant"
    content: str


@dataclass
class ChatResponse:
    """Response from a chat provider."""
    content: str
    model: Optional[str] = None
    stop_reason: Optional[str] = None
    usage: Optional[dict] = None


class ChatProvider(ABC):
    """
    Abstract base class for chat providers.

    Implement this interface to add new chat backends
    (e.g., OpenAI, local models, etc.)
    """

    @abstractmethod
    def generate_response(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> ChatResponse:
        """
        Generate a response to a conversation.

        Args:
            messages: Conversation history
            system_prompt: System prompt to guide the model
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Returns:
            ChatResponse with generated content
        """
        pass

    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the model being used."""
        pass

    @abstractmethod
    def generate_response_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response to a conversation.

        Args:
            messages: Conversation history
            system_prompt: System prompt to guide the model
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1)

        Yields:
            Text chunks as they are generated
        """
        pass

    def supports_streaming(self) -> bool:
        """Check if this provider supports streaming."""
        return True


class MockChatProvider(ChatProvider):
    """
    Mock chat provider for development and testing.

    Returns predefined responses based on message patterns.
    Useful for development without API costs.
    """

    def __init__(self):
        """Initialize mock provider."""
        self.model_name = "mock-v1"

    def generate_response(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> ChatResponse:
        """Generate a mock response."""
        import random

        # Get last user message
        last_message = messages[-1].content.lower() if messages else ""

        # Topic-specific responses
        response = self._get_topic_response(last_message)
        if response:
            return ChatResponse(content=response, model=self.model_name)

        # Pattern-based responses
        response = self._get_pattern_response(last_message)
        if response:
            return ChatResponse(content=response, model=self.model_name)

        # Default response
        defaults = [
            "That's an interesting point! Could you tell me more about what aspect you'd like to focus on?",
            "I'd like to understand your question better. Are you looking for a conceptual explanation or practical guidance?",
            "Good question! To give you the most helpful answer, could you share more context about what you're working on?"
        ]
        return ChatResponse(content=random.choice(defaults), model=self.model_name)

    def get_model_name(self) -> str:
        """Return mock model name."""
        return self.model_name

    def generate_response_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> Generator[str, None, None]:
        """Generate a mock streaming response by yielding words with delays."""
        # Get the full response first
        response = self.generate_response(
            messages, system_prompt, max_tokens, temperature
        )
        content = response.content

        # Simulate streaming by yielding word by word
        words = content.split(' ')
        for i, word in enumerate(words):
            # Add space before word (except first)
            if i > 0:
                yield ' '
            yield word
            # Small delay to simulate generation
            time.sleep(0.03)

    def _get_topic_response(self, message: str) -> Optional[str]:
        """Get response for specific technical topics."""
        import random

        if any(term in message for term in ["kafka", "consumer", "producer", "partition"]):
            responses = [
                "Kafka's architecture is built around the concept of a distributed commit log. The key components are producers (which write data), consumers (which read data), and brokers (which store the data in partitions). What aspect would you like to explore?",
                "When working with Kafka, understanding consumer groups is crucial. Each partition is consumed by exactly one consumer in a group, enabling parallel processing while maintaining ordering within partitions.",
            ]
            return random.choice(responses)

        if any(term in message for term in ["distributed", "consensus", "replication"]):
            responses = [
                "In distributed systems, the fundamental challenge is maintaining consistency across nodes while handling network partitions. The CAP theorem tells us we can only guarantee two of three properties: Consistency, Availability, and Partition tolerance.",
                "Distributed consensus algorithms like Raft and Paxos solve the problem of getting multiple nodes to agree on a value. Raft is generally easier to understand - it elects a leader who coordinates all writes.",
            ]
            return random.choice(responses)

        if any(term in message for term in ["kubernetes", "k8s", "pod", "container"]):
            responses = [
                "Kubernetes orchestrates containerized applications across a cluster of nodes. The basic unit is a Pod (one or more containers), managed by higher-level objects like Deployments and StatefulSets.",
                "For cost optimization in Kubernetes, consider: right-sizing your pods, using Horizontal Pod Autoscaler, spot instances for fault-tolerant workloads, and namespace resource quotas.",
            ]
            return random.choice(responses)

        if any(term in message for term in ["machine learning", "ml", "model", "ai"]):
            responses = [
                "ML systems have unique infrastructure challenges: data pipelines, feature stores, model serving, and monitoring for drift. Are you focused on the training side or inference/serving?",
                "The ML lifecycle includes data preparation, feature engineering, model training, validation, deployment, and monitoring. Which stage are you working on?",
            ]
            return random.choice(responses)

        return None

    def _get_pattern_response(self, message: str) -> Optional[str]:
        """Get response based on message patterns."""
        import random

        if any(word in message for word in ["yes", "sure", "okay", "interested"]):
            responses = [
                "Great! Let's dive deeper. What aspect would you like to start with? I can explain the fundamentals or jump into more advanced topics.",
                "Excellent! I'm happy to help you understand this better. Would you prefer a high-level overview first?",
            ]
            return random.choice(responses)

        if any(word in message for word in ["no", "not now", "later", "busy"]):
            responses = [
                "No problem! I'll keep this in mind for later. Feel free to ask me anything else whenever you're ready.",
                "Understood! I'll queue this for when you have more time.",
            ]
            return random.choice(responses)

        if any(word in message for word in ["more", "detail", "explain", "how", "why"]):
            responses = [
                "Let me break this down further. The fundamental concept involves several interconnected ideas. Would you like me to elaborate on any specific aspect?",
                "Happy to go deeper! The key insight here is understanding the 'why' behind the design decisions. Which aspect interests you most?",
            ]
            return random.choice(responses)

        if any(word in message for word in ["example", "show", "demo", "code"]):
            responses = [
                "Here's a practical example: Imagine a system processing thousands of events per second. The challenge is ensuring each event is processed exactly once, even when failures occur.",
                "Let me give you a concrete example. Companies like Netflix and Uber use patterns like idempotent operations and transaction logs to solve these challenges.",
            ]
            return random.choice(responses)

        if any(word in message for word in ["thanks", "thank you", "helpful"]):
            responses = [
                "You're welcome! Is there anything else you'd like to explore on this topic?",
                "Glad I could help! Feel free to ask more questions or we can move on to related topics.",
            ]
            return random.choice(responses)

        return None


class ClaudeChatProvider(ChatProvider):
    """
    Claude API chat provider.

    Integrates with Anthropic's Claude API for production use.
    Requires an API key from console.anthropic.com.

    Supported models (as of Jan 2025):
    - claude-haiku-3-5-20241022 (cheapest, fastest)
    - claude-sonnet-3-7-20250219 (balanced)
    - claude-sonnet-4-5-20250929 (most capable)
    - claude-opus-4-5-20251101 (most powerful)
    """

    # Model information (cost per million tokens)
    MODELS = {
        "claude-haiku-3-5-20241022": {
            "name": "Claude 3.5 Haiku",
            "input_cost": 0.80,
            "output_cost": 4.00,
            "description": "Fast and affordable"
        },
        "claude-haiku-4-5-20251001": {
            "name": "Claude 4.5 Haiku",
            "input_cost": 1.00,
            "output_cost": 5.00,
            "description": "Fastest and most affordable"
        },
        "claude-sonnet-3-7-20250219": {
            "name": "Claude 3.7 Sonnet",
            "input_cost": 3.00,
            "output_cost": 15.00,
            "description": "Balanced performance and cost"
        },
        "claude-sonnet-4-5-20250929": {
            "name": "Claude Sonnet 4.5",
            "input_cost": 3.00,
            "output_cost": 15.00,
            "description": "Most capable Sonnet model"
        },
        "claude-opus-4-5-20251101": {
            "name": "Claude Opus 4.5",
            "input_cost": 15.00,
            "output_cost": 75.00,
            "description": "Most powerful model"
        }
    }

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(self, api_key: str, model: Optional[str] = None):
        """
        Initialize Claude provider.

        Args:
            api_key: Anthropic API key
            model: Model ID (defaults to Haiku for cost efficiency)
        """
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package not installed. "
                "Install it with: pip install anthropic"
            )

        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model or self.DEFAULT_MODEL

        if self.model not in self.MODELS:
            available = ", ".join(self.MODELS.keys())
            raise ValueError(
                f"Unknown model: {self.model}. "
                f"Available models: {available}"
            )

    def generate_response(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> ChatResponse:
        """Generate a response using Claude API."""
        # Convert messages to API format
        api_messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

        # Make API call
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=api_messages
            )

            # Extract text content
            content = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    content += block.text

            # Build usage info
            usage = None
            if response.usage:
                usage = {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                }

            return ChatResponse(
                content=content,
                model=response.model,
                stop_reason=response.stop_reason,
                usage=usage
            )

        except Exception as e:
            # Re-raise with more context
            raise RuntimeError(f"Claude API error: {str(e)}") from e

    def get_model_name(self) -> str:
        """Return the Claude model being used."""
        return self.model

    def generate_response_stream(
        self,
        messages: list[ChatMessage],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1024,
        temperature: float = 1.0
    ) -> Generator[str, None, None]:
        """Generate a streaming response using Claude API."""
        # Convert messages to API format
        api_messages = [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

        # Make streaming API call
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=api_messages
            ) as stream:
                for text in stream.text_stream:
                    yield text

        except Exception as e:
            # Yield error message
            yield f"[Error: {str(e)}]"

    @classmethod
    def get_available_models(cls) -> dict:
        """Get information about available models."""
        return cls.MODELS

    @classmethod
    def get_default_model(cls) -> str:
        """Get the default model (cheapest for dev)."""
        return cls.DEFAULT_MODEL
