from backend.scoring import ScoringEngine


def test_ranks_are_sorted_by_score_descending():
    doctors = ScoringEngine().all()
    assert len(doctors) == 20
    assert [d["rank"] for d in doctors] == list(range(1, 21))
    scores = [d["score"] for d in doctors]
    assert scores == sorted(scores, reverse=True)


def test_score_rewards_growth_and_time_since_visit(tmp_path):
    data = tmp_path / "doctors.json"
    data.write_text("""[
      {"id": "a", "name": "A", "specialty": "S", "city": "C", "rxHistory": [10,10,10,10,10,10], "daysSinceLastVisit": 5},
      {"id": "b", "name": "B", "specialty": "S", "city": "C", "rxHistory": [10,10,10,10,12,14], "daysSinceLastVisit": 5},
      {"id": "c", "name": "C", "specialty": "S", "city": "C", "rxHistory": [10,10,10,10,10,10], "daysSinceLastVisit": 80}
    ]""")
    engine = ScoringEngine(data)
    a, b, c = engine.get("a"), engine.get("b"), engine.get("c")
    assert b["score"] > a["score"]  # faster growth -> higher
    assert c["score"] > a["score"]  # longer since visit -> higher
    assert b["growthPct3m"] == 40
    assert b["rxLastMonth"] == 14 and b["rxWindowStart"] == 10


def test_breakdown_adds_up_to_score():
    for d in ScoringEngine().all():
        assert d["breakdown"]["growthPoints"] + d["breakdown"]["recencyPoints"] == d["score"]
        assert 0 <= d["score"] <= 100
