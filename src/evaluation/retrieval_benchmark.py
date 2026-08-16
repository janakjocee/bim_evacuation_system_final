"""Reproducible regulation evidence-retrieval benchmark."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable

import numpy as np

from src.nlp.regulation_parser import RegulationClause, RegulationParser
from src.utils.helpers import sha256_file


def load_queries(path: Path) -> list[Dict[str, Any]]:
    return [
        json.loads(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def legacy_keyword_rank(query: str, clauses: list[RegulationClause]) -> list[str]:
    """Reproduce the original whitespace-token overlap ranking."""
    query_words = set(query.lower().split())
    scored = []
    for position, clause in enumerate(clauses):
        overlap = len(query_words & set(clause.text.lower().split()))
        if overlap:
            scored.append((overlap / max(len(query_words), 1), -position, clause.clause_id))
    return [clause_id for _, _, clause_id in sorted(scored, reverse=True)]


def normalised_keyword_rank(query: str, clauses: list[RegulationClause]) -> list[str]:
    """Rank with punctuation-safe token overlap and deterministic tie-breaking."""
    query_words = _tokens(query)
    scored = []
    for position, clause in enumerate(clauses):
        clause_words = _tokens(f"{clause.clause_id} {clause.text}")
        overlap = len(query_words & clause_words)
        if overlap:
            score = overlap / max(len(query_words), 1)
            scored.append((score, -position, clause.clause_id))
    return [clause_id for _, _, clause_id in sorted(scored, reverse=True)]


def tfidf_ranks(queries: list[str], clauses: list[RegulationClause]) -> list[list[str]]:
    from sklearn.feature_extraction.text import TfidfVectorizer

    clause_texts = [f"{clause.clause_id} {clause.text}" for clause in clauses]
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english", sublinear_tf=True)
    clause_matrix = vectorizer.fit_transform(clause_texts)
    query_matrix = vectorizer.transform(queries)
    similarities = query_matrix @ clause_matrix.T
    return [
        [clauses[index].clause_id for index in np.asarray(row.toarray()).ravel().argsort()[::-1]]
        for row in similarities
    ]


def embedding_ranks(
    queries: list[str],
    clauses: list[RegulationClause],
    model_name: str,
) -> list[list[str]]:
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    clause_texts = [f"{clause.clause_id} {clause.text}" for clause in clauses]
    clause_vectors = model.encode(clause_texts, normalize_embeddings=True, show_progress_bar=False)
    query_vectors = model.encode(queries, normalize_embeddings=True, show_progress_bar=False)
    similarities = np.asarray(query_vectors) @ np.asarray(clause_vectors).T
    return [
        [clauses[index].clause_id for index in row.argsort()[::-1]]
        for row in similarities
    ]


def retrieval_metrics(query_rows: list[Dict[str, Any]], rankings: list[list[str]]) -> Dict[str, Any]:
    reciprocal_ranks = []
    recall_at_1 = []
    recall_at_3 = []
    cases = []
    for row, ranking in zip(query_rows, rankings):
        relevant = set(row["relevant_clause_ids"])
        first_rank = next((index + 1 for index, value in enumerate(ranking) if value in relevant), None)
        reciprocal_ranks.append(0 if first_rank is None else 1 / first_rank)
        recall_at_1.append(float(bool(relevant & set(ranking[:1]))))
        recall_at_3.append(float(bool(relevant & set(ranking[:3]))))
        cases.append({
            "query_id": row["query_id"],
            "expected": sorted(relevant),
            "top_3": ranking[:3],
            "first_relevant_rank": first_rank,
        })
    count = max(len(query_rows), 1)
    return {
        "query_count": len(query_rows),
        "recall_at_1": round(sum(recall_at_1) / count, 4),
        "recall_at_3": round(sum(recall_at_3) / count, 4),
        "mrr": round(sum(reciprocal_ranks) / count, 4),
        "cases": cases,
    }


def evaluate_source(
    source_id: str,
    source_path: Path,
    all_queries: list[Dict[str, Any]],
    include_embeddings: bool = False,
    embedding_model: str = "all-MiniLM-L6-v2",
) -> Dict[str, Any]:
    source_path = Path(source_path)
    source_text = source_path.read_text(encoding="utf-8")
    parser = RegulationParser()
    clauses = parser.parse(source_text)
    queries = [row for row in all_queries if row["source_id"] == source_id]
    query_texts = [row["query"] for row in queries]

    methods = {
        "legacy_whitespace_overlap": retrieval_metrics(
            queries,
            [legacy_keyword_rank(query, clauses) for query in query_texts],
        ),
        "normalised_token_overlap": retrieval_metrics(
            queries,
            [normalised_keyword_rank(query, clauses) for query in query_texts],
        ),
        "tfidf_lexical": retrieval_metrics(queries, tfidf_ranks(query_texts, clauses)),
    }
    embedding_status = "not_requested"
    if include_embeddings:
        try:
            methods["sentence_embeddings"] = retrieval_metrics(
                queries,
                embedding_ranks(query_texts, clauses, embedding_model),
            )
            embedding_status = "completed"
        except Exception as exc:
            embedding_status = f"unavailable: {type(exc).__name__}: {exc}"

    return {
        "source_id": source_id,
        "source_file_name": source_path.name,
        "source_sha256": sha256_file(source_path),
        "clause_count": len(clauses),
        "query_count": len(queries),
        "methods": methods,
        "embedding_model": embedding_model,
        "embedding_status": embedding_status,
    }


def evaluate_sources(
    queries_path: Path,
    sources: Dict[str, Path],
    include_embeddings: bool = False,
) -> Dict[str, Any]:
    queries = load_queries(queries_path)
    reports = [
        evaluate_source(source_id, path, queries, include_embeddings=include_embeddings)
        for source_id, path in sources.items()
    ]
    return {
        "benchmark": "regulation_evidence_retrieval_v1",
        "query_judgement_status": "codex_assisted_requires_project_author_review",
        "sources": reports,
        "limitations": [
            "Expected relevance is not an independent fire-engineer judgement.",
            "Queries were authored after inspecting source documents.",
            "Retrieval metrics do not validate legal interpretation or engineering compliance.",
        ],
    }
