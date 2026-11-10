"""Rule-based HCP priority scoring, computed with DuckDB.

This is a deliberately simple stand-in for a real ML model: the score rises
when prescriptions are growing quickly and when the HCP has not been visited
for a long time. Keeping it in SQL makes the formula easy to read and lets the
same query run against a much larger table (or Parquet files) unchanged.
"""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Any

import duckdb

DATA_FILE = Path(__file__).resolve().parent / "data" / "doctors.json"

SCORING_VERSION = "rules-v1"

# Weights and normalisation bounds for the two signals.
GROWTH_WEIGHT = 0.6
RECENCY_WEIGHT = 0.4
GROWTH_FLOOR = -0.20  # -20% or worse over 3 months -> 0 points
GROWTH_CEIL = 0.40  # +40% or better over 3 months -> full points
RECENCY_CAP_DAYS = 90  # 90+ days without a visit -> full points
TREND_WINDOW_MONTHS = 3

SCORING_SQL = f"""
WITH base AS (
    SELECT
        id,
        name,
        specialty,
        city,
        rxHistory AS rx_history,
        daysSinceLastVisit AS days_since_last_visit,
        rxHistory[len(rxHistory)] AS rx_last_month,
        rxHistory[len(rxHistory) - {TREND_WINDOW_MONTHS}] AS rx_window_start
    FROM doctors
),
signals AS (
    SELECT
        *,
        (rx_last_month - rx_window_start) / rx_window_start::DOUBLE AS growth_3m,
        greatest(0.0, least(1.0,
            ((rx_last_month - rx_window_start) / rx_window_start::DOUBLE - {GROWTH_FLOOR})
            / ({GROWTH_CEIL} - {GROWTH_FLOOR})
        )) AS growth_signal,
        least(1.0, days_since_last_visit / {RECENCY_CAP_DAYS}.0) AS recency_signal
    FROM base
)
SELECT
    *,
    round(100 * ({GROWTH_WEIGHT} * growth_signal + {RECENCY_WEIGHT} * recency_signal))::INTEGER AS score,
    row_number() OVER (
        ORDER BY {GROWTH_WEIGHT} * growth_signal + {RECENCY_WEIGHT} * recency_signal DESC, id
    ) AS rank
FROM signals
ORDER BY rank
"""


class ScoringEngine:
    """Loads the dataset into an in-memory DuckDB database and scores it."""

    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self._con = duckdb.connect(database=":memory:")
        self._lock = threading.Lock()
        self._con.execute(
            "CREATE TABLE doctors AS SELECT * FROM read_json(?, format = 'array')",
            [str(data_file)],
        )
        self._scored = self._run()
        self._by_id = {d["id"]: d for d in self._scored}

    def _run(self) -> list[dict[str, Any]]:
        # DuckDB connections are not safe to share across threads; use a cursor under a lock.
        with self._lock:
            cur = self._con.cursor()
            rel = cur.execute(SCORING_SQL)
            cols = [c[0] for c in rel.description]
            rows = rel.fetchall()
        return [_to_api(dict(zip(cols, row))) for row in rows]

    def all(self) -> list[dict[str, Any]]:
        return self._scored

    def get(self, doctor_id: str) -> dict[str, Any] | None:
        return self._by_id.get(doctor_id)


def _to_api(row: dict[str, Any]) -> dict[str, Any]:
    """Map a SQL row to the camelCase shape the frontend consumes."""
    growth_points = round(100 * GROWTH_WEIGHT * row["growth_signal"])
    return {
        "id": row["id"],
        "rank": int(row["rank"]),
        "name": row["name"],
        "specialty": row["specialty"],
        "city": row["city"],
        "score": int(row["score"]),
        "rxHistory": list(row["rx_history"]),
        "rxLastMonth": int(row["rx_last_month"]),
        "rxWindowStart": int(row["rx_window_start"]),
        "growthPct3m": round(100 * row["growth_3m"]),
        "daysSinceLastVisit": int(row["days_since_last_visit"]),
        "breakdown": {
            "growthPoints": growth_points,
            # Derive from the total so the two parts always add up after rounding.
            "recencyPoints": int(row["score"]) - growth_points,
        },
    }
