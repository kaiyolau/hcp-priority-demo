"""Generate the synthetic HCP dataset used by the demo.

All data is fake. A fixed seed keeps the output stable so the committed
JSON file and the tests stay in sync.
"""

import json
import random
from pathlib import Path

SEED = 42
OUT = Path(__file__).resolve().parent.parent / "backend" / "data" / "doctors.json"

FIRST = ["Olivia", "Liam", "Emma", "Noah", "Ava", "Ethan", "Sophia", "Lucas", "Mia", "Benjamin",
         "Chloe", "Daniel", "Grace", "Samuel", "Hannah", "Arjun", "Mei", "Omar", "Priya", "Jonah"]
LAST = ["Tremblay", "Nguyen", "Singh", "MacDonald", "Chen", "Roy", "Patel", "Wilson", "Gagnon",
        "Kim", "Martin", "Ali", "Campbell", "Wong", "Lee", "Fraser", "Bouchard", "Sharma", "Clarke", "Park"]
SPECIALTIES = ["Cardiology", "Endocrinology", "Oncology", "Neurology", "Rheumatology", "Family Medicine"]
CITIES = ["Vancouver", "Toronto", "Montreal", "Calgary", "Ottawa", "Edmonton", "Victoria", "Halifax"]


def monthly_history(rng: random.Random) -> list[int]:
    """Six months of prescription volume with a per-doctor trend."""
    base = rng.randint(25, 140)
    monthly_drift = rng.uniform(-0.08, 0.12)
    values = []
    level = float(base)
    for _ in range(6):
        level *= 1 + monthly_drift + rng.uniform(-0.04, 0.04)
        values.append(max(3, round(level)))
    return values


def main() -> None:
    rng = random.Random(SEED)
    last_names = LAST[:]
    rng.shuffle(last_names)
    doctors = []
    for i in range(20):
        history = monthly_history(rng)
        doctors.append({
            "id": f"hcp-{i + 1:03d}",
            "name": f"Dr. {FIRST[i]} {last_names[i]}",
            "specialty": rng.choice(SPECIALTIES),
            "city": rng.choice(CITIES),
            # Oldest -> newest; the last entry is "last month".
            "rxHistory": history,
            "daysSinceLastVisit": rng.choice([3, 7, 12, 18, 25, 33, 41, 45, 52, 60, 68, 75, 90, 104, 120]),
        })
    OUT.write_text(json.dumps(doctors, indent=2) + "\n")
    print(f"wrote {len(doctors)} doctors to {OUT}")


if __name__ == "__main__":
    main()
