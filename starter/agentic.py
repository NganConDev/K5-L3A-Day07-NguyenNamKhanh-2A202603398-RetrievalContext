"""Example agent loop; connect a real model and the Day 6 retriever via adapters.

Adapters are intentionally not provided: Day 6 has no fixed database schema and
model providers differ. Never use fake adapters to report benchmark quality.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Protocol

STARTER_DIR = Path(__file__).resolve().parent
if str(STARTER_DIR) not in sys.path:
    sys.path.insert(0, str(STARTER_DIR))

try:
    from baseline import pack_context
except ModuleNotFoundError:  # pragma: no cover - package import fallback
    from starter.baseline import pack_context

ROOT = Path(__file__).resolve().parents[1]
DAY7_INPUT = ROOT / "src" / "Day7_INPUT"
if str(DAY7_INPUT / "src") not in sys.path:
    sys.path.insert(0, str(DAY7_INPUT / "src"))

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dependency may be absent in minimal environments
    load_dotenv = None

try:
    from embeddings import MyEmbedder
    from store import PgVectorStore
except Exception:  # pragma: no cover - only for environments without the Day 7 project import path
    MyEmbedder = None
    PgVectorStore = None


class Controller(Protocol):
    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        """Call a real model with a search tool; return normalized action.

        Search: {'action': 'search', 'query': '...'}.
        Final: {'action': 'answer', 'answer': '...', 'citations': ['chunk-id']}.
        Citations must also appear as [chunk-id] in the answer text.
        """
        ...


class Retriever(Protocol):
    def search(self, query: str, *, filters: dict[str, Any] | None, top_k: int) -> list[dict[str, Any]]:
        """Query the real Day 6 vector store with a compatible query embedding.

        Return each chunk's id, text, source_id, source, page, metadata and score.
        The query embedding model and dimension must match the document index.
        """
        ...


class SimpleRuleController:
    """Baseline controller: search first, then answer from the best available context.

    This is intentionally simple and deterministic: it does not call a paid model.
    It is useful as a baseline while you connect a real model later.
    """

    def decide(self, question: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        if not question or not str(question).strip():
            raise ValueError("question không hợp lệ")

        if history and history[-1].get("context_ids"):
            top_id = history[-1]["context_ids"][0]
            context = history[-1].get("context", "")
            answer = context.strip()[:300].replace("\n", " ")
            if len(answer) > 180:
                answer = answer[:177].rstrip() + "..."
            return {
                "action": "answer",
                "answer": f"{answer} [{top_id}]",
                "citations": [top_id],
            }
        return {"action": "search", "query": question.strip()}


class VectorStoreRetriever:
    """Real baseline retriever for the Day 7 PostgreSQL + pgvector store."""

    def __init__(
        self,
        database_url: str | None = None,
        *,
        strategy: str = "A",
        model_name: str = "tfidf-local",
        top_k: int = 3,
    ) -> None:
        if PgVectorStore is None or MyEmbedder is None:
            raise RuntimeError("Day 7 vector-store modules are not available in the current Python environment.")

        if database_url is None:
            env_path = DAY7_INPUT / ".env"
            if env_path.exists() and load_dotenv is not None:
                load_dotenv(env_path)
            database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is missing. Check src/Day7_INPUT/.env")

        self.database_url = database_url
        self.strategy = strategy
        self.embedder = MyEmbedder(model_name=model_name)
        self.top_k = top_k
        self._fitted = False

    def _fit_if_needed(self) -> None:
        if self._fitted:
            return
        with __import__("psycopg").connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT text FROM chunks WHERE strategy = %s ORDER BY chunk_id LIMIT 5000",
                    (self.strategy,),
                )
                rows = [r[0] for r in cur.fetchall()]
        if not rows:
            raise RuntimeError(
                "No rows found in the pgvector table. Run the Day 7 ingestion pipeline before using the retriever."
            )
        self.embedder.fit(rows)
        self._fitted = True

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        if not query or not str(query).strip():
            raise ValueError("query không hợp lệ")
        self._fit_if_needed()
        query_vector = self.embedder.embed_query(str(query))
        store = PgVectorStore(self.database_url, self.embedder.dimensions)
        hits = store.search(self.strategy, query_vector, top_k=top_k or self.top_k, filters=filters or {})
        normalized: list[dict[str, Any]] = []
        for hit in hits:
            normalized.append(
                {
                    "id": hit.get("chunk_id"),
                    "text": hit.get("text", ""),
                    "source_id": hit.get("document_id"),
                    "source": hit.get("source"),
                    "page": hit.get("page", 0),
                    "score": hit.get("score", 0.0),
                    "metadata": hit.get("metadata") or {},
                }
            )
        return normalized


def build_baseline_agent(
    *,
    database_url: str | None = None,
    strategy: str = "A",
    model_name: str = "tfidf-local",
    top_k: int = 3,
    budget: int = 800,
) -> tuple[SimpleRuleController, VectorStoreRetriever]:
    """Create a simple, working Day 7 baseline agent.

    It is intentionally lightweight: search with the Day 7 vector store, then answer
    from the best retrieved context. This is a useful starting point before adding a
    real LLM-based controller or a hybrid retriever.
    """
    controller = SimpleRuleController()
    retriever = VectorStoreRetriever(database_url=database_url, strategy=strategy, model_name=model_name, top_k=top_k)
    return controller, retriever


def run_agent(question: str, controller: Controller, retriever: Retriever, *,
              filters: dict[str, Any] | None = None, max_searches: int = 4,
              top_k: int = 3, budget: int = 800) -> dict[str, Any]:
    """Return answer, citation IDs and trace; no benchmark gold enters this loop.

    A final answer without valid citations, an empty context, and a search limit
    lead to abstention. This only checks citation IDs, not semantic grounding.
    Provider/retriever errors propagate; no silent mock fallback.
    """
    if not question.strip() or max_searches < 1 or top_k < 1 or budget < 1:
        raise ValueError('question, max_searches, top_k hoặc budget không hợp lệ')
    history: list[dict[str, Any]] = []
    chunks: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    events: list[dict[str, Any]] = []
    for _ in range(max_searches + 1):
        action = controller.decide(question, history)
        if action.get('action') == 'search':
            if sum(e['event'] == 'search' for e in events) >= max_searches:
                return {'status': 'abstain', 'answer': 'Không đủ bằng chứng để trả lời.', 'citations': [], 'events': events + [{'event': 'search_limit'}]}
            query = action.get('query')
            if not isinstance(query, str) or not query.strip():
                raise ValueError('search query phải là chuỗi không rỗng')
            results = retriever.search(query, filters=filters, top_k=top_k)
            if len(results) > top_k or len({r['id'] for r in results}) != len(results):
                raise ValueError('retriever phải trả tối đa top_k chunk ID duy nhất')
            candidates.extend(results)
            context, ids = pack_context(candidates, budget=budget)
            chunks = {c['id']: c for c in candidates if c['id'] in ids}
            events.append({'event': 'search', 'query': query, 'filter': filters, 'results': results,
                           'context': context, 'context_ids': ids})
            # Send only the latest cumulative context; avoid multiplying the budget.
            history = [{'tool': 'search', 'queries': [e['query'] for e in events if e['event'] == 'search'],
                        'context': context, 'context_ids': ids}]
        elif action.get('action') == 'answer':
            answer, citations = action.get('answer'), action.get('citations')
            if not isinstance(answer, str) or not isinstance(citations, list) or any(not isinstance(i, str) for i in citations):
                raise ValueError('answer/citations không hợp lệ')
            valid = bool(answer.strip() and citations and all(i in chunks and f'[{i}]' in answer for i in citations))
            if valid:
                return {'status': 'answered', 'answer': answer, 'citations': citations, 'events': events + [{'event': 'answer'}]}
            return {'status': 'abstain', 'answer': 'Không đủ bằng chứng để trả lời.', 'citations': [], 'events': events + [{'event': 'invalid_or_missing_citations'}]}
        else:
            raise ValueError('action phải là search hoặc answer')
    return {'status': 'abstain', 'answer': 'Không đủ bằng chứng để trả lời.', 'citations': [], 'events': events}


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split())


def _tokenize(text: str) -> list[str]:
    import re
    import unicodedata
    normalized = unicodedata.normalize("NFKC", _normalize_text(text)).casefold()
    return re.findall(r"[a-z0-9]+", normalized)


class DenseVectorRetrieval:
    """Dense query-to-chunk retrieval using the Day 7 embedder or a local TF-IDF fallback."""

    def __init__(self, chunks: list[dict[str, Any]], *, strategy: str = "A") -> None:
        self.chunks = chunks
        self.strategy = strategy
        self.embedder = None
        try:
            if MyEmbedder is not None:
                self.embedder = MyEmbedder(model_name="tfidf-local")
                texts = [c.get("text", "") for c in chunks if c.get("text")]
                if texts:
                    self.embedder.fit(texts)
        except Exception:  # pragma: no cover - fallback is allowed
            self.embedder = None

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        query_text = _normalize_text(query)
        filtered = self._apply_filters(self.chunks, filters)
        if not filtered:
            return []

        if self.embedder is not None:
            qv = self.embedder.embed_query(query_text)
            doc_vectors = self.embedder.embed_documents([c.get("text", "") for c in filtered])
            ranked = []
            for chunk, vector in zip(filtered, doc_vectors):
                score = sum(a * b for a, b in zip(qv, vector))
                ranked.append({**chunk, "score": float(score), "strategy": self.strategy})
            ranked.sort(key=lambda c: (-c["score"], str(c.get("id", ""))))
            return ranked[:top_k]

        # fallback: token overlap score when embeddings are not available
        query_tokens = set(_tokenize(query_text))
        ranked = []
        for chunk in filtered:
            tokens = set(_tokenize(chunk.get("text", "")))
            overlap = len(query_tokens & tokens)
            ranked.append({**chunk, "score": float(overlap), "strategy": self.strategy})
        ranked.sort(key=lambda c: (-c["score"], str(c.get("id", ""))))
        return ranked[:top_k]

    @staticmethod
    def _apply_filters(chunks: list[dict[str, Any]], filters: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not filters:
            return chunks
        filtered = []
        for chunk in chunks:
            metadata = chunk.get("metadata") or {}
            ok = True
            for key, value in filters.items():
                if metadata.get(key) != value and chunk.get(key) != value:
                    ok = False
                    break
            if ok:
                filtered.append(chunk)
        return filtered


class LexicalTFIDFRetrieval:
    """TF-IDF lexical retrieval using cosine similarity on chunk text."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.cosine_similarity = cosine_similarity
        self.matrix = self.vectorizer.fit_transform([c.get("text", "") for c in chunks if c.get("text")])

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        filtered = DenseVectorRetrieval._apply_filters(self.chunks, filters)
        if not filtered:
            return []
        texts = [c.get("text", "") for c in filtered]
        if not texts:
            return []
        vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        matrix = vectorizer.fit_transform(texts)
        q_vec = vectorizer.transform([query])
        sims = self.cosine_similarity(q_vec, matrix)[0]
        ranked = []
        for chunk, score in zip(filtered, sims):
            ranked.append({**chunk, "score": float(score), "strategy": "tfidf"})
        ranked.sort(key=lambda c: (-c["score"], str(c.get("id", ""))))
        return ranked[:top_k]


class BM25Retrieval:
    """BM25 lexical retrieval implemented in pure Python; no external BM25 dependency required."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        self.documents = [_tokenize(c.get("text", "")) for c in chunks]
        self.N = len(self.documents)
        self.df = {}
        for doc in self.documents:
            for term in set(doc):
                self.df[term] = self.df.get(term, 0) + 1
        self.avgdl = sum(len(doc) for doc in self.documents) / max(1, self.N)
        self.k1 = 1.5
        self.b = 0.75

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        filtered = DenseVectorRetrieval._apply_filters(self.chunks, filters)
        if not filtered:
            return []
        q_tokens = _tokenize(query)
        ranked = []
        for chunk in filtered:
            doc_tokens = _tokenize(chunk.get("text", ""))
            score = 0.0
            for term in set(q_tokens):
                if term not in self.df:
                    continue
                tf = doc_tokens.count(term)
                idf = __import__("math").log(((self.N - self.df[term] + 0.5) / (self.df[term] + 0.5)) + 1.0)
                denom = tf + self.k1 * (1 - self.b + self.b * len(doc_tokens) / max(1.0, self.avgdl))
                score += idf * ((tf * (self.k1 + 1)) / denom)
            ranked.append({**chunk, "score": float(score), "strategy": "bm25"})
        ranked.sort(key=lambda c: (-c["score"], str(c.get("id", ""))))
        return ranked[:top_k]


class HybridRRFRetrieval:
    """Reciprocal Rank Fusion combining dense and lexical rankings."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        dense = DenseVectorRetrieval(self.chunks).search(query, filters=filters, top_k=top_k)
        tfidf = LexicalTFIDFRetrieval(self.chunks).search(query, filters=filters, top_k=top_k)
        scores = {}
        for rank, item in enumerate(dense, start=1):
            scores[item.get("id")] = scores.get(item.get("id"), 0.0) + 1.0 / (60 + rank)
        for rank, item in enumerate(tfidf, start=1):
            scores[item.get("id")] = scores.get(item.get("id"), 0.0) + 1.0 / (60 + rank)

        merged = []
        for chunk in self.chunks:
            cid = chunk.get("id")
            if cid in scores:
                merged.append({**chunk, "score": float(scores[cid]), "strategy": "hybrid_rrf"})
        merged.sort(key=lambda c: (-c["score"], str(c.get("id", ""))))
        return merged[:top_k]


class QueryExpansionRetrieval:
    """Simple query expansion using a small domain lexicon for software engineering tasks."""

    def __init__(self, chunks: list[dict[str, Any]]) -> None:
        self.chunks = chunks
        self.synonyms = {
            "clean code": ["clean code", "code quality", "readability", "maintainability", "craftsmanship"],
            "professional": ["professional", "craftsmanship", "quality", "care", "best practice"],
            "maintenance": ["maintenance", "repair", "refactoring", "quality"],
            "details": ["details", "care", "quality", "craftsmanship"],
        }

    def _expand(self, query: str) -> str:
        q = _normalize_text(query).casefold()
        expanded_terms = [q]
        for key, values in self.synonyms.items():
            if key in q:
                expanded_terms.extend(values)
        return " ".join(expanded_terms)

    def search(self, query: str, *, filters: dict[str, Any] | None = None, top_k: int = 3) -> list[dict[str, Any]]:
        expanded_query = self._expand(query)
        return LexicalTFIDFRetrieval(self.chunks).search(expanded_query, filters=filters, top_k=top_k)


def benchmark_retrieval_methods(chunks: list[dict[str, Any]], question: str, *, top_k: int = 3) -> dict[str, list[dict[str, Any]]]:
    """Convenience helper to run all five retrieval methods on a single question."""
    methods = {
        "dense": DenseVectorRetrieval(chunks).search(question, top_k=top_k),
        "tfidf": LexicalTFIDFRetrieval(chunks).search(question, top_k=top_k),
        "bm25": BM25Retrieval(chunks).search(question, top_k=top_k),
        "hybrid_rrf": HybridRRFRetrieval(chunks).search(question, top_k=top_k),
        "query_expansion": QueryExpansionRetrieval(chunks).search(question, top_k=top_k),
    }
    return methods
