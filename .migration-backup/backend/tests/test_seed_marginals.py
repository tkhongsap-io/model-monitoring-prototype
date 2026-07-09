"""Portfolio-marginals assertions — PRD Appendix B §B.8 ("the seeded counter set")."""
from collections import Counter

from app.seeds_loader import build_rows

APPROVED = {"privacy_status": "Approved", "security_status": "Approved", "rai_status": "Complete"}


def test_seeded_counter_set():
    rows = build_rows(seed=42)
    assert len(rows) == 130

    status = Counter(r["status"] for r in rows)
    assert status["production"] == 38
    assert status["PoV"] + status["UAT"] == 36           # in-development
    assert status["requirements"] == 40                  # requirements/not-started
    assert status["paused"] == 3
    assert status["retired"] == 13                       # retired/cancelled

    assert sum(1 for r in rows if r["risk_tier"] == "Unknown") == 12

    hi_gaps = [r for r in rows if r["risk_tier"] == "High" and r["status"] == "production"
               and any(r.get(k) != v for k, v in APPROVED.items())]
    assert len(hi_gaps) == 4, [r["registry_id"] for r in hi_gaps]


def test_determinism():
    a = build_rows(seed=42)
    b = build_rows(seed=42)
    assert a == b


def test_deep_rows_complete():
    rows = {r["registry_id"]: r for r in build_rows(seed=42)}
    p01, p02 = rows["AICT-P01"], rows["AICT-P02"]
    for r in (p01, p02):
        assert r["status"] == "production" and r["risk_tier"] == "High"
        for f in ("business_owner", "technical_owner", "monitoring_owner"):
            assert r[f] != "Unknown"
    assert p02["feedback_status"] == "Unknown"           # declared-reason Unknown
    assert "finding" in p02["feedback_unknown_reason"]
    assert p01["feedback_status"] == "Green"
