"""Generate a short, grounded explanation of why an HCP is prioritised.

Flow: build a facts payload -> ask the LLM -> verify every number in the
answer exists in the facts -> otherwise fall back to a deterministic template.
Results are cached in-process so repeated clicks do not re-hit the LLM.
"""

from __future__ import annotations

import json
import re
import threading
import time
from dataclasses import asdict, dataclass
from typing import Any

from .llm import LLMClient, LLMError
from .scoring import TREND_WINDOW_MONTHS

SYSTEM_PROMPT = (
    "You help pharmaceutical sales reps decide which healthcare professional (HCP) to visit next. "
    "Using ONLY the JSON facts provided, write one or two sentences (max 45 words) explaining why "
    "this HCP is or is not a priority right now. Mention the prescription trend and the days since "
    "the last visit. Only use numbers that appear in the facts, never estimate or invent figures. "
    "Write plain text with no preamble, markdown, or quotes."
)

_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")


@dataclass
class Explanation:
    doctorId: str
    text: str
    source: str  # "llm" | "rules"
    model: str | None
    cached: bool
    latencyMs: int
    attempts: int
    fallbackReason: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_facts(doctor: dict[str, Any], total: int) -> dict[str, Any]:
    """The only information the LLM is allowed to use."""
    return {
        "name": doctor["name"],
        "specialty": doctor["specialty"],
        "city": doctor["city"],
        "priorityRank": doctor["rank"],
        "totalHcps": total,
        "priorityScore": doctor["score"],
        "rxLastMonth": doctor["rxLastMonth"],
        f"rx{TREND_WINDOW_MONTHS}MonthsEarlier": doctor["rxWindowStart"],
        f"rxChangePct{TREND_WINDOW_MONTHS}Months": doctor["growthPct3m"],
        "rxTrendDirection": _direction(doctor["growthPct3m"]),
        "daysSinceLastVisit": doctor["daysSinceLastVisit"],
        "monthlyRxHistoryOldestFirst": doctor["rxHistory"],
    }


def allowed_numbers(facts: dict[str, Any]) -> set[float]:
    nums: set[float] = {float(TREND_WINDOW_MONTHS), float(len(facts["monthlyRxHistoryOldestFirst"]))}
    for value in facts.values():
        values = value if isinstance(value, list) else [value]
        for v in values:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                nums.add(float(v))
                nums.add(abs(float(v)))
    return nums


def ungrounded_numbers(text: str, facts: dict[str, Any]) -> list[str]:
    """Return numbers in `text` that do not appear in `facts` (empty list = grounded)."""
    allowed = allowed_numbers(facts)
    bad = []
    for raw in _NUMBER_RE.findall(text):
        value = float(raw.replace(",", ""))
        # Allow +/-1 so "30%" still matches a fact of 29.6 that was rounded to 30.
        if not any(abs(value - a) <= 1 for a in allowed):
            bad.append(raw)
    return bad


def rules_explanation(doctor: dict[str, Any]) -> str:
    """Deterministic, data-only explanation used when the LLM is unavailable."""
    first = doctor["name"]
    growth = doctor["growthPct3m"]
    days = doctor["daysSinceLastVisit"]
    start, end = doctor["rxWindowStart"], doctor["rxLastMonth"]

    if growth > 0:
        trend = f"prescriptions grew {growth}% over the last {TREND_WINDOW_MONTHS} months ({start} to {end})"
    elif growth < 0:
        trend = f"prescriptions fell {abs(growth)}% over the last {TREND_WINDOW_MONTHS} months ({start} to {end})"
    else:
        trend = f"prescriptions were flat over the last {TREND_WINDOW_MONTHS} months at {end}"

    if growth >= 10 and days >= 30:
        verdict = "momentum is building and the relationship needs attention, so now is a good time to visit."
    elif growth >= 10:
        verdict = "they were seen recently, so a lighter touch can keep the momentum going."
    elif days >= 45:
        verdict = "it has been a while since the last visit, so a check-in could help reverse the trend."
    else:
        verdict = "with a recent visit and a soft trend, other HCPs are likely a better use of time this week."
    return f"{first}'s {trend}, and the last visit was {days} days ago; {verdict}"


class ExplanationService:
    def __init__(self, llm: LLMClient | None, enabled: bool = True, ttl_s: float = 3600) -> None:
        self._llm = llm
        self._enabled = enabled
        self._ttl_s = ttl_s
        # In-process cache. Each serverless instance has its own copy; a shared
        # store such as Redis would be the next step in production.
        self._cache: dict[str, tuple[float, Explanation]] = {}
        self._lock = threading.Lock()

    @property
    def llm_enabled(self) -> bool:
        return self._enabled and self._llm is not None

    def explain(self, doctor: dict[str, Any], total: int) -> Explanation:
        key = f"{doctor['id']}:{doctor['score']}"
        with self._lock:
            hit = self._cache.get(key)
        if hit and time.monotonic() - hit[0] < self._ttl_s:
            return Explanation(**{**asdict(hit[1]), "cached": True, "latencyMs": 0})

        started = time.perf_counter()
        result = self._generate(doctor, total)
        result.latencyMs = round((time.perf_counter() - started) * 1000)
        # Only cache LLM answers; a fallback might be due to a transient outage.
        if result.source == "llm":
            with self._lock:
                self._cache[key] = (time.monotonic(), result)
        return result

    def _generate(self, doctor: dict[str, Any], total: int) -> Explanation:
        def fallback(reason: str, attempts: int = 0) -> Explanation:
            return Explanation(doctor["id"], rules_explanation(doctor), "rules", None, False, 0, attempts, reason)

        if not self._enabled:
            return fallback("feature_flag_off")
        if self._llm is None:
            return fallback("llm_not_configured")

        facts = build_facts(doctor, total)
        try:
            res = self._llm.complete(SYSTEM_PROMPT, json.dumps(facts))
        except LLMError as err:
            return fallback(f"llm_error:{err.reason}", err.attempts)

        if not res.text:
            return fallback("empty_response", res.attempts)
        if bad := ungrounded_numbers(res.text, facts):
            return fallback(f"ungrounded_numbers:{','.join(bad)}", res.attempts)
        return Explanation(doctor["id"], res.text, "llm", res.model, False, 0, res.attempts, None)


def _direction(growth_pct: int) -> str:
    if growth_pct > 0:
        return "up"
    if growth_pct < 0:
        return "down"
    return "flat"
