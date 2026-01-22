"""
Proactive AI Recommendation System - FastAPI Backend

A modular backend service for the proactive AI assistant that combines
recommendation systems with conversational AI.

API Endpoints:
- GET /api/recommendations - Get personalized recommendations
- POST /api/chat - Send a message and get a response
- POST /api/feedback - Record user feedback
- GET /api/user/{user_id} - Get user profile
- PUT /api/preferences - Update user preferences

To run:
    uvicorn app.main:app --reload --port 8000
"""

from datetime import datetime
from typing import Optional
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from .data_store import DataStore
from .recommendation import RecommendationEngine
from .conversation import ConversationService
from .trigger import TriggerService, TriggerDecision
from .text_similarity import TextSimilarity, QueryExpander
from .models import User, UserActivity, Feedback, UserContext


# Initialize FastAPI app
app = FastAPI(
    title="Proactive AI Recommendation System",
    description="Backend service for proactive AI assistant combining recommendations with LLM conversations",
    version="2.0.0"
)

# Add CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
data_store = DataStore()
recommendation_engine = RecommendationEngine(data_store)
conversation_service = ConversationService(data_store)
trigger_service = TriggerService(data_store)
text_similarity = TextSimilarity()
query_expander = QueryExpander()

# Build text similarity index on startup
def build_similarity_index():
    """Build TF-IDF index from all candidates."""
    candidates = data_store.get_all_candidates()
    documents = [f"{c.title} {c.summary} {' '.join(c.keywords)}" for c in candidates]
    text_similarity.build_index(documents)


# Request/Response Models

class RecommendationRequest(BaseModel):
    """Request for recommendations."""
    user_id: str
    limit: int = Field(default=5, ge=1, le=20)
    include_signals: bool = True


class CandidateResponse(BaseModel):
    """A candidate in the response."""
    id: str
    title: str
    summary: str
    category: str
    keywords: list[str]
    source: str


class SignalResponse(BaseModel):
    """A signal explaining a recommendation."""
    type: str
    description: str


class ScoredCandidateResponse(BaseModel):
    """A recommendation with score and signals."""
    candidate: CandidateResponse
    score: float
    signals: list[SignalResponse]


class RecommendationResponse(BaseModel):
    """Response containing recommendations."""
    user_id: str
    recommendations: list[ScoredCandidateResponse]
    timestamp: str


class ChatRequest(BaseModel):
    """Request for chat interaction."""
    user_id: str
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    """Response from chat."""
    response: str
    conversation_id: str
    timestamp: str


class FeedbackRequest(BaseModel):
    """Request to record feedback."""
    user_id: str
    candidate_id: str
    action: str  # started, dismissed, ignored, replied, dont_show_like_this
    conversation_turns: int = 0


class FeedbackResponse(BaseModel):
    """Response after recording feedback."""
    id: str
    status: str


class UserResponse(BaseModel):
    """User profile response."""
    id: str
    name: str
    email: str
    topics_of_interest: list[str]
    frequency: str
    preferred_hour_start: int
    preferred_hour_end: int


class PreferencesRequest(BaseModel):
    """Request to update preferences."""
    user_id: str
    topics_of_interest: Optional[list[str]] = None
    frequency: Optional[str] = None
    preferred_hour_start: Optional[int] = None
    preferred_hour_end: Optional[int] = None


class CreateUserRequest(BaseModel):
    """Request to create a new user."""
    user_id: str
    name: str
    email: str = ""
    topics_of_interest: list[str] = []
    frequency: str = "sometimes"
    preferred_hour_start: int = 9
    preferred_hour_end: int = 18


class ProactiveMessageRequest(BaseModel):
    """Request to generate a proactive message."""
    user_id: str
    candidate_id: Optional[str] = None


class ProactiveMessageResponse(BaseModel):
    """Response with generated proactive message."""
    message: str
    candidate: CandidateResponse
    signals: list[SignalResponse]


class ActivityRequest(BaseModel):
    """Request to record user activity."""
    user_id: str
    activity_type: str
    keywords: list[str] = []
    query: str = ""


class TriggerCheckRequest(BaseModel):
    """Request to check if we should trigger a proactive message."""
    user_id: str


class TriggerCheckResponse(BaseModel):
    """Response from trigger check."""
    should_trigger: bool
    decision: str
    reason: str
    recommendation: Optional[ScoredCandidateResponse] = None
    retry_after_seconds: Optional[int] = None


class SearchRequest(BaseModel):
    """Request for semantic search."""
    query: str
    limit: int = Field(default=5, ge=1, le=20)


class SearchResponse(BaseModel):
    """Response from semantic search."""
    query: str
    results: list[ScoredCandidateResponse]
    expanded_terms: list[str]


class AnalyticsResponse(BaseModel):
    """Analytics and metrics response."""
    total_candidates: int
    total_users: int
    total_feedback: int
    engagement_rate: float
    top_categories: list[dict]
    recent_activity: list[dict]


class SnoozeRequest(BaseModel):
    """Request to snooze notifications."""
    user_id: str
    hours: int = Field(default=1, ge=1, le=168)  # Max 1 week


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "service": "Proactive AI Recommendation System",
        "status": "healthy",
        "version": "1.0.0"
    }


@app.get("/api/recommendations", response_model=RecommendationResponse)
async def get_recommendations(
    user_id: str,
    limit: int = 5
):
    """
    Get personalized recommendations for a user.

    The recommendation engine:
    1. Retrieves candidates matching user interests
    2. Ranks them by relevance
    3. Returns top-K with explanation signals
    """
    try:
        # Build user context (simplified for MVP)
        context = UserContext(
            user_id=user_id,
            receptivity_score=0.7  # Default for demo
        )

        # Get recommendations
        scored_candidates = recommendation_engine.get_recommendations(
            user_id=user_id,
            limit=limit,
            context=context
        )

        # Transform to response format
        recommendations = []
        for sc in scored_candidates:
            recommendations.append(ScoredCandidateResponse(
                candidate=CandidateResponse(
                    id=sc.candidate.id,
                    title=sc.candidate.title,
                    summary=sc.candidate.summary,
                    category=sc.candidate.category,
                    keywords=sc.candidate.keywords,
                    source=sc.candidate.source
                ),
                score=round(sc.score, 2),
                signals=[
                    SignalResponse(type=s.type, description=s.description)
                    for s in sc.signals
                ]
            ))

        return RecommendationResponse(
            user_id=user_id,
            recommendations=recommendations,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message and get an AI response.

    The conversation service:
    1. Maintains conversation history
    2. Generates contextual responses
    3. Can be integrated with LLM APIs
    """
    try:
        response, conversation_id = conversation_service.generate_chat_response(
            user_id=request.user_id,
            message=request.message,
            context=request.context
        )

        return ChatResponse(
            response=response,
            conversation_id=conversation_id,
            timestamp=datetime.now().isoformat()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    Send a message and get a streaming AI response.

    Uses Server-Sent Events (SSE) to stream the response
    as it's being generated. Provides a more interactive experience.

    Response format:
    - data: <text chunk>  (for content, newlines encoded as \\n)
    - data: [DONE]        (when complete)
    """
    async def generate():
        try:
            # Stream response using the conversation service
            for chunk in conversation_service.generate_chat_response_stream(
                user_id=request.user_id,
                message=request.message,
                context=request.context
            ):
                # Encode newlines for SSE (newlines in data field would break SSE format)
                # Replace actual newlines with escaped \n sequence
                encoded_chunk = chunk.replace('\n', '\\n')
                yield f"data: {encoded_chunk}\n\n"

            # Signal completion
            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: [ERROR: {str(e)}]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@app.post("/api/feedback", response_model=FeedbackResponse)
async def record_feedback(request: FeedbackRequest):
    """
    Record user feedback on a recommendation.

    Feedback is used to:
    1. Update candidate engagement scores
    2. Improve future recommendations
    3. Track user satisfaction metrics
    """
    try:
        feedback = Feedback(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            candidate_id=request.candidate_id,
            action=request.action,
            conversation_turns=request.conversation_turns,
            created_at=datetime.now().isoformat()
        )

        saved = data_store.record_feedback(feedback)

        return FeedbackResponse(
            id=saved.id,
            status="recorded"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/user", response_model=UserResponse)
async def create_user(request: CreateUserRequest):
    """
    Create a new user.

    Used during onboarding to register new users with their preferences.
    """
    try:
        # Check if user already exists
        existing = data_store.get_user(request.user_id)
        if existing:
            raise HTTPException(status_code=409, detail="User already exists")

        user = User(
            id=request.user_id,
            name=request.name,
            email=request.email,
            topics_of_interest=request.topics_of_interest,
            frequency=request.frequency,
            preferred_hour_start=request.preferred_hour_start,
            preferred_hour_end=request.preferred_hour_end
        )

        created = data_store.create_user(user)

        return UserResponse(
            id=created.id,
            name=created.name,
            email=created.email,
            topics_of_interest=created.topics_of_interest,
            frequency=created.frequency,
            preferred_hour_start=created.preferred_hour_start,
            preferred_hour_end=created.preferred_hour_end
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/user/{user_id}", response_model=UserResponse)
async def get_user(user_id: str):
    """Get user profile."""
    user = data_store.get_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        topics_of_interest=user.topics_of_interest,
        frequency=user.frequency,
        preferred_hour_start=user.preferred_hour_start,
        preferred_hour_end=user.preferred_hour_end
    )


@app.put("/api/preferences", response_model=UserResponse)
async def update_preferences(request: PreferencesRequest):
    """
    Update user preferences.

    Preferences control:
    - What topics to recommend
    - How often to make proactive suggestions
    - When to reach out
    """
    try:
        user = data_store.update_user_preferences(
            user_id=request.user_id,
            topics_of_interest=request.topics_of_interest,
            frequency=request.frequency,
            preferred_hour_start=request.preferred_hour_start,
            preferred_hour_end=request.preferred_hour_end
        )

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        return UserResponse(
            id=user.id,
            name=user.name,
            email=user.email,
            topics_of_interest=user.topics_of_interest,
            frequency=user.frequency,
            preferred_hour_start=user.preferred_hour_start,
            preferred_hour_end=user.preferred_hour_end
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/activity")
async def record_activity(request: ActivityRequest):
    """
    Record user activity for improving recommendations.

    Activity types:
    - article_read
    - search
    - pr_opened
    - page_view
    """
    try:
        activity = UserActivity(
            user_id=request.user_id,
            activity_type=request.activity_type,
            keywords=request.keywords,
            query=request.query,
            timestamp=datetime.now().isoformat()
        )

        data_store.add_user_activity(activity)

        return {"status": "recorded"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats/{user_id}")
async def get_user_stats(user_id: str):
    """Get feedback statistics for a user."""
    stats = data_store.get_feedback_stats(user_id)
    return {
        "user_id": user_id,
        "stats": stats
    }


@app.delete("/api/conversation/{user_id}")
async def clear_conversation(user_id: str):
    """Clear conversation history for a user."""
    conversation_service.clear_conversation(user_id)
    return {"status": "cleared"}


@app.post("/api/trigger/check", response_model=TriggerCheckResponse)
async def check_trigger(request: TriggerCheckRequest):
    """
    Check if we should send a proactive message to this user.

    Uses the trigger decision service to evaluate:
    - User preferences (frequency, time windows)
    - Time since last message
    - Recommendation quality
    - User receptivity
    """
    try:
        user = data_store.get_user(request.user_id)
        if not user:
            return TriggerCheckResponse(
                should_trigger=False,
                decision="skip",
                reason="User not found"
            )

        # Get top recommendation
        context = UserContext(
            user_id=request.user_id,
            receptivity_score=trigger_service.compute_receptivity(request.user_id)
        )

        recommendations = recommendation_engine.get_recommendations(
            user_id=request.user_id,
            limit=1,
            context=context
        )

        if not recommendations:
            return TriggerCheckResponse(
                should_trigger=False,
                decision="skip",
                reason="No recommendations available"
            )

        top_rec = recommendations[0]

        # Check trigger decision
        result = trigger_service.should_trigger(user, top_rec, context)

        # Build response
        rec_response = None
        if result.decision == TriggerDecision.TRIGGER:
            rec_response = ScoredCandidateResponse(
                candidate=CandidateResponse(
                    id=top_rec.candidate.id,
                    title=top_rec.candidate.title,
                    summary=top_rec.candidate.summary,
                    category=top_rec.candidate.category,
                    keywords=top_rec.candidate.keywords,
                    source=top_rec.candidate.source
                ),
                score=round(top_rec.score, 2),
                signals=[
                    SignalResponse(type=s.type, description=s.description)
                    for s in top_rec.signals
                ]
            )

        retry_seconds = None
        if result.retry_after:
            retry_seconds = int(result.retry_after.total_seconds())

        return TriggerCheckResponse(
            should_trigger=result.decision == TriggerDecision.TRIGGER,
            decision=result.decision.value,
            reason=result.reason,
            recommendation=rec_response,
            retry_after_seconds=retry_seconds
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/search", response_model=SearchResponse)
async def semantic_search(request: SearchRequest):
    """
    Search candidates using semantic similarity.

    Uses TF-IDF and query expansion to find relevant content.
    """
    try:
        # Expand query with related terms
        expanded_terms = query_expander.expand(request.query)

        # Get all candidates
        candidates = data_store.get_all_candidates()

        # Build search documents
        documents = [
            (c.id, f"{c.title} {c.summary} {' '.join(c.keywords)}")
            for c in candidates
        ]

        # Expanded query
        full_query = f"{request.query} {' '.join(expanded_terms)}"

        # Find similar documents
        similar = text_similarity.find_similar(full_query, documents, request.limit)

        # Build response
        results = []
        for doc_id, score in similar:
            candidate = data_store.get_candidate_by_id(doc_id)
            if candidate:
                results.append(ScoredCandidateResponse(
                    candidate=CandidateResponse(
                        id=candidate.id,
                        title=candidate.title,
                        summary=candidate.summary,
                        category=candidate.category,
                        keywords=candidate.keywords,
                        source=candidate.source
                    ),
                    score=round(score, 3),
                    signals=[SignalResponse(
                        type="semantic_match",
                        description=f"Semantic similarity: {score:.1%}"
                    )]
                ))

        return SearchResponse(
            query=request.query,
            results=results,
            expanded_terms=expanded_terms
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics", response_model=AnalyticsResponse)
async def get_analytics():
    """
    Get system analytics and metrics.

    Provides insights into:
    - Content pool size
    - User engagement
    - Category distribution
    - Recent activity
    """
    try:
        candidates = data_store.get_all_candidates()
        users = data_store._data.get("users", [])
        feedback = data_store._data.get("feedback", [])
        activities = data_store._data.get("user_activity", [])

        # Calculate engagement rate
        total_shown = len(feedback)
        engaged = len([f for f in feedback if f.get("action") in ["started", "replied"]])
        engagement_rate = engaged / total_shown if total_shown > 0 else 0

        # Top categories
        category_counts = {}
        for c in candidates:
            cat = c.category
            category_counts[cat] = category_counts.get(cat, 0) + 1

        top_categories = [
            {"category": k, "count": v}
            for k, v in sorted(category_counts.items(), key=lambda x: -x[1])
        ]

        # Recent activity (last 10)
        recent = sorted(activities, key=lambda x: x.get("timestamp", ""), reverse=True)[:10]
        recent_activity = [
            {
                "user_id": a.get("user_id"),
                "type": a.get("activity_type"),
                "timestamp": a.get("timestamp")
            }
            for a in recent
        ]

        return AnalyticsResponse(
            total_candidates=len(candidates),
            total_users=len(users),
            total_feedback=len(feedback),
            engagement_rate=round(engagement_rate, 3),
            top_categories=top_categories,
            recent_activity=recent_activity
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/snooze")
async def snooze_notifications(request: SnoozeRequest):
    """
    Snooze proactive notifications for a specified duration.

    Useful when user is busy or in focus mode.
    """
    try:
        from datetime import timedelta

        user = data_store.get_user(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user's paused_until
        pause_until = datetime.now() + timedelta(hours=request.hours)

        # Update in data store
        for u in data_store._data.get("users", []):
            if u["id"] == request.user_id:
                u["paused_until"] = pause_until.isoformat()
                break

        data_store._save_data()

        return {
            "status": "snoozed",
            "until": pause_until.isoformat(),
            "hours": request.hours
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/snooze/{user_id}")
async def cancel_snooze(user_id: str):
    """Cancel snooze and resume notifications."""
    try:
        for u in data_store._data.get("users", []):
            if u["id"] == user_id:
                u["paused_until"] = None
                break

        data_store._save_data()

        return {"status": "resumed"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/proactive-message", response_model=ProactiveMessageResponse)
async def generate_proactive_message(request: ProactiveMessageRequest):
    """
    Generate a proactive message for a user.

    Uses the conversation service to generate a personalized
    conversation opener based on recommendations.
    """
    try:
        user = data_store.get_user(request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get recommendation (either specified or top one)
        if request.candidate_id:
            candidate = data_store.get_candidate_by_id(request.candidate_id)
            if not candidate:
                raise HTTPException(status_code=404, detail="Candidate not found")
            # Create a basic scored candidate
            from .models import ScoredCandidate, Signal
            scored = ScoredCandidate(
                candidate=candidate,
                score=0.8,
                signals=[Signal(type="user_selected", description="User-selected topic")]
            )
        else:
            # Get top recommendation
            context = UserContext(
                user_id=request.user_id,
                receptivity_score=trigger_service.compute_receptivity(request.user_id)
            )
            recommendations = recommendation_engine.get_recommendations(
                user_id=request.user_id,
                limit=1,
                context=context
            )
            if not recommendations:
                raise HTTPException(status_code=404, detail="No recommendations available")
            scored = recommendations[0]

        # Generate the proactive message
        message = conversation_service.generate_proactive_message(user, scored)

        return ProactiveMessageResponse(
            message=message,
            candidate=CandidateResponse(
                id=scored.candidate.id,
                title=scored.candidate.title,
                summary=scored.candidate.summary,
                category=scored.candidate.category,
                keywords=scored.candidate.keywords,
                source=scored.candidate.source
            ),
            signals=[
                SignalResponse(type=s.type, description=s.description)
                for s in scored.signals
            ]
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/receptivity/{user_id}")
async def get_receptivity(user_id: str):
    """
    Get current receptivity score for a user.

    Useful for UI to show optimal times to engage.
    """
    try:
        receptivity = trigger_service.compute_receptivity(user_id)
        current_hour = datetime.now().hour

        # Get hourly receptivity pattern
        hourly_pattern = {}
        for hour in range(24):
            hourly_pattern[hour] = round(
                trigger_service.compute_receptivity(user_id, hour), 2
            )

        return {
            "user_id": user_id,
            "current_receptivity": round(receptivity, 2),
            "current_hour": current_hour,
            "hourly_pattern": hourly_pattern,
            "optimal_hours": [
                h for h, r in hourly_pattern.items() if r >= 0.7
            ]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Application startup/shutdown events

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    print("Proactive AI Recommendation System v2.0 starting...")
    print(f"Loaded {len(data_store.get_all_candidates())} candidates")
    print(f"Loaded {len(data_store._data.get('users', []))} users")

    # Build text similarity index
    build_similarity_index()
    print("Text similarity index built")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print("Proactive AI Recommendation System shutting down...")
