"""
ReviewSentry AI - Main FastAPI Application
------------------------------------------
Production-ready REST API & Web Server.
Serves interactive glassmorphism dashboard UI and provides policy audit endpoints.
"""

import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from policy_engine import audit_review, AuditResult, OFFICIAL_POLICIES
from backboard_client import ReviewSentrySynthesizer

app = FastAPI(
    title="ReviewSentry AI",
    description="AI-Powered Reputation Defense & Policy Violation Dispute Engine for Local Businesses & Freelancers",
    version="1.0.0",
)

# Enable CORS for cross-origin or local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

synthesizer = ReviewSentrySynthesizer()


# Request Schemas
class AuditRequest(BaseModel):
    review_text: str = Field(..., min_length=5, description="Full text of the review to audit")
    rating: int = Field(default=1, ge=1, le=5, description="Star rating of review (1-5)")
    business_name: str = Field(default="Brew & Bites Cafe", description="Name of the business")
    reviewer_name: Optional[str] = Field(default="Anonymous Reviewer", description="Name/Handle of reviewer")
    competitor_mentions: Optional[List[str]] = Field(default=None, description="Known competitors in neighborhood")


class DisputeRequest(BaseModel):
    review_text: str = Field(..., min_length=5)
    rating: int = Field(default=1, ge=1, le=5)
    business_name: str = Field(default="Brew & Bites Cafe")
    reviewer_name: str = Field(default="Anonymous Reviewer")


class ResponseRequest(BaseModel):
    review_text: str = Field(..., min_length=5)
    business_name: str = Field(default="Brew & Bites Cafe")
    reviewer_name: str = Field(default="Valued Guest")


# Pre-loaded Sample Reviews for Instant 1-Click Judge Testing
SAMPLE_REVIEWS = [
    {
        "id": "sample-competitor",
        "title": "Competitor Attack (Conflict of Interest)",
        "rating": 1,
        "text": "Worst coffee ever. Go to the other cafe next door instead of here, their beans are ten times fresher!",
        "expected_violation": "Google Maps Policy § 2.1 - Conflict of Interest",
    },
    {
        "id": "sample-defamation",
        "title": "Unsubstantiated Defamation (Criminal Charge)",
        "rating": 1,
        "text": "The manager is a thief and scammer who stole my wallet from the counter! Call the police on them!",
        "expected_violation": "Google Maps Policy § 3.2 - Harassment & Unsubstantiated Accusations",
    },
    {
        "id": "sample-extortion",
        "title": "Review Extortion / Blackmail",
        "rating": 1,
        "text": "I asked for a free refund and discount on my order or else I will leave 1 star everywhere. Bad business!",
        "expected_violation": "Google Maps Policy § 4.1 - Coercion & Review Extortion",
    },
    {
        "id": "sample-offtopic",
        "title": "Off-Topic Non-Customer Rant",
        "rating": 1,
        "text": "Never been here and never stepped foot inside, but I saw on TikTok that their politics are terrible! Boycott!",
        "expected_violation": "Google Maps Policy § 1.4 - Off-Topic & Inauthentic Experience",
    },
    {
        "id": "sample-genuine",
        "title": "Genuine Customer Complaint (Food/Service)",
        "rating": 1,
        "text": "The pasta was cold when it arrived and our waiter took 30 minutes to bring the bill. Disappointed.",
        "expected_violation": "None (Genuine Customer Feedback -> Triggers De-escalation Recovery)",
    },
]


@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "app": "ReviewSentry AI",
        "version": "1.0.0",
        "backboard_sdk_active": synthesizer.client is not None,
        "engine": "Google Maps Content Policy Deterministic Guardrail + Gemma 2",
    }


@app.get("/api/samples")
async def get_samples():
    """Returns curated benchmark reviews for instant demonstration."""
    return {"samples": SAMPLE_REVIEWS}


@app.get("/api/policies")
async def get_policies():
    """Returns official Google Maps Content Policy rulebook."""
    return {"policies": OFFICIAL_POLICIES}


@app.post("/api/audit")
async def api_audit(req: AuditRequest):
    """Audits review text deterministically against platform policies."""
    result = audit_review(
        review_text=req.review_text,
        rating=req.rating,
        business_name=req.business_name,
        competitor_mentions=req.competitor_mentions,
    )
    return result


@app.post("/api/analyze")
async def api_full_analysis(req: AuditRequest):
    """
    Comprehensive all-in-one analysis:
    Runs deterministic audit, then generates either formal dispute notice
    or 3-tier customer de-escalation response.
    """
    audit = audit_review(
        review_text=req.review_text,
        rating=req.rating,
        business_name=req.business_name,
        competitor_mentions=req.competitor_mentions,
    )

    dispute_notice = None
    deescalation_responses = None

    if audit.is_disputable and audit.primary_violation:
        dispute_notice = await synthesizer.generate_dispute_notice(
            audit=audit,
            review_text=req.review_text,
            business_name=req.business_name,
            reviewer_name=req.reviewer_name or "Anonymous Reviewer",
        )
    else:
        deescalation_responses = await synthesizer.generate_deescalation_responses(
            review_text=req.review_text,
            business_name=req.business_name,
            reviewer_name=req.reviewer_name or "Valued Guest",
        )

    return {
        "audit": audit,
        "dispute_notice": dispute_notice,
        "deescalation_responses": deescalation_responses,
    }


# Static Files & Frontend Mount
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        {"message": "ReviewSentry AI API is running. Access /api/health or view /docs for API documentation."}
    )


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
