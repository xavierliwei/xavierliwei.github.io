"""
Data models for the Proactive AI Recommendation System.

This module defines all the data structures used throughout the system.
Designed for easy refactoring - models can be moved to separate files or
integrated with an ORM like SQLAlchemy.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ContentCategory(str, Enum):
    """Categories for content recommendations."""
    LEARNING = "learning"
    WORK = "work"
    NEWS = "news"
    HEALTH = "health"
    PRODUCTIVITY = "productivity"


class FeedbackAction(str, Enum):
    """Types of user feedback actions."""
    STARTED = "started"
    DISMISSED = "dismissed"
    IGNORED = "ignored"
    REPLIED = "replied"
    DONT_SHOW_LIKE_THIS = "dont_show_like_this"


class FrequencyPreference(str, Enum):
    """How often the user wants proactive suggestions."""
    RARELY = "rarely"
    SOMETIMES = "sometimes"
    OFTEN = "often"


@dataclass
class Candidate:
    """
    A content candidate that can be recommended to users.

    This is the core unit of the recommendation system. Each candidate
    represents a piece of content that might be relevant to a user.
    """
    id: str
    title: str
    summary: str
    category: str
    keywords: list[str]
    source: str
    engagement_score: float = 0.0
    created_at: str = ""
    content_type: str = "article"
    difficulty: str = "intermediate"
    priority: str = "medium"

    def matches_interests(self, interests: list[str]) -> int:
        """Count how many user interests match this candidate's keywords."""
        return len(set(self.keywords) & set(interests))


@dataclass
class User:
    """
    User profile with preferences and interests.

    Stores both explicit preferences (topics_of_interest) and
    derived settings (frequency, timing preferences).
    """
    id: str
    name: str
    email: str
    topics_of_interest: list[str] = field(default_factory=list)
    frequency: str = "sometimes"
    preferred_hour_start: int = 9
    preferred_hour_end: int = 18
    paused_until: Optional[datetime] = None
    created_at: str = ""


@dataclass
class UserActivity:
    """
    A single user activity event.

    Used for building user context and improving recommendations.
    """
    user_id: str
    activity_type: str
    timestamp: str
    keywords: list[str] = field(default_factory=list)
    query: str = ""
    pr_id: str = ""


@dataclass
class Signal:
    """
    A signal explaining why a recommendation was made.

    These are shown to users in the transparency panel.
    """
    type: str
    description: str
    weight: float = 1.0


@dataclass
class ScoredCandidate:
    """
    A candidate with its computed relevance score and explanation signals.

    This is the output of the ranking stage.
    """
    candidate: Candidate
    score: float
    signals: list[Signal] = field(default_factory=list)


@dataclass
class UserContext:
    """
    Real-time context about a user's current state.

    Used by the trigger decision system to determine when to reach out.
    """
    user_id: str
    current_activity: str = "browsing"
    recent_topics: list[str] = field(default_factory=list)
    time_since_last_interaction: int = 0  # seconds
    receptivity_score: float = 0.5


@dataclass
class Feedback:
    """
    User feedback on a recommendation.

    Used to improve the ranking model over time.
    """
    id: str
    user_id: str
    candidate_id: str
    action: str
    conversation_turns: int = 0
    created_at: str = ""


@dataclass
class ChatMessage:
    """
    A message in a conversation.
    """
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""
    metadata: Optional[dict] = None


@dataclass
class Conversation:
    """
    A conversation between user and assistant.
    """
    id: str
    user_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    context: Optional[dict] = None
    started_at: str = ""
