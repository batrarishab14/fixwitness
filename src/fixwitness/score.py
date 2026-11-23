"""Confidence score.

The score is a transparent heuristic, not the probability that the fix is correct.

* It is 0 when the check fails: any valid input changed, the fix is still exploitable, or it
  still fails on the incident input.
* Evidence strength uses the "rule of three": if the fix gives identical output on n
  independent inputs, the 95% upper bound on the share of such inputs it would change is
  about 3/n. Evidence strength is therefore 1 - 3/n.
* Claims must be demonstrated on the original: that an attack payload worked on it (security
  fixes) and/or that the incident input broke it (repairs). If a claim could not be
  demonstrated, "the fix resolves it" is unproven and the score is multiplied by 0.7.

score = round(100 * evidence_strength * reproduction_factor)
"""

from __future__ import annotations

UNREPRODUCED_FACTOR = 0.7
HIGH = 90
MEDIUM = 75

METHOD = (
    "score = 100 x (1 - 3/n) x r, where n is the number of valid inputs that gave identical "
    "output (rule of three) and r is 1.0 if every claim was demonstrated on the original (the exploit "
    "worked on it, the incident input broke it), else 0.7. 0 if any valid input changed, the fix is "
    "still exploitable or it still fails on the incident input. A heuristic, not a probability."
)


def confidence(verdict: str, identical_valid: int, reproduced: bool) -> dict:
    if verdict != "PASS" or identical_valid <= 0:
        return {
            "score": 0,
            "level": "NONE",
            "components": {
                "valid_inputs_identical": identical_valid,
                "evidence_strength": 0.0,
                "reproduction_factor": 1.0 if reproduced else UNREPRODUCED_FACTOR,
                "original_exploit_reproduced": reproduced,
            },
            "method": METHOD,
        }
    evidence = max(0.0, 1.0 - 3.0 / identical_valid)
    factor = 1.0 if reproduced else UNREPRODUCED_FACTOR
    score = round(100 * evidence * factor)
    level = "HIGH" if score >= HIGH else "MEDIUM" if score >= MEDIUM else "LOW"
    return {
        "score": score,
        "level": level,
        "components": {
            "valid_inputs_identical": identical_valid,
            "evidence_strength": round(evidence, 3),
            "reproduction_factor": factor,
            "original_exploit_reproduced": reproduced,
        },
        "method": METHOD,
    }
