"""
ReviewSentry AI - Production Automated Test Suite
-------------------------------------------------
Comprehensive Pytest suite with 20 automated test cases.
Validates deterministic policy extraction, evidence capture,
AI synthesis, and FastAPI endpoint stability.
"""

import asyncio
import pytest
from fastapi.testclient import TestClient

from main import app
from policy_engine import (
    audit_review,
    PolicyViolationType,
    OFFICIAL_POLICIES,
    AuditResult,
)
from backboard_client import ReviewSentrySynthesizer

client = TestClient(app)
synthesizer = ReviewSentrySynthesizer()


# ---------------------------------------------------------
# Unit Tests: Deterministic Policy Engine (1-10)
# ---------------------------------------------------------

def test_competitor_conflict_of_interest_detection():
    review = "Terrible service. Go to the other cafe next door instead of here!"
    result = audit_review(review, rating=1)
    assert result.is_disputable is True
    assert result.primary_violation is not None
    assert result.primary_violation.category == PolicyViolationType.CONFLICT_OF_INTEREST
    assert result.recommended_action == "DISPUTE_LEGAL_ESCALATION"
    assert len(result.evidence_snippets) > 0


def test_defamation_theft_scam_detection():
    review = "The cashier is a thief and scammer who stole my purse! Criminals!"
    result = audit_review(review, rating=1)
    assert result.is_disputable is True
    assert result.primary_violation.category == PolicyViolationType.DEFAMATION_AND_HARASSMENT
    assert any("thief" in snip or "scammer" in snip for snip in result.evidence_snippets)


def test_extortion_blackmail_refund_demand():
    review = "Give me a free coffee or else I will leave 1 star on every review site."
    result = audit_review(review, rating=1)
    assert result.is_disputable is True
    assert result.primary_violation.category == PolicyViolationType.COERCION_AND_BLACKMAIL


def test_off_topic_non_visitor_detection():
    review = "Never been here and never stepped foot inside, but boycott them for politics!"
    result = audit_review(review, rating=1)
    assert result.is_disputable is True
    assert result.primary_violation.category == PolicyViolationType.OFF_TOPIC_OR_FAKE


def test_profanity_vulgarity_detection():
    review = "This place is complete bullshit run by an asshole manager."
    result = audit_review(review, rating=1)
    assert result.is_disputable is True
    assert result.primary_violation.category == PolicyViolationType.PROFANITY_AND_VULGARITY


def test_genuine_complaint_cold_food_not_disputable():
    review = "The soup was cold and the steak was overcooked. Not worth the price."
    result = audit_review(review, rating=1)
    assert result.is_disputable is False
    assert result.primary_violation is None
    assert result.recommended_action == "DEESCALATE_AND_RECOVER"


def test_genuine_complaint_slow_service_not_disputable():
    review = "Waited 45 minutes for our table even though we had a booking. Disappointing."
    result = audit_review(review, rating=2)
    assert result.is_disputable is False
    assert result.primary_violation is None


def test_dynamic_competitor_name_matching():
    review = "Honestly just visit CoffeeGlory down the avenue, they are much better."
    result = audit_review(review, rating=1, competitor_mentions=["CoffeeGlory"])
    assert result.is_disputable is True
    assert result.primary_violation.category == PolicyViolationType.CONFLICT_OF_INTEREST
    assert any("CoffeeGlory" in snip for snip in result.evidence_snippets)


def test_confidence_score_scaling():
    critical_review = "The owner is a thief and scammer!"
    critical_result = audit_review(critical_review, rating=1)
    assert critical_result.confidence_score >= 0.90

    high_star_review = "The owner is a thief and scammer!"
    high_star_result = audit_review(high_star_review, rating=4)
    assert high_star_result.confidence_score < critical_result.confidence_score


def test_evidence_snippet_extraction():
    review = "The food was okay but the owner fired me because I am an ex-employee who knows too much."
    result = audit_review(review, rating=1)
    assert result.is_disputable is True
    assert any("ex-employee" in snip or "fired me" in snip for snip in result.evidence_snippets)


# ---------------------------------------------------------
# Integration Tests: Backboard & AI Synthesis (11-12)
# ---------------------------------------------------------

def test_dispute_notice_generation_format():
    review = "Go to the other cafe next door instead of here, their food is way better!"
    audit = audit_review(review, rating=1, business_name="Brew Cafe")
    notice = asyncio.run(synthesizer.generate_dispute_notice(
        audit=audit,
        review_text=review,
        business_name="Brew Cafe",
        reviewer_name="TrollUser99",
    ))
    assert any(phrase in notice for phrase in ["Dispute", "Notice", "Google Maps", "Conflict of Interest"])
    assert "Brew Cafe" in notice
    assert "TrollUser99" in notice


def test_deescalation_response_3_tiers():
    review = "The soup was cold and arrived 30 minutes late."
    responses = asyncio.run(synthesizer.generate_deescalation_responses(
        review_text=review,
        business_name="Brew Cafe",
        reviewer_name="Sarah",
    ))
    assert "empathetic" in responses
    assert "action_oriented" in responses
    assert "concise" in responses
    assert len(responses["empathetic"]) > 10


# ---------------------------------------------------------
# API Tests: FastAPI Endpoints (13-20)
# ---------------------------------------------------------

def test_api_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ReviewSentry AI"


def test_api_samples_endpoint():
    response = client.get("/api/samples")
    assert response.status_code == 200
    samples = response.json().get("samples", [])
    assert len(samples) >= 5
    assert any(s["id"] == "sample-competitor" for s in samples)


def test_api_policies_endpoint():
    response = client.get("/api/policies")
    assert response.status_code == 200
    policies = response.json().get("policies", {})
    assert "CONFLICT_OF_INTEREST" in policies
    assert "DEFAMATION_AND_HARASSMENT" in policies


def test_api_audit_endpoint():
    payload = {
        "review_text": "This place is a scam and the manager is a thief!",
        "rating": 1,
        "business_name": "Test Bistro",
    }
    response = client.post("/api/audit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["is_disputable"] is True
    assert data["primary_violation"]["category"] == "DEFAMATION_AND_HARASSMENT"


def test_api_analyze_endpoint_disputable():
    payload = {
        "review_text": "Never stepped foot here, boycott them for their politics!",
        "rating": 1,
        "business_name": "Urban Coffee",
        "reviewer_name": "RandomBot",
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["audit"]["is_disputable"] is True
    assert any(phrase in data["dispute_notice"] for phrase in ["Dispute", "Notice", "Removal", "Google Maps"])


def test_api_analyze_endpoint_genuine():
    payload = {
        "review_text": "The chicken was dry and the restroom was dirty.",
        "rating": 2,
        "business_name": "Downtown Diner",
        "reviewer_name": "Mike",
    }
    response = client.post("/api/analyze", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["audit"]["is_disputable"] is False
    assert data["deescalation_responses"] is not None
    assert "empathetic" in data["deescalation_responses"]


def test_empty_or_short_input_validation():
    payload = {
        "review_text": "bad",  # Less than min_length=5
        "rating": 1,
    }
    response = client.post("/api/audit", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_high_star_rating_confidence_adjustment():
    review = "Worst manager fired me because I am an ex-employee."
    res1 = audit_review(review, rating=1)
    res5 = audit_review(review, rating=5)
    assert res1.confidence_score > res5.confidence_score
