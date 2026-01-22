"""
Conversation Orchestrator.

This module handles the LLM integration for generating proactive messages
and managing conversations. Supports both mock (for dev) and Claude API
(for production) via pluggable chat providers.

Usage:
    # The service automatically uses the provider specified in config
    service = ConversationService(data_store)

    # Generate a chat response
    response, conv_id = service.generate_chat_response(
        user_id="user_123",
        message="Tell me about Kafka"
    )
"""

from datetime import datetime
from typing import Optional, Generator
import uuid

from .models import (
    Candidate, User, ScoredCandidate, ChatMessage, Conversation, Signal
)
from .data_store import DataStore
from .chat_provider import ChatProvider, MockChatProvider, ClaudeChatProvider, ChatMessage as ProviderMessage
from .config import get_config


# Prompt templates for different scenarios
PROACTIVE_MESSAGE_TEMPLATE = """
You are a helpful assistant that proactively starts conversations.

USER CONTEXT:
- Name: {user_name}
- Interests: {user_interests}

RECOMMENDATION:
- Topic: {topic_title}
- Summary: {topic_summary}
- Why relevant: {relevance_reasons}

GUIDELINES:
- Keep the opening message to 2-3 sentences
- Ask an engaging question, don't just inform
- Reference why this might interest them
- Be helpful, not intrusive

Generate a natural conversation opener about this topic.
"""

CHAT_RESPONSE_TEMPLATE = """
You are a helpful assistant having a conversation about: {topic}

Previous messages:
{conversation_history}

User's message: {user_message}

Guidelines:
- Be helpful and informative
- Stay on topic but allow natural tangents
- Ask follow-up questions to deepen understanding
- Keep responses concise but thorough

Generate a helpful response:
"""


class ConversationService:
    """
    Manages conversations and generates AI responses.

    Uses pluggable chat providers (mock for dev, Claude for production).
    The provider is automatically selected based on configuration.
    """

    def __init__(self, data_store: DataStore, chat_provider: Optional[ChatProvider] = None):
        self.data_store = data_store
        self._conversations: dict[str, Conversation] = {}

        # Initialize chat provider
        if chat_provider:
            self.chat_provider = chat_provider
        else:
            # Auto-select provider based on config
            config = get_config()
            if config.is_using_claude():
                self.chat_provider = ClaudeChatProvider(
                    api_key=config.claude_api_key,
                    model=config.claude_model
                )
                print(f"Using Claude API with model: {config.claude_model}")
            else:
                self.chat_provider = MockChatProvider()
                print("Using mock chat provider for development")

    def generate_proactive_message(
        self,
        user: User,
        scored_candidate: ScoredCandidate
    ) -> str:
        """
        Generate a proactive conversation opener.

        Args:
            user: The target user
            scored_candidate: The recommended content with relevance signals

        Returns:
            A natural language message to start the conversation
        """
        # Build relevance explanation from signals
        relevance_reasons = self._format_signals(scored_candidate.signals)

        # If using Claude API, generate with LLM
        config = get_config()
        if config.is_using_claude():
            system_prompt = PROACTIVE_MESSAGE_TEMPLATE.format(
                user_name=user.name,
                user_interests=", ".join(user.topics_of_interest[:5]),
                topic_title=scored_candidate.candidate.title,
                topic_summary=scored_candidate.candidate.summary,
                relevance_reasons=relevance_reasons
            )

            try:
                response = self.chat_provider.generate_response(
                    messages=[ProviderMessage(
                        role="user",
                        content="Generate a proactive conversation opener based on the context."
                    )],
                    system_prompt=system_prompt,
                    max_tokens=256,
                    temperature=0.8
                )
                return response.content
            except Exception as e:
                # Fallback to mock on error
                print(f"Error generating proactive message with Claude: {e}")

        # Use mock responses for development or as fallback
        return self._generate_proactive_mock(
            scored_candidate.candidate,
            user.name
        )

    def generate_chat_response(
        self,
        user_id: str,
        message: str,
        context: Optional[dict] = None
    ) -> tuple[str, str]:
        """
        Generate a response to a user message.

        Args:
            user_id: The user's ID
            message: The user's message
            context: Optional context (e.g., current topic)

        Returns:
            Tuple of (response, conversation_id)
        """
        # Get or create conversation
        conversation = self._get_or_create_conversation(user_id, context)

        # Add user message
        user_msg = ChatMessage(
            role="user",
            content=message,
            timestamp=datetime.now().isoformat()
        )
        conversation.messages.append(user_msg)

        # Generate response using chat provider
        response = self._generate_response(conversation, context)

        # Add assistant message
        assistant_msg = ChatMessage(
            role="assistant",
            content=response,
            timestamp=datetime.now().isoformat()
        )
        conversation.messages.append(assistant_msg)

        return response, conversation.id

    def generate_chat_response_stream(
        self,
        user_id: str,
        message: str,
        context: Optional[dict] = None
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response to a user message.

        Args:
            user_id: The user's ID
            message: The user's message
            context: Optional context (e.g., current topic)

        Yields:
            Text chunks as they are generated
        """
        # Get or create conversation
        conversation = self._get_or_create_conversation(user_id, context)

        # Add user message
        user_msg = ChatMessage(
            role="user",
            content=message,
            timestamp=datetime.now().isoformat()
        )
        conversation.messages.append(user_msg)

        # Build system prompt
        system_prompt = "You are a helpful AI assistant that provides clear, informative responses about technical topics. "
        if context and context.get("topic"):
            system_prompt += f"The current conversation topic is: {context['topic']}."

        # Convert conversation messages to provider format
        provider_messages = [
            ProviderMessage(role=msg.role, content=msg.content)
            for msg in conversation.messages
        ]

        # Get configuration
        config = get_config()

        # Collect full response for saving to conversation history
        full_response = []

        # Stream response
        try:
            for chunk in self.chat_provider.generate_response_stream(
                messages=provider_messages,
                system_prompt=system_prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            ):
                full_response.append(chunk)
                yield chunk
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            full_response.append(error_msg)
            yield error_msg

        # Add complete assistant message to conversation history
        assistant_msg = ChatMessage(
            role="assistant",
            content="".join(full_response),
            timestamp=datetime.now().isoformat()
        )
        conversation.messages.append(assistant_msg)

    def _get_or_create_conversation(
        self,
        user_id: str,
        context: Optional[dict] = None
    ) -> Conversation:
        """Get existing conversation or create new one."""
        # For simplicity, one conversation per user for now
        if user_id in self._conversations:
            conv = self._conversations[user_id]
            # Update context if provided
            if context:
                conv.context = context
            return conv

        # Create new conversation
        conv = Conversation(
            id=str(uuid.uuid4()),
            user_id=user_id,
            messages=[],
            context=context,
            started_at=datetime.now().isoformat()
        )
        self._conversations[user_id] = conv
        return conv

    def _format_signals(self, signals: list[Signal]) -> str:
        """Format signals into readable text."""
        if not signals:
            return "Matches your general interests"

        descriptions = [s.description for s in signals[:3]]
        return "; ".join(descriptions)

    def _generate_response(
        self,
        conversation: Conversation,
        context: Optional[dict] = None
    ) -> str:
        """
        Generate a response using the chat provider.

        Args:
            conversation: The conversation object
            context: Optional context (e.g., current topic)

        Returns:
            Generated response text
        """
        # Build system prompt
        system_prompt = "You are a helpful AI assistant that provides clear, informative responses about technical topics. "
        if context and context.get("topic"):
            system_prompt += f"The current conversation topic is: {context['topic']}."

        # Convert conversation messages to provider format
        provider_messages = [
            ProviderMessage(role=msg.role, content=msg.content)
            for msg in conversation.messages
        ]

        # Get configuration
        config = get_config()

        # Generate response
        try:
            response = self.chat_provider.generate_response(
                messages=provider_messages,
                system_prompt=system_prompt,
                max_tokens=config.max_tokens,
                temperature=config.temperature
            )
            return response.content
        except Exception as e:
            # Fallback to error message
            return f"I apologize, but I encountered an error generating a response: {str(e)}"

    def _generate_proactive_mock(
        self,
        candidate: Candidate,
        user_name: str
    ) -> str:
        """
        Generate a mock proactive message.

        Replace with actual LLM call in production.
        """
        category = candidate.category.lower()

        templates = {
            "learning": [
                f"I noticed you've been diving into {candidate.keywords[0] if candidate.keywords else 'technical topics'}. {candidate.title} - would you like to explore this together?",
                f"Based on your recent learning, I thought you might find this interesting: {candidate.summary[:100]}... Want to discuss?",
            ],
            "work": [
                f"Hey, heads up - {candidate.summary[:80]}... Would you like me to help you address this?",
                f"I see something that might need your attention: {candidate.title}. Should we take a look?",
            ],
            "news": [
                f"There's an interesting development that relates to your work: {candidate.summary[:100]}... Want to discuss the implications?",
                f"I came across some news you might find relevant: {candidate.title}. Shall we explore what it means for you?",
            ],
            "health": [
                f"I noticed a pattern that might be worth discussing: {candidate.summary[:80]}... Would you like some suggestions?",
            ],
            "productivity": [
                f"I have a suggestion that might help your workflow: {candidate.summary[:80]}... Interested?",
            ]
        }

        category_templates = templates.get(category, templates["learning"])
        import random
        return random.choice(category_templates)

    def _generate_chat_mock(
        self,
        message: str,
        conversation: Conversation,
        context: Optional[dict]
    ) -> str:
        """
        Generate a mock chat response.

        Replace with actual LLM call in production.
        """
        import random
        message_lower = message.lower()

        # Check for topic-specific keywords first
        topic_response = self._get_topic_specific_response(message_lower, context)
        if topic_response:
            return topic_response

        # Affirmative responses
        if any(word in message_lower for word in ["yes", "sure", "okay", "interested", "definitely", "absolutely"]):
            return self._get_positive_response(context)

        # Negative/deferral responses
        if any(word in message_lower for word in ["no", "not now", "later", "busy", "maybe later"]):
            responses = [
                "No problem! I'll keep this in mind for later. Feel free to ask me anything else whenever you're ready.",
                "Understood! I'll queue this for when you have more time. Is there anything else on your mind?",
                "Got it! I'll save this topic for another time. Let me know if there's something more urgent you'd like to discuss."
            ]
            return random.choice(responses)

        # Request for explanation
        if any(word in message_lower for word in ["more", "detail", "explain", "how", "why", "what is"]):
            return self._get_detailed_response(context, message_lower)

        # Request for examples
        if any(word in message_lower for word in ["example", "show", "demo", "code", "sample"]):
            return self._get_example_response(context, message_lower)

        # Continuation
        if any(word in message_lower for word in ["next", "what else", "continue", "more topics", "then what"]):
            return self._get_continuation_response(context)

        # Questions about tradeoffs/comparisons
        if any(word in message_lower for word in ["tradeoff", "trade-off", "versus", "vs", "compare", "difference"]):
            return self._get_comparison_response(context)

        # Thanks/acknowledgment
        if any(word in message_lower for word in ["thanks", "thank you", "helpful", "great", "awesome"]):
            responses = [
                "You're welcome! Is there anything else you'd like to explore on this topic?",
                "Glad I could help! Feel free to ask more questions or we can move on to related topics.",
                "Happy to help! Would you like to dive deeper or explore a different aspect?"
            ]
            return random.choice(responses)

        # Default contextual response
        return self._get_contextual_default(context, message_lower)

    def _get_topic_specific_response(
        self, message: str, context: Optional[dict]
    ) -> Optional[str]:
        """Generate responses for specific technical topics."""
        import random

        # Kafka-related
        if any(term in message for term in ["kafka", "consumer", "producer", "partition", "broker"]):
            responses = [
                "Kafka's architecture is built around the concept of a distributed commit log. The key components are producers (which write data), consumers (which read data), and brokers (which store the data in partitions). What aspect would you like to explore - the producer API, consumer groups, or how partitions work?",
                "When working with Kafka, understanding consumer groups is crucial. Each partition is consumed by exactly one consumer in a group, enabling parallel processing while maintaining ordering within partitions. Are you dealing with a specific use case?",
                "Kafka's exactly-once semantics involve three main mechanisms: idempotent producers, transactional writes, and consumer offset management. Which part would you like to understand better?"
            ]
            return random.choice(responses)

        # Distributed systems
        if any(term in message for term in ["distributed", "consensus", "replication", "consistency"]):
            responses = [
                "In distributed systems, the fundamental challenge is maintaining consistency across nodes while handling network partitions and failures. The CAP theorem tells us we can only guarantee two of three properties: Consistency, Availability, and Partition tolerance. Which tradeoff is most relevant to your use case?",
                "Distributed consensus algorithms like Raft and Paxos solve the problem of getting multiple nodes to agree on a value. Raft is generally easier to understand - it elects a leader who coordinates all writes. Would you like me to walk through how leader election works?",
                "Replication strategies vary based on your consistency requirements. Strong consistency (synchronous replication) ensures all replicas have the same data but adds latency. Eventual consistency (async replication) is faster but allows temporary divergence. What's your latency vs consistency requirement?"
            ]
            return random.choice(responses)

        # Kubernetes
        if any(term in message for term in ["kubernetes", "k8s", "pod", "container", "deployment"]):
            responses = [
                "Kubernetes orchestrates containerized applications across a cluster of nodes. The basic unit is a Pod (one or more containers), managed by higher-level objects like Deployments and StatefulSets. What are you trying to deploy?",
                "For cost optimization in Kubernetes, consider: right-sizing your pods based on actual resource usage, using Horizontal Pod Autoscaler, spot/preemptible instances for fault-tolerant workloads, and namespace resource quotas. Which approach interests you most?",
                "Kubernetes networking can be tricky. Each Pod gets its own IP, Services provide stable endpoints, and Ingress handles external traffic. Are you working on service-to-service communication or external access?"
            ]
            return random.choice(responses)

        # ML/AI
        if any(term in message for term in ["machine learning", "ml", "model", "training", "neural", "ai"]):
            responses = [
                "ML systems have unique infrastructure challenges: data pipelines, feature stores, model serving, and monitoring for drift. Are you focused on the training side or inference/serving?",
                "The ML lifecycle includes data preparation, feature engineering, model training, validation, deployment, and monitoring. Which stage are you working on?",
                "For ML infrastructure, key decisions include: batch vs real-time inference, model versioning strategy, and A/B testing frameworks. What's your current setup looking like?"
            ]
            return random.choice(responses)

        return None

    def _get_positive_response(self, context: Optional[dict]) -> str:
        """Response when user shows interest."""
        import random
        if context and context.get("topic"):
            topic = context["topic"]
            responses = [
                f"Excellent! Let's dive into {topic}. The key concepts to understand are the core principles and how they apply in practice. What's your current familiarity level - beginner, intermediate, or advanced?",
                f"Great choice! {topic} is a fascinating area. Should we start with the fundamentals or jump into a specific aspect you're curious about?",
                f"Perfect! I'd love to explore {topic} with you. Do you have a particular use case in mind, or shall we cover the concepts broadly first?"
            ]
            return random.choice(responses)

        responses = [
            "Great! Let's explore this together. What aspect would you like to start with? I can explain the fundamentals or jump into more advanced topics based on your preference.",
            "Excellent! I'm happy to help you understand this better. Would you prefer a high-level overview first, or should we dive into specifics?",
            "Perfect! There's a lot to cover here. Tell me about your current understanding and what you're trying to achieve, and I'll tailor my explanation."
        ]
        return random.choice(responses)

    def _get_detailed_response(self, context: Optional[dict], message: str = "") -> str:
        """Response when user asks for more details."""
        import random
        responses = [
            "Let me break this down further. The fundamental concept involves several interconnected ideas. First, there's the core principle of how these systems operate. Second, we need to consider the trade-offs involved. Would you like me to elaborate on either of these aspects?",
            "Happy to go deeper! The key insight here is understanding the 'why' behind the design decisions. Systems are built this way because of specific constraints around performance, reliability, and maintainability. Which constraint matters most for your use case?",
            "Absolutely! Let me explain the mechanics. At its core, this works by [mechanism]. The interesting part is how it handles edge cases like failures and concurrent access. Should I walk through a specific scenario?",
            "Sure! The detailed view involves understanding three layers: the interface (what users see), the implementation (how it works internally), and the operational aspects (monitoring, scaling, failure handling). Which layer would you like to explore?"
        ]
        return random.choice(responses)

    def _get_example_response(self, context: Optional[dict], message: str = "") -> str:
        """Response when user asks for examples."""
        import random
        responses = [
            "Here's a practical example: Imagine a system processing thousands of events per second. The challenge is ensuring each event is processed exactly once, even when failures occur. Companies like Netflix and Uber use techniques like idempotent operations and transaction logs to solve this. Would you like me to walk through how one of these patterns works?",
            "Let me give you a concrete example. Say you're building an e-commerce checkout system. You need to handle concurrent requests, prevent double-charging, and maintain consistency between inventory and orders. The pattern typically involves: [1] validating the request, [2] reserving inventory, [3] processing payment, [4] confirming the order. Want me to detail any of these steps?",
            "Here's a real-world scenario: A social media platform needs to show personalized feeds to millions of users with sub-100ms latency. They solve this using a combination of pre-computation (generating feeds in the background), caching (storing results in Redis), and fallbacks (showing recent posts if personalization fails). Which aspect would you like to explore?"
        ]
        return random.choice(responses)

    def _get_continuation_response(self, context: Optional[dict]) -> str:
        """Response when user wants to continue or see next steps."""
        import random
        responses = [
            "Great question! Building on what we discussed, the next logical step would be to explore the practical applications. Would you like me to walk through a specific use case?",
            "Now that we've covered the basics, there are several directions we could go: diving deeper into implementation details, exploring common pitfalls and how to avoid them, or discussing how this integrates with your existing stack. Which sounds most useful?",
            "The natural progression from here is to look at how these concepts work together in a real system. We could examine a case study, walk through a design exercise, or discuss operational concerns. What interests you most?",
            "Excellent! The next level involves understanding the nuances and edge cases. These are often where things get interesting (and where most bugs hide!). Should we explore some tricky scenarios?"
        ]
        return random.choice(responses)

    def _get_comparison_response(self, context: Optional[dict]) -> str:
        """Response when user asks about tradeoffs or comparisons."""
        import random
        responses = [
            "Great question about tradeoffs! Most engineering decisions involve balancing competing concerns. The key factors to consider are usually: performance (latency/throughput), reliability (fault tolerance), complexity (development/operational cost), and cost (infrastructure/licensing). Which of these matters most for your situation?",
            "When comparing approaches, I like to think in terms of: 'What problem does each solve best?' and 'What are the failure modes?' No solution is universally better - it depends on your specific constraints. Can you tell me more about your requirements?",
            "The tradeoff matrix here typically looks like: Option A is simpler but less scalable, Option B handles scale better but adds operational complexity, and Option C is the most flexible but requires more expertise. What's your team's experience level and scale requirements?"
        ]
        return random.choice(responses)

    def _get_contextual_default(self, context: Optional[dict], message: str) -> str:
        """Generate a contextual default response."""
        import random

        if context and context.get("topic"):
            topic = context["topic"]
            responses = [
                f"That's an interesting angle on {topic}! Could you tell me more about what aspect you'd like to focus on? I can provide specific information based on your needs.",
                f"Good question! In the context of {topic}, there are several ways to approach this. What's driving your interest - is it a specific problem you're trying to solve?",
                f"I'd be happy to explore that further. How does this relate to what you're building? Understanding your use case helps me give more relevant advice."
            ]
            return random.choice(responses)

        responses = [
            "That's an interesting point! Could you tell me more about what aspect you'd like to focus on? I can provide more specific information based on your needs.",
            "I'd like to understand your question better. Are you looking for a conceptual explanation, practical guidance, or help with a specific problem you're facing?",
            "Good question! To give you the most helpful answer, could you share more context about what you're working on or what sparked this question?"
        ]
        return random.choice(responses)

    def get_conversation_history(
        self,
        user_id: str
    ) -> list[ChatMessage]:
        """Get conversation history for a user."""
        if user_id in self._conversations:
            return self._conversations[user_id].messages
        return []

    def clear_conversation(self, user_id: str) -> None:
        """Clear conversation history for a user."""
        if user_id in self._conversations:
            del self._conversations[user_id]
