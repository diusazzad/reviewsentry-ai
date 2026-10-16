/**
 * ReviewSentry AI - Client Application Logic
 * Handles interactive audits, sample benchmarking, and dispute copying.
 */

document.addEventListener('DOMContentLoaded', () => {
  // Elements
  const form = document.getElementById('audit-form');
  const reviewText = document.getElementById('input-review-text');
  const charCounter = document.getElementById('char-counter');
  const businessName = document.getElementById('input-business-name');
  const reviewerName = document.getElementById('input-reviewer-name');
  const ratingInput = document.getElementById('input-rating');
  const competitorsInput = document.getElementById('input-competitors');
  const btnAnalyze = document.getElementById('btn-analyze');
  const btnSpinner = document.getElementById('btn-spinner');
  const btnText = btnAnalyze.querySelector('.btn-text');

  // UI State Panels
  const emptyState = document.getElementById('empty-state');
  const resultsContainer = document.getElementById('results-container');
  const scorecardBadge = document.getElementById('score-status-badge');
  const metricConfidence = document.getElementById('metric-confidence');
  const metricClause = document.getElementById('metric-clause');
  const evidenceBox = document.getElementById('evidence-box');
  const evidencePills = document.getElementById('evidence-pills');

  // Tabs
  const tabDisputeBtn = document.getElementById('tab-dispute-btn');
  const tabResponseBtn = document.getElementById('tab-response-btn');
  const tabDisputeContent = document.getElementById('tab-dispute-content');
  const tabResponseContent = document.getElementById('tab-response-content');

  // Output Fields
  const disputeText = document.getElementById('dispute-notice-text');
  const respEmpathetic = document.getElementById('resp-empathetic');
  const respAction = document.getElementById('resp-action');
  const respConcise = document.getElementById('resp-concise');

  // Sample Data Cache
  let samplesData = [];

  // 1. Textarea Character Counter
  reviewText.addEventListener('input', () => {
    const len = reviewText.value.length;
    charCounter.textContent = `${len} chars`;
  });

  // 2. Fetch Sample Reviews for Instant Click-to-Test
  fetch('/api/samples')
    .then(res => res.json())
    .then(data => {
      if (data && data.samples) {
        samplesData = data.samples;
      }
    })
    .catch(err => console.warn('Could not load samples dynamically:', err));

  // Sample Buttons Click Handlers
  document.querySelectorAll('.sample-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.sample-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const sampleId = btn.getAttribute('data-id');
      const sample = samplesData.find(s => s.id === sampleId) || getLocalFallbackSample(sampleId);

      if (sample) {
        reviewText.value = sample.text;
        ratingInput.value = sample.rating.toString();
        reviewerName.value = "John Doe (Reviewer)";
        charCounter.textContent = `${sample.text.length} chars`;
        // Trigger auto analysis for delightful UX
        runAnalysis();
      }
    });
  });

  // 3. Tab Switching
  tabDisputeBtn.addEventListener('click', () => {
    tabDisputeBtn.classList.add('active');
    tabResponseBtn.classList.remove('active');
    tabDisputeContent.style.display = 'block';
    tabResponseContent.style.display = 'none';
  });

  tabResponseBtn.addEventListener('click', () => {
    tabResponseBtn.classList.add('active');
    tabDisputeBtn.classList.remove('active');
    tabResponseContent.style.display = 'block';
    tabDisputeContent.style.display = 'none';
  });

  // 4. Form Submission
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    runAnalysis();
  });

  async function runAnalysis() {
    const text = reviewText.value.trim();
    if (text.length < 5) {
      alert('Please enter a review text with at least 5 characters.');
      return;
    }

    // Set Loading State
    setLoading(true);

    const comps = competitorsInput.value
      .split(',')
      .map(c => c.trim())
      .filter(c => c.length > 0);

    const payload = {
      review_text: text,
      rating: parseInt(ratingInput.value, 10),
      business_name: businessName.value.trim() || 'Our Business',
      reviewer_name: reviewerName.value.trim() || 'Anonymous Reviewer',
      competitor_mentions: comps.length > 0 ? comps : null,
    };

    try {
      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const data = await response.json();
      renderResults(data);
    } catch (err) {
      alert(`Analysis failed: ${err.message}. Please check if server is running.`);
      console.error(err);
    } finally {
      setLoading(false);
    }
  }

  function renderResults(data) {
    const audit = data.audit;

    emptyState.style.display = 'none';
    resultsContainer.style.display = 'flex';

    // 1. Scorecard
    if (audit.is_disputable) {
      scorecardBadge.className = 'score-status-badge disputable';
      scorecardBadge.innerHTML = '🚨 Policy Violation Confirmed (Takedown Ready)';
      metricClause.textContent = audit.primary_violation ? audit.primary_violation.clause_id : 'Content Violation';
      metricClause.style.color = '#f87171';
    } else {
      scorecardBadge.className = 'score-status-badge genuine';
      scorecardBadge.innerHTML = '🤝 Genuine Customer Feedback (Salvageable)';
      metricClause.textContent = 'Standard Critique (No Infraction)';
      metricClause.style.color = '#34d399';
    }

    metricConfidence.textContent = `${Math.round(audit.confidence_score * 100)}%`;

    // 2. Evidence Snippets
    evidencePills.innerHTML = '';
    if (audit.evidence_snippets && audit.evidence_snippets.length > 0) {
      evidenceBox.style.display = 'block';
      audit.evidence_snippets.forEach(snip => {
        const pill = document.createElement('span');
        pill.className = 'evidence-pill';
        pill.textContent = snip;
        evidencePills.appendChild(pill);
      });
    } else {
      evidenceBox.style.display = 'none';
    }

    // 3. Dispute Notice
    if (data.dispute_notice) {
      disputeText.textContent = data.dispute_notice;
      tabDisputeBtn.style.display = 'inline-block';
      tabDisputeBtn.click(); // Select dispute tab by default
    } else {
      disputeText.textContent = 'This review does not qualify for Google Maps legal dispute takedown as it does not violate platform policies.';
      tabResponseBtn.click(); // Select response tab if genuine
    }

    // 4. De-escalation Responses
    if (data.deescalation_responses) {
      respEmpathetic.textContent = data.deescalation_responses.empathetic || 'Apology response unavailable.';
      respAction.textContent = data.deescalation_responses.action_oriented || 'Action response unavailable.';
      respConcise.textContent = data.deescalation_responses.concise || 'Concise response unavailable.';
    }
  }

  function setLoading(loading) {
    btnAnalyze.disabled = loading;
    btnSpinner.style.display = loading ? 'inline-block' : 'none';
    btnText.style.display = loading ? 'none' : 'inline';
  }

  // 5. Copy to Clipboard Handlers
  document.getElementById('btn-copy-dispute').addEventListener('click', () => {
    copyToClipboard(disputeText.textContent, document.getElementById('btn-copy-dispute'));
  });

  document.querySelectorAll('.btn-copy-sm').forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-target');
      const text = document.getElementById(targetId).textContent;
      copyToClipboard(text, btn);
    });
  });

  function copyToClipboard(text, buttonElement) {
    if (!navigator.clipboard) {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = text;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      flashCopied(buttonElement);
      return;
    }

    navigator.clipboard.writeText(text).then(() => {
      flashCopied(buttonElement);
    }).catch(err => {
      console.error('Copy failed:', err);
    });
  }

  function flashCopied(btn) {
    const origText = btn.textContent;
    btn.textContent = '✓ Copied!';
    btn.style.background = '#10b981';
    btn.style.color = '#fff';
    setTimeout(() => {
      btn.textContent = origText;
      btn.style.background = '';
      btn.style.color = '';
    }, 1800);
  }

  // Local fallback samples if API is delayed
  function getLocalFallbackSample(id) {
    const fallbacks = {
      'sample-competitor': {
        rating: 1,
        text: 'Worst coffee ever. Go to the other cafe next door instead of here, their beans are ten times fresher!'
      },
      'sample-defamation': {
        rating: 1,
        text: 'The manager is a thief and scammer who stole my wallet from the counter! Call the police on them!'
      },
      'sample-extortion': {
        rating: 1,
        text: 'I asked for a free refund and discount on my order or else I will leave 1 star everywhere. Bad business!'
      },
      'sample-offtopic': {
        rating: 1,
        text: 'Never been here and never stepped foot inside, but I saw on TikTok that their politics are terrible! Boycott!'
      },
      'sample-genuine': {
        rating: 1,
        text: 'The pasta was cold when it arrived and our waiter took 30 minutes to bring the bill. Disappointed.'
      }
    };
    return fallbacks[id] || null;
  }
});
