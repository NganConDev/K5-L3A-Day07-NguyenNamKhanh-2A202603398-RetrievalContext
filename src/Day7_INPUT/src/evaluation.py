"""Evaluate retrieved evidence and preserve per-query traces."""
from __future__ import annotations

from typing import Any


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and sufficient evidence for a question."""
    gold_page = question.get("gold_page")
    gold_source = question.get("gold_source_id")
    evidence_quote = question.get("evidence_quote", "")

    hit1 = False
    evidence_hit3 = False
    evaluated_hits: list[dict[str, Any]] = []

    for hit in hits:
        source_match = gold_source is None or hit.get("source") == gold_source or hit.get("document_id") == gold_source
        page_match = gold_page is None or hit.get("page") == gold_page
        quote_match = False
        if evidence_quote:
            quote_match = evidence_quote.lower() in (hit.get("text") or "").lower()
        hit_ok = source_match and page_match
        evidence_ok = quote_match or (source_match and page_match)
        evaluated_hits.append(
            {
                "chunk_id": hit.get("chunk_id"),
                "source": hit.get("source"),
                "page": hit.get("page"),
                "text": hit.get("text"),
                "score": hit.get("score"),
                "hit_ok": hit_ok,
                "evidence_ok": evidence_ok,
            }
        )
        if hit_ok and not hit1:
            hit1 = True
        if evidence_ok and not evidence_hit3:
            evidence_hit3 = True

    return {
        "question_id": question.get("id"),
        "split": question.get("split"),
        "hit1": hit1,
        "evidence_hit3": evidence_hit3,
        "hits": evaluated_hits,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by strategy and dev/test split."""
    summary: dict[str, Any] = {"total": len(traces), "hit1": 0, "evidence_hit3": 0}
    for trace in traces:
        summary["hit1"] += 1 if trace.get("hit1") else 0
        summary["evidence_hit3"] += 1 if trace.get("evidence_hit3") else 0
    summary["hit1_rate"] = summary["hit1"] / max(summary["total"], 1)
    summary["evidence_hit3_rate"] = summary["evidence_hit3"] / max(summary["total"], 1)
    return summary
