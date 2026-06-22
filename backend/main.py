import asyncio
import re
import json
import os
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from sse_starlette.sse import EventSourceResponse

from backend.db import search_restaurants, get_unique_locations, get_unique_cuisines
from backend.recommender import generate_recommendations, generate_recommendations_stream

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Zomato AI Restaurant Recommender API",
    description="API for filtering restaurants and getting AI-generated recommendations.",
    version="2.0.0"
)

# ---------------------------------------------------------------------------
# CORS — allows all Vercel deployments + local dev origins
# ---------------------------------------------------------------------------

# Explicit localhost origins for local development
ALLOWED_ORIGINS = [
    "http://localhost:3000",   # Next.js dev server
    "http://127.0.0.1:3000",
    "http://localhost:5173",   # Vite dev server (fallback)
    "http://127.0.0.1:5173",
    "http://localhost:5500",   # VS Code Live Server
    "http://127.0.0.1:5500",
    "http://localhost:5501",   # VS Code Live Server (alt)
    "http://127.0.0.1:5501",
    "http://localhost:8080",   # Python http.server
    "http://127.0.0.1:8080",
    "null",                    # file:// origin
]

# Also allow any explicit FRONTEND_URL set via environment variable
FRONTEND_URL = os.environ.get("FRONTEND_URL", "")
if FRONTEND_URL:
    ALLOWED_ORIGINS.append(FRONTEND_URL)

# Regex pattern — allows ALL *.vercel.app subdomains (production + preview)
# and all localhost ports automatically, without needing to update env vars
ALLOWED_ORIGIN_REGEX = (
    r"https://.*\.vercel\.app"
    r"|http://localhost:\d+"
    r"|http://127\.0\.0\.1:\d+"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_origin_regex=ALLOWED_ORIGIN_REGEX,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

# ---------------------------------------------------------------------------
# Standardized Response Helpers
# ---------------------------------------------------------------------------

def success_response(data: Any, status_code: int = 200) -> JSONResponse:
    """Wrap successful responses in a standardized envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": data,
            "error": None
        }
    )

def error_response(message: str, status_code: int = 400) -> JSONResponse:
    """Wrap error responses in a standardized envelope."""
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "data": None,
            "error": message
        }
    )

# ---------------------------------------------------------------------------
# Global Exception Handler — catches unhandled errors gracefully
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch any unhandled exception and return a clean JSON error."""
    return error_response(
        message=f"An unexpected server error occurred: {str(exc)}",
        status_code=500
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Wrap FastAPI's HTTPException in our standardized envelope."""
    return error_response(
        message=exc.detail,
        status_code=exc.status_code
    )

# ---------------------------------------------------------------------------
# Request Schemas
# ---------------------------------------------------------------------------

class RecommendRequest(BaseModel):
    location: str = Field(..., description="Location to search in (e.g. Banashankari, Basavanagudi)")
    cuisine: Optional[str] = Field(None, description="Cuisine type (e.g. Italian, North Indian, Chinese)")
    budget: Optional[str] = Field(None, description="Budget tier: 'low', 'medium', or 'high'")
    min_rating: Optional[float] = Field(0.0, ge=0.0, le=5.0, description="Minimum restaurant rating (0.0 to 5.0)")
    extra_preferences: Optional[str] = Field("", description="Additional context or vibe preferences (e.g. romantic, family-friendly, rooftop)")

# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check():
    """Verify backend and database connection status."""
    try:
        locations = get_unique_locations()
        db_status = "connected" if len(locations) > 0 else "empty"
        return success_response({
            "status": "healthy",
            "database": db_status,
            "unique_locations_count": len(locations)
        })
    except Exception as e:
        return error_response(
            message=f"Database health check failed: {str(e)}",
            status_code=503
        )

# ---------------------------------------------------------------------------
# Meta Endpoints — for frontend dropdowns / autocomplete
# ---------------------------------------------------------------------------

@app.get("/api/meta/locations")
def get_locations():
    """Retrieve all unique restaurant locations (sorted, deduplicated)."""
    try:
        locations = get_unique_locations()
        if not locations:
            return error_response(
                message="No locations found in the database.",
                status_code=404
            )
        return success_response(locations)
    except Exception as e:
        return error_response(
            message=f"Failed to fetch locations: {str(e)}",
            status_code=500
        )

@app.get("/api/meta/cuisines")
def get_cuisines():
    """Retrieve all unique cuisines (sorted, deduplicated)."""
    try:
        cuisines = get_unique_cuisines()
        if not cuisines:
            return error_response(
                message="No cuisines found in the database.",
                status_code=404
            )
        return success_response(cuisines)
    except Exception as e:
        return error_response(
            message=f"Failed to fetch cuisines: {str(e)}",
            status_code=500
        )

# ---------------------------------------------------------------------------
# Restaurant Search (hard-filter only, no AI)
# ---------------------------------------------------------------------------

@app.get("/api/restaurants/search")
def search(
    location: str = Query(..., description="Location to search in"),
    cuisine: Optional[str] = Query(None, description="Cuisine type"),
    budget: Optional[str] = Query(None, description="Budget level ('low', 'medium', 'high')"),
    min_rating: Optional[float] = Query(0.0, description="Minimum rating")
):
    """
    Search and filter restaurants using hard constraints.
    Returns the top candidates sorted by rating.
    """
    if not location.strip():
        raise HTTPException(status_code=400, detail="Location is required and cannot be empty.")
    
    # Validate budget if provided
    if budget and budget.strip().lower() not in ("low", "medium", "high"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid budget '{budget}'. Must be one of: 'low', 'medium', 'high'."
        )

    candidates = search_restaurants(
        location=location,
        cuisine=cuisine,
        budget=budget,
        min_rating=min_rating,
        limit=15
    )

    return success_response({
        "count": len(candidates),
        "candidates": candidates
    })

# ---------------------------------------------------------------------------
# AI Recommendation (standard POST — full response)
# ---------------------------------------------------------------------------

@app.post("/api/restaurants/recommend")
def recommend(request: RecommendRequest):
    """
    Recommend the best restaurants using database filtering + AI reasoning.
    
    Steps:
    1. Filter restaurants matching location, budget, cuisine, rating constraints.
    2. Pass top candidates along with user preferences to the LLM.
    3. LLM ranks the top 3 and adds customized explanations.
    """
    location = request.location.strip()
    if not location:
        raise HTTPException(status_code=400, detail="Location is required.")

    # Validate budget if provided
    if request.budget and request.budget.strip().lower() not in ("low", "medium", "high"):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid budget '{request.budget}'. Must be one of: 'low', 'medium', 'high'."
        )

    # Step 1: Query candidates matching hard constraints
    candidates = search_restaurants(
        location=location,
        cuisine=request.cuisine,
        budget=request.budget,
        min_rating=request.min_rating,
        limit=12
    )

    query_info = {
        "location": location,
        "cuisine": request.cuisine,
        "budget": request.budget,
        "min_rating": request.min_rating,
        "extra_preferences": request.extra_preferences
    }

    # Handle zero matching candidates
    if not candidates:
        return success_response({
            "query_info": query_info,
            "count": 0,
            "recommendations": [],
            "message": "No restaurants match your filters. Try broadening your location, budget, or rating constraints."
        })

    # Step 2: Generate AI recommendations
    preferences = {
        "location": location,
        "cuisine": request.cuisine,
        "budget": request.budget,
        "min_rating": request.min_rating
    }

    try:
        recommendations = generate_recommendations(
            candidates=candidates,
            preferences=preferences,
            extra_preferences=request.extra_preferences
        )
    except Exception as e:
        return error_response(
            message=f"AI recommendation engine encountered an error: {str(e)}. Please try again.",
            status_code=502
        )

    return success_response({
        "query_info": query_info,
        "count": len(recommendations),
        "recommendations": recommendations
    })

# ---------------------------------------------------------------------------
# AI Recommendation — SSE Streaming Endpoint
# ---------------------------------------------------------------------------

@app.post("/api/restaurants/recommend/stream")
async def recommend_stream(request: RecommendRequest):
    """
    Streaming version of the recommendation endpoint.
    Sends Server-Sent Events (SSE) so the frontend can display
    the AI explanation as it types out in real-time.

    SSE event types:
      - 'candidates'  : the filtered candidate list (sent immediately)
      - 'chunk'       : a token/chunk of the LLM response as it streams
      - 'complete'    : the final parsed recommendations (sent at the end)
      - 'error'       : an error message
    """


    location = request.location.strip()
    if not location:
        return error_response("Location is required.", 400)

    # Validate budget
    if request.budget and request.budget.strip().lower() not in ("low", "medium", "high"):
        return error_response(
            f"Invalid budget '{request.budget}'. Must be one of: 'low', 'medium', 'high'.",
            400
        )

    candidates = search_restaurants(
        location=location,
        cuisine=request.cuisine,
        budget=request.budget,
        min_rating=request.min_rating,
        limit=12
    )

    query_info = {
        "location": location,
        "cuisine": request.cuisine,
        "budget": request.budget,
        "min_rating": request.min_rating,
        "extra_preferences": request.extra_preferences
    }

    if not candidates:
        async def no_results_stream():
            yield {
                "event": "error",
                "data": json.dumps({
                    "query_info": query_info,
                    "message": "No restaurants match your filters. Try broadening your search."
                })
            }
        return EventSourceResponse(no_results_stream())

    preferences = {
        "location": location,
        "cuisine": request.cuisine,
        "budget": request.budget,
        "min_rating": request.min_rating
    }

    async def event_generator():
        # First, send the candidate list so the frontend can show something immediately
        yield {
            "event": "candidates",
            "data": json.dumps({
                "query_info": query_info,
                "count": len(candidates),
                "candidates": candidates
            })
        }

        # Stream the LLM response
        try:
            full_text = ""
            async for chunk in generate_recommendations_stream(
                candidates=candidates,
                preferences=preferences,
                extra_preferences=request.extra_preferences
            ):
                full_text += chunk
                yield {
                    "event": "chunk",
                    "data": json.dumps({"token": chunk})
                }

            # Parse the final result once streaming is done
            from backend.recommender import parse_llm_response
            final_recs = parse_llm_response(full_text, candidates)

            yield {
                "event": "complete",
                "data": json.dumps({
                    "query_info": query_info,
                    "count": len(final_recs),
                    "recommendations": final_recs
                })
            }

        except Exception as e:
            yield {
                "event": "error",
                "data": json.dumps({"message": f"Streaming error: {str(e)}"})
            }

    return EventSourceResponse(event_generator())

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port, reload=False)
