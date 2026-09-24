from __future__ import annotations


def rank_hits(hits: list[dict]) -> list[dict]:
    ranked = sorted(hits, key=lambda hit: float(hit.get("quantumScore") or 0.0), reverse=True)
    for index, hit in enumerate(ranked, start=1):
        hit["rank"] = index
    return ranked
