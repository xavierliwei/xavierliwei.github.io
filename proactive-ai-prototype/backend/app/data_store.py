"""
Data storage abstraction layer.

This module provides a simple JSON-based storage that can be easily
replaced with a real database (PostgreSQL, MongoDB, etc.) later.

Design principle: All data access goes through this module, making it
easy to swap implementations.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import uuid

from .models import (
    Candidate, User, UserActivity, Feedback, Conversation, ChatMessage
)


class DataStore:
    """
    JSON-based data store for MVP.

    To refactor to a real database:
    1. Create a new class implementing the same interface
    2. Replace instantiation in main.py
    """

    def __init__(self, data_file: str = "data/candidates.json"):
        self.data_file = Path(__file__).parent.parent / data_file
        self._data = self._load_data()

    def _load_data(self) -> dict:
        """Load data from JSON file."""
        if self.data_file.exists():
            with open(self.data_file, "r") as f:
                return json.load(f)
        return {"candidates": [], "users": [], "user_activity": [], "feedback": []}

    def _save_data(self) -> None:
        """Persist data to JSON file."""
        with open(self.data_file, "w") as f:
            json.dump(self._data, f, indent=2, default=str)

    # Candidate operations

    def get_all_candidates(self) -> list[Candidate]:
        """Get all candidates from the pool."""
        return [self._dict_to_candidate(c) for c in self._data.get("candidates", [])]

    def _dict_to_candidate(self, data: dict) -> Candidate:
        """Convert a dict to Candidate, handling extra fields gracefully."""
        # Only pass fields that Candidate accepts
        valid_fields = {
            'id', 'title', 'summary', 'category', 'keywords', 'source',
            'engagement_score', 'created_at', 'content_type', 'difficulty', 'priority'
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return Candidate(**filtered)

    def get_candidate_by_id(self, candidate_id: str) -> Optional[Candidate]:
        """Get a specific candidate by ID."""
        for c in self._data.get("candidates", []):
            if c["id"] == candidate_id:
                return self._dict_to_candidate(c)
        return None

    def get_candidates_by_keywords(
        self, keywords: list[str], limit: int = 100
    ) -> list[Candidate]:
        """
        Retrieve candidates matching any of the given keywords.

        This is the retrieval stage of the recommendation pipeline.
        """
        candidates = []
        for c in self._data.get("candidates", []):
            candidate_keywords = set(c.get("keywords", []))
            if candidate_keywords & set(keywords):
                candidates.append(self._dict_to_candidate(c))

        # Sort by engagement score (simple ranking for retrieval)
        candidates.sort(key=lambda x: x.engagement_score, reverse=True)
        return candidates[:limit]

    def get_candidates_by_category(self, category: str) -> list[Candidate]:
        """Get all candidates in a specific category."""
        return [
            self._dict_to_candidate(c)
            for c in self._data.get("candidates", [])
            if c.get("category") == category
        ]

    def update_candidate_score(self, candidate_id: str, score_delta: float) -> None:
        """Update a candidate's engagement score."""
        for c in self._data.get("candidates", []):
            if c["id"] == candidate_id:
                c["engagement_score"] = c.get("engagement_score", 0) + score_delta
                break
        self._save_data()

    # User operations

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        for u in self._data.get("users", []):
            if u["id"] == user_id:
                return User(**u)
        return None

    def create_user(self, user: User) -> User:
        """Create a new user."""
        user_dict = {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "topics_of_interest": user.topics_of_interest,
            "frequency": user.frequency,
            "preferred_hour_start": user.preferred_hour_start,
            "preferred_hour_end": user.preferred_hour_end,
            "created_at": datetime.now().isoformat()
        }
        self._data.setdefault("users", []).append(user_dict)
        self._save_data()
        return user

    def update_user_preferences(
        self,
        user_id: str,
        topics_of_interest: Optional[list[str]] = None,
        frequency: Optional[str] = None,
        preferred_hour_start: Optional[int] = None,
        preferred_hour_end: Optional[int] = None
    ) -> Optional[User]:
        """Update user preferences."""
        for u in self._data.get("users", []):
            if u["id"] == user_id:
                if topics_of_interest is not None:
                    u["topics_of_interest"] = topics_of_interest
                if frequency is not None:
                    u["frequency"] = frequency
                if preferred_hour_start is not None:
                    u["preferred_hour_start"] = preferred_hour_start
                if preferred_hour_end is not None:
                    u["preferred_hour_end"] = preferred_hour_end
                self._save_data()
                return User(**u)
        return None

    # User activity operations

    def get_user_activity(
        self, user_id: str, limit: int = 50
    ) -> list[UserActivity]:
        """Get recent user activity."""
        activities = [
            UserActivity(**a)
            for a in self._data.get("user_activity", [])
            if a["user_id"] == user_id
        ]
        # Sort by timestamp descending
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]

    def add_user_activity(self, activity: UserActivity) -> None:
        """Record a new user activity."""
        activity_dict = {
            "user_id": activity.user_id,
            "activity_type": activity.activity_type,
            "timestamp": activity.timestamp or datetime.now().isoformat(),
            "keywords": activity.keywords,
            "query": activity.query,
            "pr_id": activity.pr_id
        }
        self._data.setdefault("user_activity", []).append(activity_dict)
        self._save_data()

    def get_user_keywords(self, user_id: str) -> list[str]:
        """
        Extract keywords from user's recent activity.

        This is used to enrich the retrieval query.
        """
        activities = self.get_user_activity(user_id, limit=20)
        keywords = []
        for activity in activities:
            keywords.extend(activity.keywords)
            if activity.query:
                # Simple keyword extraction from search queries
                keywords.extend(activity.query.lower().split())
        return list(set(keywords))

    # Feedback operations

    def record_feedback(self, feedback: Feedback) -> Feedback:
        """Record user feedback on a recommendation."""
        feedback_dict = {
            "id": feedback.id or str(uuid.uuid4()),
            "user_id": feedback.user_id,
            "candidate_id": feedback.candidate_id,
            "action": feedback.action,
            "conversation_turns": feedback.conversation_turns,
            "created_at": feedback.created_at or datetime.now().isoformat()
        }
        self._data.setdefault("feedback", []).append(feedback_dict)
        self._save_data()

        # Update candidate score based on feedback
        score_deltas = {
            "started": 1.0,
            "replied": 0.5,
            "dismissed": -0.3,
            "ignored": -0.1,
            "dont_show_like_this": -1.0
        }
        delta = score_deltas.get(feedback.action, 0)
        if delta != 0:
            self.update_candidate_score(feedback.candidate_id, delta)

        return Feedback(**feedback_dict)

    def get_shown_candidates(self, user_id: str) -> list[str]:
        """Get IDs of candidates already shown to this user."""
        return [
            f["candidate_id"]
            for f in self._data.get("feedback", [])
            if f["user_id"] == user_id
        ]

    def get_feedback_stats(self, user_id: str) -> dict:
        """Get aggregated feedback statistics for a user."""
        feedback_list = [
            f for f in self._data.get("feedback", [])
            if f["user_id"] == user_id
        ]
        stats = {
            "total": len(feedback_list),
            "started": 0,
            "dismissed": 0,
            "ignored": 0,
            "replied": 0
        }
        for f in feedback_list:
            action = f.get("action", "")
            if action in stats:
                stats[action] += 1
        return stats

    # Collaborative filtering operations

    def find_similar_users(self, user_id: str, limit: int = 10) -> list[tuple[str, float]]:
        """
        Find users with similar interests using Jaccard similarity.

        Returns list of (user_id, similarity_score) tuples.
        """
        target_user = self.get_user(user_id)
        if not target_user:
            return []

        target_interests = set(target_user.topics_of_interest)
        if not target_interests:
            return []

        similarities = []
        for u in self._data.get("users", []):
            if u["id"] == user_id:
                continue

            other_interests = set(u.get("topics_of_interest", []))
            if not other_interests:
                continue

            # Jaccard similarity: intersection / union
            intersection = len(target_interests & other_interests)
            union = len(target_interests | other_interests)
            if union > 0:
                similarity = intersection / union
                if similarity > 0:
                    similarities.append((u["id"], similarity))

        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:limit]

    def get_candidates_engaged_by_similar_users(
        self,
        user_id: str,
        limit: int = 20
    ) -> list[tuple[str, float]]:
        """
        Get candidates that similar users engaged with positively.

        Returns list of (candidate_id, weighted_score) tuples.
        """
        similar_users = self.find_similar_users(user_id)
        if not similar_users:
            return []

        # Get candidates already seen by target user
        seen_by_target = set(self.get_shown_candidates(user_id))

        # Aggregate positive engagement from similar users
        candidate_scores: dict[str, float] = {}
        positive_actions = {"started", "replied"}

        for similar_user_id, similarity in similar_users:
            user_feedback = [
                f for f in self._data.get("feedback", [])
                if f["user_id"] == similar_user_id and f.get("action") in positive_actions
            ]
            for f in user_feedback:
                candidate_id = f["candidate_id"]
                # Skip if target user already saw this
                if candidate_id in seen_by_target:
                    continue
                # Weight by similarity and action strength
                action_weight = 1.0 if f["action"] == "started" else 0.5
                score = similarity * action_weight
                candidate_scores[candidate_id] = candidate_scores.get(candidate_id, 0) + score

        # Sort by score descending
        sorted_candidates = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_candidates[:limit]

    def get_popular_candidates(self, limit: int = 10) -> list[tuple[str, int]]:
        """
        Get most popular candidates based on positive engagement count.

        Returns list of (candidate_id, engagement_count) tuples.
        """
        positive_actions = {"started", "replied"}
        engagement_counts: dict[str, int] = {}

        for f in self._data.get("feedback", []):
            if f.get("action") in positive_actions:
                candidate_id = f["candidate_id"]
                engagement_counts[candidate_id] = engagement_counts.get(candidate_id, 0) + 1

        sorted_candidates = sorted(engagement_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_candidates[:limit]
