from __future__ import annotations
import os
from ..spec.loader import Endpoint

_model = None

def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(os.getenv("RERANKER_MODEL",
                                        "cross-encoder/ms-marco-MiniLM-L-6-v2"))
    return _model

def rerank(query: str, candidates: list[Endpoint], top_k: int = 20) -> list[Endpoint]:
    if not candidates:
        return []
    from ..spec.query_hints import expand_query

    expanded = expand_query(query)
    scores = _get_model().predict(
        [(expanded, ep.to_rerank_text()) for ep in candidates],
        show_progress_bar=False,
    )
    ranked = sorted(zip(scores, candidates), key=lambda x: x[0], reverse=True)
    return [ep for _, ep in ranked[:top_k]]
