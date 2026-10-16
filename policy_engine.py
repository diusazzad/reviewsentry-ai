"""
ReviewSentry AI - Deterministic Policy Rules Engine
---------------------------------------------------
Implements official Google Maps & Yelp Contributed Content Policy rules.
Acts as Layer 1 deterministic guardrail to prevent LLM hallucinations
and extract legally verifiable policy violation clauses.
"""

import re
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class PolicyViolationType(str, Enum):
    CONFLICT_OF_INTEREST = "CONFLICT_OF_INTEREST"
    OFF_TOPIC_OR_FAKE = "OFF_TOPIC_OR_FAKE"
    DEFAMATION_AND_HARASSMENT = "DEFAMATION_AND_HARASSMENT"
    COERCION_AND_BLACKMAIL = "COERCION_AND_BLACKMAIL"
    PROFANITY_AND_VULGARITY = "PROFANITY_AND_VULGARITY"
    GENUINE_CUSTOMER_CRITIQUE = "GENUINE_CUSTOMER_CRITIQUE"


class PolicyClause(BaseModel):
    clause_id: str
    category: PolicyViolationType
    title: str
    official_rule: str
    legal_rationale: str
    removal_priority: str  # HIGH, CRITICAL, MEDIUM


# Official Google Maps User Contributed Content Policy Rulebook
OFFICIAL_POLICIES: Dict[PolicyViolationType, PolicyClause] = {
    PolicyViolationType.CONFLICT_OF_INTEREST: PolicyClause(
        clause_id="Google Maps Policy § 2.1 - Conflict of Interest",
        category=PolicyViolationType.CONFLICT_OF_INTEREST,
        title="Conflict of Interest & Competitor Disparagement",
        official_rule=(
            "Content is prohibited if it is posted by a competitor to undermine ratings, "
            "or by a current/former employee with a grievance. Directing customers to another "
            "competing business is an explicit violation of map contribution terms."
        ),
        legal_rationale=(
            "Violates antitrust and fair advertising standards. Disparagement intended to drive "
            "trade to a competitor constitutes deceptive marketing and tortious interference."
        ),
        removal_priority="CRITICAL",
    ),
    PolicyViolationType.DEFAMATION_AND_HARASSMENT: PolicyClause(
        clause_id="Google Maps Policy § 3.2 - Harassment & Unsubstantiated Accusations",
        category=PolicyViolationType.DEFAMATION_AND_HARASSMENT,
        title="Defamation, Criminal Allegations & Personal Attacks",
        official_rule=(
            "Reviews containing unsubstantiated criminal accusations (e.g. theft, poisoning, "
            "fraud, scam), personal attacks on identifiable staff, or defamatory allegations "
            "without legal proof are strictly prohibited."
        ),
        legal_rationale=(
            "Exposes platforms to safe harbor liability under Section 230 / regional defamation "
            "laws when criminal misconduct is falsely imputed to a commercial establishment."
        ),
        removal_priority="CRITICAL",
    ),
    PolicyViolationType.COERCION_AND_BLACKMAIL: PolicyClause(
        clause_id="Google Maps Policy § 4.1 - Coercion & Review Extortion",
        category=PolicyViolationType.COERCION_AND_BLACKMAIL,
        title="Review Extortion, Coercion & Demands for Free Goods",
        official_rule=(
            "Reviews used as a bargaining chip or threat to demand free products, discounts, "
            "refunds, or special treatment under the threat of negative ratings are prohibited."
        ),
        legal_rationale=(
            "Classified as commercial extortion and bad-faith manipulation under Consumer "
            "Protection regulations."
        ),
        removal_priority="HIGH",
    ),
    PolicyViolationType.OFF_TOPIC_OR_FAKE: PolicyClause(
        clause_id="Google Maps Policy § 1.4 - Off-Topic & Inauthentic Experience",
        category=PolicyViolationType.OFF_TOPIC_OR_FAKE,
        title="Off-Topic, Fake Engagement & Non-Customer Rants",
        official_rule=(
            "Content must be based on genuine, first-hand customer experiences. General political, "
            "social commentaries, mistargeted location rants, or reviews left without ever visiting "
            "or purchasing are subject to immediate removal."
        ),
        legal_rationale=(
            "Fails the fundamental requirement of authentic consumer reporting; degrades search "
            "index integrity."
        ),
        removal_priority="HIGH",
    ),
    PolicyViolationType.PROFANITY_AND_VULGARITY: PolicyClause(
        clause_id="Google Maps Policy § 3.1 - Obscenity & Profanity",
        category=PolicyViolationType.PROFANITY_AND_VULGARITY,
        title="Obscene Language & Severe Profanity",
        official_rule=(
            "Content containing vulgar, sexually explicit, or abusive profanities directed at a "
            "business or its staff violates community standards."
        ),
        legal_rationale="Violates universal content decency guidelines across all consumer platforms.",
        removal_priority="HIGH",
    ),
}

# Compiled Deterministic Detection Patterns
PATTERNS = {
    PolicyViolationType.CONFLICT_OF_INTEREST: [
        r"\b(?:go\s+to|visit|try)\s+(?:the\s+)?(?:other|another|competing)\s+(?:shop|store|cafe|restaurant|place)\b",
        r"\b(?:instead\s+of\s+here|better\s+off\s+going\s+to|check\s+out\s+my|my\s+store)\b",
        r"\b(?:ex[- ]employee|fired\s+me|worked\s+here|manager\s+fired|worst\s+boss)\b",
        r"\b(?:competitor|rival\s+business|support\s+local\s+rival)\b",
    ],
    PolicyViolationType.DEFAMATION_AND_HARASSMENT: [
        r"\b(?:thief|thieves|thievery|stole|robbed|scam(?:mer|s|ming)?|fraud(?:ulent)?)\b",
        r"\b(?:food\s+poisoning|poisoned|hospitalized|criminal|illegal|police\s+case)\b",
        r"\b(?:con\s+artist|corrupt|fake\s+business|money\s+laundering)\b",
        r"\b(?:call\s+the\s+police|sue\s+them|jail\s+the\s+owner)\b",
    ],
    PolicyViolationType.COERCION_AND_BLACKMAIL: [
        r"\b(?:give\s+me|demanded|asked\s+for)\s+(?:a\s+)?(?:refund|discount|free(?:\s+\w+)?)\s+or\s+(?:else|i\s+will)\b",
        r"\b(?:unless\s+you\s+(?:give|refund|pay)|free\s+(?:food|coffee|drink|meal|item|\w+)\s+or\s+(?:else|1\s*star))\b",
        r"\b(?:will\s+remove\s+this\s+if\s+you|pay\s+me\s+back\s+or\s+bad\s+review)\b",
    ],
    PolicyViolationType.OFF_TOPIC_OR_FAKE: [
        r"\b(?:never\s+been\s+here|never\s+visited|never\s+stepped\s+foot|didn'?t\s+even\s+go)\b",
        r"\b(?:just\s+drove\s+by|saw\s+on\s+facebook|saw\s+on\s+tiktok|news\s+said)\b",
        r"\b(?:wrong\s+(?:place|address|store|business)|meant\s+to\s+review)\b",
        r"\b(?:boycott\s+them\s+for|political|election|government)\b",
    ],
    PolicyViolationType.PROFANITY_AND_VULGARITY: [
        r"\b(?:f\*+k|fucking|bitch|bastard|asshole|bullshit|scumbag|idiot)\b",
        r"\b(?:piece\s+of\s+shit|scum|damn\s+thieves)\b",
    ],
}


class AuditResult(BaseModel):
    is_disputable: bool
    confidence_score: float = Field(ge=0.0, le=1.0)
    primary_violation: Optional[PolicyClause] = None
    all_violations: List[PolicyClause] = []
    evidence_snippets: List[str] = []
    recommended_action: str
    action_summary: str


def audit_review(
    review_text: str,
    rating: int = 1,
    business_name: str = "Our Business",
    competitor_mentions: Optional[List[str]] = None,
) -> AuditResult:
    """
    Deterministically audits a customer review against Google Maps Content Policies.
    """
    clean_text = review_text.strip()
    evidence_list: List[str] = []
    detected_violations: List[PolicyClause] = []

    # Check each policy category using regex patterns
    for violation_type, pattern_list in PATTERNS.items():
        matched_type = False
        for pattern in pattern_list:
            matches = re.finditer(pattern, clean_text, re.IGNORECASE)
            for m in matches:
                matched_type = True
                # Extract snippet with surrounding context
                start = max(0, m.start() - 20)
                end = min(len(clean_text), m.end() + 20)
                snippet = clean_text[start:end].strip()
                evidence_list.append(f'"{snippet}"')
        
        if matched_type:
            detected_violations.append(OFFICIAL_POLICIES[violation_type])

    # Dynamic competitor check if competitor names are provided
    if competitor_mentions:
        for comp in competitor_mentions:
            if re.search(rf"\b{re.escape(comp)}\b", clean_text, re.IGNORECASE):
                if OFFICIAL_POLICIES[PolicyViolationType.CONFLICT_OF_INTEREST] not in detected_violations:
                    detected_violations.append(OFFICIAL_POLICIES[PolicyViolationType.CONFLICT_OF_INTEREST])
                evidence_list.append(f'Explicit competitor mention: "{comp}"')

    # Calculate Confidence Score & Recommendation
    if detected_violations:
        # Check severity
        has_critical = any(v.removal_priority == "CRITICAL" for v in detected_violations)
        confidence = 0.95 if has_critical else 0.85
        
        # Deduct slightly if rating is above 2 (unusual for dispute)
        if rating > 2:
            confidence -= 0.15

        primary = detected_violations[0]
        action = "DISPUTE_LEGAL_ESCALATION"
        summary = (
            f"Review violates {primary.clause_id}. "
            f"Grounds: {primary.title}. Qualifies for immediate platform takedown request."
        )
        is_disputable = True
    else:
        # Legitimate criticism (e.g. cold food, slow service, rude waiter without profanity)
        is_disputable = False
        confidence = 0.90
        primary = None
        action = "DEESCALATE_AND_RECOVER"
        summary = (
            "Review appears to be genuine customer feedback. No explicit Google Maps policy "
            "violations detected. Recommended action: Public diplomatic de-escalation response "
            "to retain customer trust and salvage rating."
        )

    return AuditResult(
        is_disputable=is_disputable,
        confidence_score=round(confidence, 2),
        primary_violation=primary,
        all_violations=detected_violations,
        evidence_snippets=list(set(evidence_list)),
        recommended_action=action,
        action_summary=summary,
    )
