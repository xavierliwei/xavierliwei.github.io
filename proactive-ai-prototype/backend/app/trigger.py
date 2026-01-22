"""
Trigger Decision Service.

Determines WHEN to send proactive messages to users.
This is a critical component for user experience - bad timing
leads to interruption fatigue and opt-outs.

Factors considered:
- User's stated preferences (frequency, time windows)
- Time since last proactive message
- Current user activity/engagement patterns
- Content urgency/relevance score
- Historical engagement patterns
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

from .models import User, UserContext, ScoredCandidate
from .data_store import DataStore


class TriggerDecision(str, Enum):
    """Possible outcomes of trigger evaluation."""
    TRIGGER = "trigger"           # Send message now
    WAIT = "wait"                 # Not the right time, try again later
    QUEUE = "queue"               # Queue for later delivery
    SKIP = "skip"                 # Don't send this recommendation


@dataclass
class TriggerResult:
    """Result of trigger evaluation."""
    decision: TriggerDecision
    reason: str
    retry_after: Optional[timedelta] = None
    priority: float = 0.5


class TriggerService:
    """
    Decides when to send proactive messages.

    Uses a multi-factor scoring system to balance:
    - User preferences and consent
    - Optimal engagement timing
    - Content relevance and urgency
    - Avoiding interruption fatigue
    """

    # Minimum hours between proactive messages by frequency preference
    MIN_INTERVALS = {
        "rarely": 72,      # 3 days
        "sometimes": 24,   # 1 day
        "often": 4         # 4 hours
    }

    # Content priority thresholds
    PRIORITY_THRESHOLDS = {
        "high": 0.8,
        "medium": 0.6,
        "low": 0.4
    }

    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def should_trigger(
        self,
        user: User,
        recommendation: ScoredCandidate,
        context: Optional[UserContext] = None
    ) -> TriggerResult:
        """
        Determine if we should send a proactive message now.

        Evaluation order:
        1. Check user preferences (hard constraints)
        2. Check timing constraints
        3. Evaluate content relevance
        4. Consider user context
        5. Make final decision
        """
        # 1. Check if user has paused notifications
        if user.paused_until:
            try:
                pause_end = datetime.fromisoformat(str(user.paused_until))
                if datetime.now() < pause_end:
                    return TriggerResult(
                        decision=TriggerDecision.WAIT,
                        reason="User has paused notifications",
                        retry_after=pause_end - datetime.now()
                    )
            except (ValueError, TypeError):
                pass

        # 2. Check time window preference
        current_hour = datetime.now().hour
        if not (user.preferred_hour_start <= current_hour < user.preferred_hour_end):
            # Calculate time until window opens
            hours_until_window = (user.preferred_hour_start - current_hour) % 24
            return TriggerResult(
                decision=TriggerDecision.QUEUE,
                reason=f"Outside preferred hours ({user.preferred_hour_start}:00-{user.preferred_hour_end}:00)",
                retry_after=timedelta(hours=hours_until_window)
            )

        # 3. Check frequency constraint
        min_interval = self.MIN_INTERVALS.get(user.frequency, 24)
        last_message_time = self._get_last_message_time(user.id)

        if last_message_time:
            hours_since_last = (datetime.now() - last_message_time).total_seconds() / 3600
            if hours_since_last < min_interval:
                return TriggerResult(
                    decision=TriggerDecision.WAIT,
                    reason=f"Too soon since last message ({hours_since_last:.1f}h < {min_interval}h)",
                    retry_after=timedelta(hours=min_interval - hours_since_last)
                )

        # 4. Check recommendation quality threshold
        if recommendation.score < 0.5:
            return TriggerResult(
                decision=TriggerDecision.SKIP,
                reason=f"Recommendation score too low ({recommendation.score:.2f})",
                priority=recommendation.score
            )

        # 5. Consider content urgency
        priority = self._compute_priority(recommendation)

        # 6. Consider user context if available
        if context:
            # Don't interrupt deep work
            if context.current_activity == "deep_work":
                return TriggerResult(
                    decision=TriggerDecision.QUEUE,
                    reason="User is in deep work mode",
                    retry_after=timedelta(hours=1),
                    priority=priority
                )

            # Adjust based on receptivity
            if context.receptivity_score < 0.3:
                return TriggerResult(
                    decision=TriggerDecision.WAIT,
                    reason=f"Low receptivity score ({context.receptivity_score:.2f})",
                    retry_after=timedelta(minutes=30),
                    priority=priority
                )

        # 7. All checks passed - trigger the message
        return TriggerResult(
            decision=TriggerDecision.TRIGGER,
            reason="All conditions met",
            priority=priority
        )

    def _get_last_message_time(self, user_id: str) -> Optional[datetime]:
        """Get timestamp of last proactive message sent to user."""
        feedback_list = self.data_store._data.get("feedback", [])

        user_feedback = [
            f for f in feedback_list
            if f["user_id"] == user_id
        ]

        if not user_feedback:
            return None

        # Sort by created_at descending
        user_feedback.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        try:
            return datetime.fromisoformat(user_feedback[0]["created_at"])
        except (ValueError, KeyError, TypeError):
            return None

    def _compute_priority(self, recommendation: ScoredCandidate) -> float:
        """
        Compute content priority for queue ordering.

        Higher priority items should be shown first when multiple are queued.
        """
        base_priority = recommendation.score

        # Boost for high-priority content categories
        candidate = recommendation.candidate
        if candidate.priority == "high":
            base_priority *= 1.3
        elif candidate.priority == "low":
            base_priority *= 0.8

        # Boost for work-related items during work hours
        current_hour = datetime.now().hour
        if 9 <= current_hour <= 17 and candidate.category == "work":
            base_priority *= 1.2

        # Cap at 1.0
        return min(base_priority, 1.0)

    def compute_receptivity(
        self,
        user_id: str,
        current_hour: Optional[int] = None
    ) -> float:
        """
        Estimate user's receptivity to proactive messages.

        Based on:
        - Historical engagement patterns by time
        - Recent activity level
        - Feedback history
        """
        if current_hour is None:
            current_hour = datetime.now().hour

        # Base receptivity by time of day (learned patterns)
        # Peak engagement typically 9-11am and 2-4pm
        time_receptivity = self._time_based_receptivity(current_hour)

        # Adjust based on feedback history
        stats = self.data_store.get_feedback_stats(user_id)
        if stats["total"] > 0:
            engagement_rate = stats.get("started", 0) / stats["total"]
            feedback_adjustment = 0.5 + 0.5 * engagement_rate
        else:
            feedback_adjustment = 0.7  # Default for new users

        return time_receptivity * feedback_adjustment

    def _time_based_receptivity(self, hour: int) -> float:
        """
        Get base receptivity score based on time of day.

        Based on typical knowledge worker engagement patterns.
        """
        # Morning ramp-up: 7-9
        if 7 <= hour < 9:
            return 0.6

        # Morning peak: 9-12
        if 9 <= hour < 12:
            return 0.9

        # Lunch dip: 12-14
        if 12 <= hour < 14:
            return 0.5

        # Afternoon peak: 14-17
        if 14 <= hour < 17:
            return 0.85

        # Evening wind-down: 17-20
        if 17 <= hour < 20:
            return 0.6

        # Night: 20-7
        return 0.3


class MessageQueue:
    """
    Queue for scheduled proactive messages.

    Messages that can't be sent immediately are queued for later delivery.
    """

    def __init__(self):
        self._queue: list[tuple[str, ScoredCandidate, datetime, float]] = []

    def add(
        self,
        user_id: str,
        recommendation: ScoredCandidate,
        deliver_after: datetime,
        priority: float = 0.5
    ) -> None:
        """Add a message to the queue."""
        self._queue.append((user_id, recommendation, deliver_after, priority))
        # Sort by delivery time, then priority
        self._queue.sort(key=lambda x: (x[2], -x[3]))

    def get_ready(self) -> list[tuple[str, ScoredCandidate]]:
        """Get all messages ready for delivery."""
        now = datetime.now()
        ready = []
        remaining = []

        for user_id, rec, deliver_after, _ in self._queue:
            if deliver_after <= now:
                ready.append((user_id, rec))
            else:
                remaining.append((user_id, rec, deliver_after, _))

        self._queue = remaining
        return ready

    def get_user_queue(self, user_id: str) -> list[ScoredCandidate]:
        """Get all queued messages for a user."""
        return [rec for uid, rec, _, _ in self._queue if uid == user_id]

    def clear_user(self, user_id: str) -> int:
        """Clear all queued messages for a user. Returns count cleared."""
        before = len(self._queue)
        self._queue = [(u, r, t, p) for u, r, t, p in self._queue if u != user_id]
        return before - len(self._queue)

    def __len__(self) -> int:
        return len(self._queue)
