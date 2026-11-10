from backend.explain import ExplanationService, build_facts, rules_explanation, ungrounded_numbers
from backend.llm import LLMError, LLMResult
from backend.scoring import ScoringEngine

DOCTOR = ScoringEngine().all()[0]


class FakeLLM:
    def __init__(self, text=None, error=None):
        self.text, self.error, self.calls = text, error, 0

    def complete(self, system, user, max_tokens=160):
        self.calls += 1
        if self.error:
            raise self.error
        return LLMResult(self.text, "fake-model", 1)


def test_grounding_accepts_numbers_from_facts():
    facts = build_facts(DOCTOR, 20)
    text = f"Up {DOCTOR['growthPct3m']}% in 3 months and {DOCTOR['daysSinceLastVisit']} days since a visit."
    assert ungrounded_numbers(text, facts) == []


def test_grounding_flags_invented_numbers():
    facts = build_facts(DOCTOR, 20)
    assert ungrounded_numbers("Prescriptions rose 987% last quarter.", facts) == ["987"]


def test_llm_answer_is_used_and_cached():
    text = f"Rx up {DOCTOR['growthPct3m']}% and {DOCTOR['daysSinceLastVisit']} days since last visit."
    llm = FakeLLM(text=text)
    svc = ExplanationService(llm)
    first = svc.explain(DOCTOR, 20)
    second = svc.explain(DOCTOR, 20)
    assert first.source == "llm" and first.text == text and not first.cached
    assert second.cached and llm.calls == 1


def test_hallucinated_numbers_fall_back_to_rules():
    svc = ExplanationService(FakeLLM(text="Volume grew 555% to 9999 scripts."))
    res = svc.explain(DOCTOR, 20)
    assert res.source == "rules"
    assert res.fallbackReason.startswith("ungrounded_numbers")
    assert res.text == rules_explanation(DOCTOR)


def test_llm_failure_falls_back_and_is_not_cached():
    llm = FakeLLM(error=LLMError("http_503", 3))
    svc = ExplanationService(llm)
    res = svc.explain(DOCTOR, 20)
    assert res.source == "rules" and res.fallbackReason == "llm_error:http_503" and res.attempts == 3
    svc.explain(DOCTOR, 20)
    assert llm.calls == 2


def test_feature_flag_off_skips_llm():
    llm = FakeLLM(text="anything")
    res = ExplanationService(llm, enabled=False).explain(DOCTOR, 20)
    assert res.source == "rules" and res.fallbackReason == "feature_flag_off" and llm.calls == 0


def test_rules_explanation_only_uses_real_numbers():
    for d in ScoringEngine().all():
        assert ungrounded_numbers(rules_explanation(d), build_facts(d, 20)) == []
