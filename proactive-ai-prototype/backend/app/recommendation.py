"""
Recommendation Engine.

This module implements the three-stage recommendation pipeline:
1. Retrieval - Get candidates matching user context
2. Ranking - Score candidates by relevance
3. Selection - Pick the best candidates to show

Design for refactoring:
- Each stage can be extracted to its own module
- Ranking logic can be replaced with ML models
- Retrieval can be enhanced with vector search
"""

from datetime import datetime
from typing import Optional

from .models import (
    Candidate, User, UserActivity, UserContext, Signal, ScoredCandidate
)
from .data_store import DataStore


class RetrievalService:
    """
    Stage 1: Candidate Retrieval.

    Responsible for fetching relevant candidates from the pool.
    Currently uses keyword matching; can be enhanced with:
    - Embedding-based similarity search
    - Collaborative filtering
    - Content-based filtering
    """

    def __init__(self, data_store: DataStore):
        self.data_store = data_store

    def retrieve_candidates(
        self,
        user: User,
        limit: int = 50
    ) -> list[Candidate]:
        """
        Retrieve candidates relevant to the user.

        Combines multiple retrieval strategies:
        1. Match user's explicit interests
        2. Match keywords from recent activity
        3. Include high-engagement content
        """
        # Combine user interests with activity-derived keywords
        keywords = list(set(user.topics_of_interest))
        activity_keywords = self.data_store.get_user_keywords(user.id)
        keywords.extend(activity_keywords)

        # Get candidates matching keywords
        candidates = self.data_store.get_candidates_by_keywords(keywords, limit * 2)

        # Filter out already-shown candidates
        shown_ids = set(self.data_store.get_shown_candidates(user.id))
        candidates = [c for c in candidates if c.id not in shown_ids]

        return candidates[:limit]


class CollaborativeFilteringService:
    """
    Collaborative filtering based recommendations.

    Uses user-item interactions to find:
    - Similar users (user-based CF)
    - Popular items (popularity baseline)
    """

    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self._cf_cache: dict[str, dict] = {}

    def get_cf_scores(self, user_id: str) -> dict[str, float]:
        """
        Get collaborative filtering scores for candidates.

        Returns dict mapping candidate_id to CF score (0-1).
        """
        # Check cache (simple TTL-free cache for MVP)
        if user_id in self._cf_cache:
            return self._cf_cache[user_id]

        cf_scores: dict[str, float] = {}

        # Get candidates from similar users
        similar_user_candidates = self.data_store.get_candidates_engaged_by_similar_users(
            user_id, limit=50
        )
        if similar_user_candidates:
            max_score = max(score for _, score in similar_user_candidates)
            for candidate_id, score in similar_user_candidates:
                # Normalize to 0-1
                cf_scores[candidate_id] = score / max_score if max_score > 0 else 0

        # Blend with popularity (for cold start)
        popular = self.data_store.get_popular_candidates(limit=20)
        if popular:
            max_pop = max(count for _, count in popular)
            for candidate_id, count in popular:
                pop_score = (count / max_pop) * 0.3 if max_pop > 0 else 0
                # Add to existing CF score or use popularity alone
                cf_scores[candidate_id] = cf_scores.get(candidate_id, 0) + pop_score

        # Cache results
        self._cf_cache[user_id] = cf_scores
        return cf_scores

    def clear_cache(self, user_id: Optional[str] = None) -> None:
        """Clear CF cache for a user or all users."""
        if user_id:
            self._cf_cache.pop(user_id, None)
        else:
            self._cf_cache.clear()


class RankingService:
    """
    Stage 2: Candidate Ranking.

    Scores candidates based on multiple factors.
    Currently uses a weighted heuristic; can be replaced with:
    - Two-tower neural networks
    - Gradient boosted trees
    - Transformer-based rankers
    """

    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.cf_service = CollaborativeFilteringService(data_store)

    def rank_candidates(
        self,
        candidates: list[Candidate],
        user: User,
        context: Optional[UserContext] = None
    ) -> list[ScoredCandidate]:
        """
        Score and rank candidates for a user.

        Scoring factors:
        - Interest match: How well keywords match user interests (35%)
        - Activity relevance: Match with recent user activity (25%)
        - Collaborative filtering: What similar users liked (15%)
        - Engagement: Historical engagement score of the content (10%)
        - Recency: Prefer fresh content (10%)
        - Timing: Is this the right time to show this? (5%)
        - Diversity: Avoid too many similar suggestions
        """
        scored = []
        user_activities = self.data_store.get_user_activity(user.id, limit=20)

        # Get CF scores for this user
        cf_scores = self.cf_service.get_cf_scores(user.id)

        for candidate in candidates:
            score, signals = self._compute_score(
                candidate, user, user_activities, context, cf_scores
            )
            scored.append(ScoredCandidate(
                candidate=candidate,
                score=score,
                signals=signals
            ))

        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)

        # Apply diversity penalty (reduce score for similar consecutive items)
        scored = self._apply_diversity(scored)

        return scored

    def _compute_score(
        self,
        candidate: Candidate,
        user: User,
        activities: list[UserActivity],
        context: Optional[UserContext],
        cf_scores: Optional[dict[str, float]] = None
    ) -> tuple[float, list[Signal]]:
        """
        Compute relevance score and explanation signals.

        Returns (score, signals) where score is 0-1 normalized.

        Weight distribution:
        - Interest match: 35%
        - Activity relevance: 25%
        - Collaborative filtering: 15%
        - Engagement: 10%
        - Recency: 10%
        - Timing: 5%
        """
        signals = []
        score_components = []

        # 1. Interest match (weight: 0.35)
        interest_matches = candidate.matches_interests(user.topics_of_interest)
        if interest_matches > 0:
            interest_score = min(interest_matches / 3, 1.0) * 0.35
            score_components.append(interest_score)
            signals.append(Signal(
                type="match",
                description=f"Matches {interest_matches} of your interests",
                weight=interest_score
            ))

        # 2. Activity relevance (weight: 0.25)
        activity_keywords = []
        for a in activities[:10]:
            activity_keywords.extend(a.keywords)
            if a.query:
                activity_keywords.extend(a.query.lower().split())

        activity_matches = len(set(candidate.keywords) & set(activity_keywords))
        if activity_matches > 0:
            activity_score = min(activity_matches / 5, 1.0) * 0.25
            score_components.append(activity_score)

            # Generate descriptive signal based on activity type
            recent_activity = activities[0] if activities else None
            if recent_activity:
                if recent_activity.activity_type == "article_read":
                    signals.append(Signal(
                        type="reading_history",
                        description=f"Related to articles you've been reading",
                        weight=activity_score
                    ))
                elif recent_activity.activity_type == "search":
                    signals.append(Signal(
                        type="search_history",
                        description=f"Related to your recent searches",
                        weight=activity_score
                    ))

        # 3. Collaborative filtering (weight: 0.15)
        if cf_scores and candidate.id in cf_scores:
            cf_score = cf_scores[candidate.id] * 0.15
            score_components.append(cf_score)
            if cf_score > 0.05:  # Only show signal if significant
                signals.append(Signal(
                    type="similar_users",
                    description="Liked by users with similar interests",
                    weight=cf_score
                ))

        # 4. Engagement score (weight: 0.10)
        engagement_score = min(candidate.engagement_score / 5, 1.0) * 0.10
        score_components.append(engagement_score)

        # 5. Recency (weight: 0.10)
        try:
            created = datetime.fromisoformat(candidate.created_at.replace('Z', '+00:00'))
            days_old = (datetime.now(created.tzinfo) - created).days
            recency_score = max(0, 1 - days_old / 30) * 0.10
            score_components.append(recency_score)
            if days_old < 3:
                signals.append(Signal(
                    type="trending",
                    description="Fresh content from the last few days",
                    weight=recency_score
                ))
        except (ValueError, TypeError):
            pass

        # 6. Timing (weight: 0.05)
        if context:
            timing_score = context.receptivity_score * 0.05
            score_components.append(timing_score)
            if context.receptivity_score > 0.7:
                signals.append(Signal(
                    type="timing",
                    description="Optimal time based on your patterns",
                    weight=timing_score
                ))

        # Calculate final score
        total_score = sum(score_components)

        # Normalize to 0-1 range
        normalized_score = min(total_score / 1.0, 1.0)

        return normalized_score, signals

    def _apply_diversity(
        self, scored: list[ScoredCandidate]
    ) -> list[ScoredCandidate]:
        """
        Apply diversity penalty to avoid repetitive suggestions.

        Reduces score for items with same category as previous items.
        """
        seen_categories = set()
        result = []

        for item in scored:
            category = item.candidate.category
            if category in seen_categories:
                # Apply 20% penalty for repeated categories
                item.score *= 0.8
            seen_categories.add(category)
            result.append(item)

        # Re-sort after applying diversity
        result.sort(key=lambda x: x.score, reverse=True)
        return result


class RecommendationEngine:
    """
    Main recommendation engine combining retrieval and ranking.

    Usage:
        engine = RecommendationEngine(data_store)
        recommendations = engine.get_recommendations(user_id, limit=5)
    """

    def __init__(self, data_store: DataStore):
        self.data_store = data_store
        self.retrieval = RetrievalService(data_store)
        self.ranking = RankingService(data_store)

    def get_recommendations(
        self,
        user_id: str,
        limit: int = 5,
        context: Optional[UserContext] = None
    ) -> list[ScoredCandidate]:
        """
        Get personalized recommendations for a user.

        Pipeline:
        1. Fetch user profile
        2. Retrieve candidate pool
        3. Rank candidates
        4. Return top-K
        """
        # Get user
        user = self.data_store.get_user(user_id)
        if not user:
            # Create default user if not exists
            user = User(
                id=user_id,
                name="Anonymous",
                email="",
                topics_of_interest=["general"]
            )

        # Retrieve candidates
        candidates = self.retrieval.retrieve_candidates(user, limit=limit * 5)

        if not candidates:
            # Fallback to all candidates if no matches
            candidates = self.data_store.get_all_candidates()[:limit * 3]

        # Rank candidates
        scored = self.ranking.rank_candidates(candidates, user, context)

        # Return top-K
        return scored[:limit]

    def get_proactive_suggestion(
        self,
        user_id: str,
        context: Optional[UserContext] = None
    ) -> Optional[ScoredCandidate]:
        """
        Get a single best suggestion for proactive outreach.

        Only returns a suggestion if it meets the quality threshold.
        """
        recommendations = self.get_recommendations(user_id, limit=1, context=context)

        if not recommendations:
            return None

        top = recommendations[0]

        # Quality threshold: only suggest if score > 0.5
        if top.score < 0.5:
            return None

        return top
